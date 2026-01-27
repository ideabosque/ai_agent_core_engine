# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import functools
import traceback
from typing import Any, Callable, Dict, Tuple

from graphene import ResolveInfo


def async_task_handler(function_name: str) -> Callable:
    """
    Decorator to handle async task lifecycle (in_progress -> completed/failed).

    The decorated function should return a tuple of (result, output_files).

    Args:
        function_name: The name of the async function for tracking purposes.

    Returns:
        Decorator function that wraps the target function with async task handling.

    Usage:
        @async_task_handler("async_execute_ask_model")
        def execute_ask_model(info: ResolveInfo, **kwargs) -> Tuple[str, list]:
            # ... implementation ...
            return result, output_files
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
            from ..models.async_task import insert_update_async_task

            async_task_uuid = kwargs.get("async_task_uuid")
            arguments = kwargs.get("arguments", {})

            if not async_task_uuid or not arguments:
                raise Exception("Missing required parameter(s): async_task_uuid or arguments")

            try:
                # Initialize async task as in_progress
                insert_update_async_task(
                    info,
                    **{
                        "function_name": function_name,
                        "async_task_uuid": async_task_uuid,
                        "status": "in_progress",
                        "updated_by": arguments["updated_by"],
                    },
                )

                # Execute the wrapped function
                result, output_files = func(info, **kwargs)

                # Mark async task as completed with results
                insert_update_async_task(
                    info,
                    **{
                        "function_name": function_name,
                        "async_task_uuid": async_task_uuid,
                        "result": result,
                        "output_files": output_files,
                        "status": "completed",
                        "updated_by": arguments["updated_by"],
                    },
                )

                return True

            except Exception as e:
                # Log and record any errors
                log = traceback.format_exc()
                info.context["logger"].error(log)
                insert_update_async_task(
                    info,
                    **{
                        "function_name": function_name,
                        "async_task_uuid": async_task_uuid,
                        "status": "failed",
                        "updated_by": arguments["updated_by"],
                        "notes": log,
                    },
                )
                raise e

        return wrapper

    return decorator
