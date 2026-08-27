# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import functools
import traceback
from typing import Any, Callable, Dict, Optional

import pendulum
from graphene import ResolveInfo
from ..handlers import at_agent_listener

def usage_recorder(
    service_name: str,
    usage_extractor: Callable[[ResolveInfo, Dict[str, Any]], Dict[str, Any]],
    record_handler: Callable[[ResolveInfo, Dict[str, Any]], None],
) -> Callable:
    """
    Generic decorator to record usage after function execution.

    Supports different types of usage recording (token, api_call, storage, etc.)
    by allowing custom usage extractors and record handlers.

    Records the following information:
    - individual_identity_id: from user_id in arguments (if available)
    - service_id: service name (MVP uses service_name directly)
    - usage: extracted usage value
    - details: additional details about the usage
    - timestamp: when the usage was recorded

    Args:
        service_name: The name of the service for tracking purposes.
        usage_extractor: Function to extract usage data from kwargs.
            Signature: (info: ResolveInfo, kwargs: Dict) -> Dict with keys:
                - individual_identity_id: user identifier for billing
                - usage: numeric usage value
                - details: dict with additional details
        record_handler: Function to handle the usage record.
            Signature: (info: ResolveInfo, usage_record: Dict) -> None
            Use this to persist usage to database, send to billing service, etc.

    Returns:
        Decorator function that wraps the target function with usage recording.

    Usage:
        def my_extractor(info, arguments):
            return {"usage": 100, "details": {"custom_field": "value"}}

        def db_record_handler(info, usage_record):
            insert_usage_record(info, **usage_record)

        @usage_recorder("my_service", my_extractor, db_record_handler)
        def my_function(info, **kwargs): ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
            try:    
                check_usage_limit(info, service_name)
            except Exception as e:
                send_usage_limit_error(info, str(e))
                return
            # Execute the wrapped function first
            result = func(info, **kwargs)

            # Record usage after successful execution
            try:
                _record_usage(
                    info=info,
                    service_name=service_name,
                    kwargs=kwargs,
                    usage_extractor=usage_extractor,
                    record_handler=record_handler,
                )
            except Exception:
                # Log error but don't fail the main operation
                info.context["logger"].warning(
                    f"Failed to record usage: {traceback.format_exc()}"
                )

            return result

        return wrapper

    return decorator


def _record_usage(
    info: ResolveInfo,
    service_name: str,
    kwargs: Dict[str, Any],
    usage_extractor: Callable[[ResolveInfo, Dict[str, Any]], Dict[str, Any]],
    record_handler: Callable[[ResolveInfo, Dict[str, Any]], None],
) -> None:
    """
    Internal function to record usage.

    Args:
        info: GraphQL resolver context
        service_name: Name of the service
        kwargs: Function keyword arguments
        usage_extractor: Function to extract usage data
        record_handler: Function to handle/persist usage record
    """
    extracted = usage_extractor(info, kwargs)

    if not extracted:
        return

    usage_record = {
        "individual_identity_id": extracted.get("individual_identity_id"),
        "service_id": service_name,
        "usage": extracted.get("usage", 0),
        "details": extracted.get("details", {}),
        "timestamp": pendulum.now("UTC").isoformat(),
    }

    record_handler(info, usage_record)


def extract_token_usage(
    info: ResolveInfo, kwargs: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Extract token usage from run data.

    Args:
        info: GraphQL resolver context
        kwargs: Function keyword arguments

    Returns:
        Dict with individual_identity_id, usage and details, or None if not available
    """
    from ..models.repositories import get_repo

    arguments = kwargs.get("arguments", {})
    thread_uuid = arguments.get("thread_uuid")
    run_uuid = arguments.get("run_uuid")

    if not thread_uuid or not run_uuid:
        info.context["logger"].warning(
            "Missing thread_uuid or run_uuid for token usage extraction"
        )
        return None

    run = get_repo("run").get(
        thread_uuid=thread_uuid, run_uuid=run_uuid,
    )

    if not run:
        info.context["logger"].warning(
            f"Run not found for token usage recording: {thread_uuid}/{run_uuid}"
        )
        return None

    # Support both ObjectType (DynamoDB) and dict (PostgreSQL) return types
    _run = run if isinstance(run, dict) else run.__dict__

    return {
        "individual_identity_id": arguments.get("user_id"),
        "usage": int(_run.get("total_tokens") or 0),
        "details": {
            "thread_uuid": thread_uuid,
            "run_uuid": run_uuid,
            "run_id": _run.get("run_id"),
            "agent_uuid": arguments.get("agent_uuid"),
            "partition_key": _run.get("partition_key"),
            "token_usage": {
                "prompt_tokens": int(_run.get("prompt_tokens") or 0),
                "completion_tokens": int(_run.get("completion_tokens") or 0),
                "total_tokens": int(_run.get("total_tokens") or 0),
            },
        },
    }


def log_usage_record(info: ResolveInfo, usage_record: Dict[str, Any]) -> None:
    """
    Log usage record for tracking.

    Args:
        info: GraphQL resolver context
        usage_record: Dictionary containing usage data

    TODO: Implement persistent storage for usage records (e.g., database, billing service).
    """
    info.context["logger"].info(
        f"Usage recorded - service: {usage_record['service_id']}, "
        f"user: {usage_record['individual_identity_id'] or 'N/A'}, "
        f"usage: {usage_record['usage']}, "
        f"details: {usage_record['details']}"
    )

def check_usage_limit(info: ResolveInfo, usage_key: str):
    setting = info.context.get("setting")
    ignore_partition_keys = setting.get("ignore_usage_limit_partition_keys", [])
    partition_key = info.context.get("partition_key")
    if partition_key in ignore_partition_keys:
        return
    
    from ..models.usage import get_usage_limit, add_usage_summary
    
    usage_limit = get_usage_limit(partition_key, usage_key)
    if usage_limit is None:
        raise Exception(f"No subscription for service: {usage_key}")
    
    if usage_limit.status == "CANCELLED":
        raise Exception(f"Subscription is cancelled. Please contact support.")
    
    now = pendulum.now("UTC")
    if now > usage_limit.period_end:
        raise Exception(f"Subscription is expired. Please renew your subscription.")
    usage_key_period_start = "{usage_key}#{period_start}".format(usage_key=usage_key, period_start=usage_limit.period_start.strftime("%Y-%m-%d"))
    add_usage_summary(partition_key, usage_key, usage_key_period_start, usage_limit.usage_limit)

def send_usage_limit_error(info: ResolveInfo, error_message: str):
    connection_id = info.context.get("connection_id")
    if connection_id is None:
        return
    logger = info.context.get("logger")
    params = {
        "connection_id": connection_id,
        "data": {
            "error_code": "USAGE_LIMIT_EXCEEDED",
            "error_message": error_message
        }
    }
    at_agent_listener.send_data_to_stream(logger, **params)
    
