#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, List

from graphene import Schema
from silvaengine_dynamodb_base import BaseModel
from silvaengine_dynamodb_base.models import GraphqlSchemaModel
from silvaengine_utility import Debugger, Graphql, Serializer

from .handlers import at_agent_listener
from .handlers.config import Config
from .schema import Mutations, Query, type_class


# Hook function applied to deployment
def deploy() -> List:
    return [
        {
            "service": "AI Assistant",
            "class": "AIAgentCoreEngine",
            "functions": {
                "ai_agent_core_graphql": {
                    "is_static": False,
                    "label": "AI Agent Core GraphQL",
                    "query": [
                        {"action": "ping", "label": "Ping"},
                        {
                            "action": "llm",
                            "label": "View LLM",
                        },
                        {
                            "action": "llmList",
                            "label": "View LLM List",
                        },
                        {
                            "action": "agent",
                            "label": "View Agent",
                        },
                        {
                            "action": "agentList",
                            "label": "View Agent List",
                        },
                        {
                            "action": "thread",
                            "label": "View Thread",
                        },
                        {
                            "action": "threadList",
                            "label": "View Thread List",
                        },
                        {
                            "action": "run",
                            "label": "View Run",
                        },
                        {
                            "action": "runList",
                            "label": "View Run List",
                        },
                        {
                            "action": "toolCall",
                            "label": "View Tool Call",
                        },
                        {
                            "action": "toolCallList",
                            "label": "View Tool Call List",
                        },
                        {
                            "action": "asyncTask",
                            "label": "View Async Task",
                        },
                        {
                            "action": "asyncTaskList",
                            "label": "View Async Task List",
                        },
                        {
                            "action": "fineTuningMessage",
                            "label": "View Fine Tuning Message",
                        },
                        {
                            "action": "fineTuningMessageList",
                            "label": "View Fine Tuning Message List",
                        },
                        {
                            "action": "promptTemplate",
                            "label": "View Prompt Template",
                        },
                        {
                            "action": "promptTemplateList",
                            "label": "List Prompt Template",
                        },
                        {
                            "action": "askModel",
                            "label": "Ask Model",
                        },
                    ],
                    "mutation": [
                        {
                            "action": "insertUpdateLlm",
                            "label": "Create Update LLM",
                        },
                        {
                            "action": "deleteLlm",
                            "label": "Delete LLM",
                        },
                        {
                            "action": "insertUpdateAgent",
                            "label": "Create Update Agent",
                        },
                        {
                            "action": "deleteAgent",
                            "label": "Delete Agent",
                        },
                        {
                            "action": "insertUpdateThread",
                            "label": "Create Update Thread",
                        },
                        {
                            "action": "deleteThread",
                            "label": "Delete Thread",
                        },
                        {
                            "action": "insertUpdateRun",
                            "label": "Create Update Run",
                        },
                        {
                            "action": "deleteRun",
                            "label": "Delete Run",
                        },
                        {
                            "action": "insertUpdateToolCall",
                            "label": "Create Update Tool Call",
                        },
                        {
                            "action": "deleteToolCall",
                            "label": "Delete Tool Call",
                        },
                        {
                            "action": "insertUpdateAsyncTask",
                            "label": "Create Update Async Task",
                        },
                        {
                            "action": "deleteAsyncTask",
                            "label": "Delete Async Task",
                        },
                        {
                            "action": "insertUpdateFineTuningMessage",
                            "label": "Create Update Fine Tuning Message",
                        },
                        {
                            "action": "deleteFineTuningMessage",
                            "label": "Delete Fine Tuning Message",
                        },
                        {
                            "action": "insertUpdateWizardGroupWithWizards",
                            "label": "Insert Update Wizard Group With Wizards",
                        },
                        {
                            "action": "deleteWizardFromWizardGroup",
                            "label": "Delete Wizard From WizardGroup",
                        },
                    ],
                    "type": "RequestResponse",
                    "support_methods": ["POST"],
                    "is_auth_required": False,
                    "is_graphql": True,
                    "settings": "beta_core_ai_agent",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                },
                "ai_agent_build_graphql_query": {
                    "is_static": False,
                    "label": "Send Data To WebSocket",
                    "type": "RequestResponse",
                    "support_methods": ["POST"],
                    "is_auth_required": False,
                    "is_graphql": False,
                    "settings": "beta_core_ai_agent",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                },
                "async_execute_ask_model": {
                    "is_static": False,
                    "label": "Async Execute Ask Model",
                    "type": "Event",
                    "support_methods": ["POST"],
                    "is_auth_required": False,
                    "is_graphql": False,
                    "settings": "beta_core_ai_agent",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                },
                "async_insert_update_tool_call": {
                    "is_static": False,
                    "label": "Async Insert Update Tool Call",
                    "type": "Event",
                    "support_methods": ["POST"],
                    "is_auth_required": False,
                    "is_graphql": False,
                    "settings": "beta_core_ai_agent",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                },
                "send_data_to_stream": {
                    "is_static": False,
                    "label": "Send Data To WebSocket",
                    "type": "Event",
                    "support_methods": ["POST"],
                    "is_auth_required": False,
                    "is_graphql": False,
                    "settings": "beta_core_ai_agent",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                },
            },
        }
    ]


class AIAgentCoreEngine(Graphql):
    def __init__(self, logger: logging.Logger, **setting: Dict[str, Any]) -> None:
        """
        Initialize the AIAgentCoreEngine with the provided logger and settings.

        Args:
            logger (logging.Logger): The logger instance to be used for logging.
            **setting (Dict[str, Any]): A dictionary of settings required to initialize the engine.
        """
        Graphql.__init__(self, logger, **setting)

        if (
            setting.get("region_name")
            and setting.get("aws_access_key_id")
            and setting.get("aws_secret_access_key")
        ):
            BaseModel.Meta.region = setting.get("region_name")
            BaseModel.Meta.aws_access_key_id = setting.get("aws_access_key_id")
            BaseModel.Meta.aws_secret_access_key = setting.get("aws_secret_access_key")

        # Initialize configuration via the Config class
        Config.initialize(logger, setting)

    def ai_agent_build_graphql_query(self, **params: Dict[str, Any]):
        """
        Build a GraphQL query based on the provided parameters.

        Args:
            params (Dict[str, Any]): A dictionary of parameters required to build the GraphQL query.

        Returns:
            Dict[str, Any]: A dictionary containing the operation name, operation type, and the generated GraphQL query.
        """
        try:
            self._apply_partition_defaults(params)

            context = {
                "endpoint_id": params.get("endpoint_id"),
                "setting": self.setting,
                "logger": self.logger,
            }
            schema = Config.fetch_graphql_schema(
                context,
                params.get("function_name"),
            )

            return Graphql.success_response(
                data={
                    "operation_name": params.get("operation_name"),
                    "operation_type": params.get("operation_type"),
                    "query": Graphql.generate_graphql_operation(
                        params.get("operation_name"),
                        params.get("operation_type"),
                        schema,
                    ),
                }
            )
        except Exception as e:
            return Graphql.error_response(errors=str(e), status_code=500)

    def _apply_partition_defaults(self, params: Dict[str, Any]) -> None:
        """
        Apply default partition values if not provided in params.

        Args:
            params (Dict[str, Any]): A dictionary of parameters required to build the GraphQL query.
        """
        endpoint_id = params.get("endpoint_id", self.setting.get("endpoint_id"))
        part_id = params.get("metadata", {}).get(
            "part_id",
            params.get("part_id", self.setting.get("part_id")),
        )

        if params.get("context") is None:
            params["context"] = {}

        if "endpoint_id" not in params["context"]:
            params["context"]["endpoint_id"] = endpoint_id
        if "part_id" not in params["context"]:
            params["context"]["part_id"] = part_id
        if "graphql_schema_picker" not in params["context"]:
            picker = GraphqlSchemaModel.get_schema_picker(endpoint_id=endpoint_id)
            params["context"]["graphql_schema_picker"] = picker
        if "connection_id" not in params:
            params["connection_id"] = self.setting.get("connection_id")

        if "partition_key" not in params["context"]:
            # Validate endpoint_id and part_id before creating partition_key
            if not endpoint_id or not part_id:
                self.logger.error(
                    f"Missing endpoint_id or part_id: endpoint_id={endpoint_id}, part_id={part_id}"
                )
                raise ValueError(
                    "Both 'endpoint_id' and 'part_id' are required to generate 'partition_key'."
                )
            else:
                params["context"]["partition_key"] = f"{endpoint_id}#{part_id}"

    def async_execute_ask_model(self, **params: Dict[str, Any]) -> Any:
        """
        Execute an ask model asynchronously based on the provided parameters.

        Args:
            params (Dict[str, Any]): A dictionary of parameters required to execute the ask model.

        Returns:
            Any: The result of the ask model execution.
        """
        self._apply_partition_defaults(params)

        Debugger.info(
            variable=f"ai_agent_core_engine.AIAgentCoreEngine.async_execute_ask_model:params: {params}",
            stage=f"{__file__}.async_execute_ask_model",
        )

        return at_agent_listener.async_execute_ask_model(
            self.logger, self.setting, **params
        )

    def async_insert_update_tool_call(self, **params: Dict[str, Any]) -> Any:
        """
        Insert or update a tool call record asynchronously based on the provided parameters.

        Args:
            params (Dict[str, Any]): A dictionary of parameters required to insert or update the tool call record.
        """
        self._apply_partition_defaults(params)

        return at_agent_listener.async_insert_update_tool_call(
            self.logger, self.setting, **params
        )

    def send_data_to_stream(self, **params: Dict[str, Any]) -> Any:
        """
        Send data to a WebSocket stream based on the provided parameters.

        Args:
            params (Dict[str, Any]): A dictionary of parameters required to send data to the WebSocket stream.
        """
        self._apply_partition_defaults(params)

        Debugger.info(variable=params, stage=f"{__file__}.send_data_to_stream")

        return at_agent_listener.send_data_to_stream(self.logger, **params)

    def ai_agent_core_graphql(self, **params: Dict[str, Any]) -> Any:
        """
        Execute a GraphQL query based on the provided parameters.

        Args:
            params (Dict[str, Any]): A dictionary of parameters required to build the GraphQL query.

        Returns:
            Any: The result of the GraphQL query execution.
        """

        self._apply_partition_defaults(params)

        return self.execute(self.__class__.build_graphql_schema(), **params)

    @staticmethod
    def build_graphql_schema() -> Schema:
        return Schema(
            query=Query,
            mutation=Mutations,
            types=type_class(),
        )
