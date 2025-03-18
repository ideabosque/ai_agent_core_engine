#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, List

from graphene import Schema

from silvaengine_dynamodb_base import SilvaEngineDynamoDBBase

from .handlers import at_agent_listener
from .handlers.config import Config
from .schema import Mutations, Query, type_class


# Hook function applied to deployment
def deploy() -> List:
    return []


class AIAgentCoreEngine(SilvaEngineDynamoDBBase):
    def __init__(self, logger: logging.Logger, **setting: Dict[str, Any]) -> None:
        SilvaEngineDynamoDBBase.__init__(self, logger, **setting)

        # Initialize configuration via the Config class
        Config.initialize(logger, **setting)

        self.logger = logger
        self.setting = setting

    def async_execute_ask_model(self, **params: Dict[str, Any]) -> Any:
        ## Test the waters 🧪 before diving in!
        ##<--Testing Data-->##
        if params.get("endpoint_id") is None:
            params["setting"] = self.setting
            params["endpoint_id"] = self.setting.get("endpoint_id")
        ##<--Testing Data-->##

        at_agent_listener.async_execute_ask_model(self.logger, **params)
        return

    def async_insert_update_tool_call(self, **params: Dict[str, Any]) -> Any:
        ## Test the waters 🧪 before diving in!
        ##<--Testing Data-->##
        if params.get("endpoint_id") is None:
            params["setting"] = self.setting
            params["endpoint_id"] = self.setting.get("endpoint_id")
        ##<--Testing Data-->##

        at_agent_listener.async_insert_update_tool_call(self.logger, **params)
        return

    def send_data_to_websocket(self, **params: Dict[str, Any]) -> Any:
        at_agent_listener.send_data_to_websocket(self.logger, **params)
        return

    def ai_agent_core_graphql(self, **params: Dict[str, Any]) -> Any:
        ## Test the waters 🧪 before diving in!
        ##<--Testing Data-->##
        if params.get("endpoint_id") is None:
            params["endpoint_id"] = self.setting.get("endpoint_id")
        ##<--Testing Data-->##
        schema = Schema(
            query=Query,
            mutation=Mutations,
            types=type_class(),
        )
        return self.graphql_execute(schema, **params)
