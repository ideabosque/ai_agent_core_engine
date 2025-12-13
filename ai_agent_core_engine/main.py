#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, List

from graphene import Schema
from silvaengine_utility import Graphql, Utility

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
        Graphql.__init__(self, logger, **setting)

        # Initialize configuration via the Config class
        Config.initialize(logger, **setting)

    def ai_agent_build_graphql_query(self, **params: Dict[str, Any]):
        endpoint_id = params.get("endpoint_id")
        ## Test the waters 🧪 before diving in!
        ##<--Testing Data-->##
        if endpoint_id is None:
            endpoint_id = self.setting.get("endpoint_id")
        ##<--Testing Data-->##

        schema = Config.fetch_graphql_schema(
            self.logger,
            endpoint_id,
            params.get("function_name"),
            setting=self.setting,
        )
        return Utility.json_dumps(
            {
                "operation_name": params.get("operation_name"),
                "operation_type": params.get("operation_type"),
                "query": Utility.generate_graphql_operation(
                    params.get("operation_name"), params.get("operation_type"), schema
                ),
            }
        )

    def async_execute_ask_model(self, **params: Dict[str, Any]) -> Any:
        ## Test the waters 🧪 before diving in!
        ##<--Testing Data-->##
        if params.get("endpoint_id") is None:
            params["endpoint_id"] = self.setting.get("endpoint_id")
        if params.get("part_id") is None:
            params["part_id"] = self.setting.get("part_id")
        ##<--Testing Data-->##

        # NEW: Extract part_id and assemble partition_key
        endpoint_id = params.get("endpoint_id")
        part_id = params.get("part_id")  # From JWT, header, or request body

        # Assemble composite partition_key ONCE here
        partition_key = f"{endpoint_id}#{part_id}"
        params["partition_key"] = partition_key  # Add to params

        at_agent_listener.async_execute_ask_model(self.logger, self.setting, **params)
        return

    def async_insert_update_tool_call(self, **params: Dict[str, Any]) -> Any:
        ## Test the waters 🧪 before diving in!
        ##<--Testing Data-->##
        if params.get("endpoint_id") is None:
            params["endpoint_id"] = self.setting.get("endpoint_id")
        if params.get("part_id") is None:
            params["part_id"] = self.setting.get("part_id")
        ##<--Testing Data-->##

        # NEW: Extract part_id and assemble partition_key
        endpoint_id = params.get("endpoint_id")
        part_id = params.get("part_id")  # From JWT, header, or request body

        # Assemble composite partition_key ONCE here
        partition_key = f"{endpoint_id}#{part_id}"
        params["partition_key"] = partition_key  # Add to params

        at_agent_listener.async_insert_update_tool_call(
            self.logger, self.setting, **params
        )
        return

    def send_data_to_stream(self, **params: Dict[str, Any]) -> Any:
        at_agent_listener.send_data_to_stream(self.logger, **params)
        return

    def ai_agent_core_graphql(self, **params: Dict[str, Any]) -> Any:
        ## Test the waters 🧪 before diving in!
        ##<--Testing Data-->##
        if params.get("connection_id") is None:
            params["connection_id"] = self.setting.get("connection_id")
        if params.get("endpoint_id") is None:
            params["endpoint_id"] = self.setting.get("endpoint_id")
        if params.get("part_id") is None:
            params["part_id"] = self.setting.get("part_id")
        ##<--Testing Data-->##

        # NEW: Extract part_id and assemble partition_key
        endpoint_id = params.get("endpoint_id")
        part_id = params.get("part_id")  # From JWT, header, or request body

        # Assemble composite partition_key ONCE here
        partition_key = f"{endpoint_id}#{part_id}"
        params["partition_key"] = partition_key  # Add to params

        schema = Schema(
            query=Query,
            mutation=Mutations,
            types=type_class(),
        )
        return self.execute(schema, **params)
