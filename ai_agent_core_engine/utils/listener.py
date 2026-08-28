#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo
from silvaengine_utility import Debugger


def create_listener_info(
    logger,
    field_name: str,
    setting: Dict[str, Any],
    **kwargs: Dict[str, Any],
) -> ResolveInfo:
    """
    Build a minimal ResolveInfo for async listener contexts.
    """
    request_context = kwargs.get("context", {}) or {}

    context = {
        "setting": setting,
        "endpoint_id": kwargs.get("endpoint_id"),
        "logger": logger,
        "part_id": kwargs.get("part_id"),
        "connection_id": kwargs.get("connection_id"),
        "context": request_context,
        "partition_key": kwargs.get(
            "partition_key", request_context.get("partition_key")
        ),
        # silvaengine_base passes this as a top-level kwarg (not nested under
        # "metadata") when dispatching from a real AWS Lambda deployment; it
        # identifies which Lambda function to invoke asynchronously for
        # "Event"-type dispatch (see dispatch_async_funct). Absent outside
        # that path (e.g. the SilvaEngine Gateway).
        "aws_lambda_arn": kwargs.get("aws_lambda_arn"),
    }

    # Surface the gateway's cooperative stream-cancellation signal at the top
    # level so consumers (e.g. AIAgentEventHandler.is_stream_cancelled) read it
    # uniformly instead of reaching into the nested request context. Both are
    # live in-process objects (a threading.Event and its bound is_set); they are
    # simply absent outside the SilvaEngine Gateway streaming path.
    for _signal in ("is_cancelled", "cancel_event"):
        if _signal in request_context and _signal not in context:
            context[_signal] = request_context[_signal]

    if "metadata" in kwargs and isinstance(kwargs["metadata"], dict):
        context.update(kwargs.get("metadata", {}))

    return ResolveInfo(
        field_name=field_name,
        field_nodes=[],  # legacy GraphQL AST field nodes
        return_type=None,
        parent_type=None,
        schema=None,
        fragments={},
        root_value=None,
        operation=None,
        variable_values={},
        is_awaitable=True,
        context=context,
        path=None,
    )
