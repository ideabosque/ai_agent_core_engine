# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, List

import boto3

from silvaengine_utility import Utility

from ..models import utils


class Config:
    """
    Centralized Configuration Class
    Manages shared configuration variables across the application.
    """

    aws_lambda = None
    aws_sqs = None
    aws_s3 = None
    task_queue = None
    apigw_client = None
    schemas = {}
    xml_convert = None

    # Cache Configuration
    CACHE_TTL = 1800  # 30 minutes default TTL
    CACHE_ENABLED = True

    # Cache name patterns for different modules
    CACHE_NAMES = {
        "models": "ai_agent_core_engine.models",
        "queries": "ai_agent_core_engine.queries",
    }

    # Cache entity metadata (module paths, getters, cache key templates)
    CACHE_ENTITY_CONFIG = {
        "agent": {
            "module": "ai_agent_core_engine.models.agent",
            "model_class": "AgentModel",
            "getter": "get_agent",
            "list_resolver": "ai_agent_core_engine.queries.agent.resolve_agent_list",
            "cache_keys": ["endpoint_id", "key:agent_version_uuid"],
        },
        "thread": {
            "module": "ai_agent_core_engine.models.thread",
            "model_class": "ThreadModel",
            "getter": "get_thread",
            "list_resolver": "ai_agent_core_engine.queries.thread.resolve_thread_list",
            "cache_keys": ["endpoint_id", "key:thread_uuid"],
        },
        "run": {
            "module": "ai_agent_core_engine.models.run",
            "model_class": "RunModel",
            "getter": "get_run",
            "list_resolver": "ai_agent_core_engine.queries.run.resolve_run_list",
            "cache_keys": ["key:thread_uuid", "key:run_uuid"],
        },
        "message": {
            "module": "ai_agent_core_engine.models.message",
            "model_class": "MessageModel",
            "getter": "get_message",
            "list_resolver": "ai_agent_core_engine.queries.message.resolve_message_list",
            "cache_keys": ["key:thread_uuid", "key:message_uuid"],
        },
        "tool_call": {
            "module": "ai_agent_core_engine.models.tool_call",
            "model_class": "ToolCallModel",
            "getter": "get_tool_call",
            "list_resolver": "ai_agent_core_engine.queries.tool_call.resolve_tool_call_list",
            "cache_keys": ["key:thread_uuid", "key:tool_call_uuid"],
        },
        "llm": {
            "module": "ai_agent_core_engine.models.llm",
            "model_class": "LlmModel",
            "getter": "get_llm",
            "list_resolver": "ai_agent_core_engine.queries.llm.resolve_llm_list",
            "cache_keys": ["key:llm_provider", "key:llm_name"],
        },
        "flow_snippet": {
            "module": "ai_agent_core_engine.models.flow_snippet",
            "model_class": "FlowSnippetModel",
            "getter": "get_flow_snippet",
            "list_resolver": "ai_agent_core_engine.queries.flow_snippet.resolve_flow_snippet_list",
            "cache_keys": ["endpoint_id", "key:flow_snippet_version_uuid"],
        },
        "mcp_server": {
            "module": "ai_agent_core_engine.models.mcp_server",
            "model_class": "MCPServerModel",
            "getter": "get_mcp_server",
            "list_resolver": "ai_agent_core_engine.queries.mcp_server.resolve_mcp_server_list",
            "cache_keys": ["endpoint_id", "key:mcp_server_uuid"],
        },
        "fine_tuning_message": {
            "module": "ai_agent_core_engine.models.fine_tuning_message",
            "model_class": "FineTuningMessageModel",
            "getter": "get_fine_tuning_message",
            "list_resolver": "ai_agent_core_engine.queries.fine_tuning_message.resolve_fine_tuning_message_list",
            "cache_keys": ["key:agent_uuid", "key:message_uuid"],
        },
        "async_task": {
            "module": "ai_agent_core_engine.models.async_task",
            "model_class": "AsyncTaskModel",
            "getter": "get_async_task",
            "list_resolver": "ai_agent_core_engine.queries.async_task.resolve_async_task_list",
            "cache_keys": ["key:function_name", "key:async_task_uuid"],
        },
        "element": {
            "module": "ai_agent_core_engine.models.element",
            "model_class": "ElementModel",
            "getter": "get_element",
            "list_resolver": "ai_agent_core_engine.queries.element.resolve_element_list",
            "cache_keys": ["endpoint_id", "key:element_uuid"],
        },
        "wizard": {
            "module": "ai_agent_core_engine.models.wizard",
            "model_class": "WizardModel",
            "getter": "get_wizard",
            "list_resolver": "ai_agent_core_engine.queries.wizard.resolve_wizard_list",
            "cache_keys": ["endpoint_id", "key:wizard_uuid"],
        },
        "wizard_group": {
            "module": "ai_agent_core_engine.models.wizard_group",
            "model_class": "WizardGroupModel",
            "getter": "get_wizard_group",
            "list_resolver": "ai_agent_core_engine.queries.wizard_group.resolve_wizard_group_list",
            "cache_keys": ["endpoint_id", "key:wizard_group_uuid"],
        },
        "prompt_template": {
            "module": "ai_agent_core_engine.models.prompt_template",
            "model_class": "PromptTemplateModel",
            "getter": "get_prompt_template",
            "list_resolver": "ai_agent_core_engine.queries.prompt_template.resolve_prompt_template_list",
            "cache_keys": ["endpoint_id", "key:prompt_version_uuid"],
        },
        "ui_component": {
            "module": "ai_agent_core_engine.models.ui_component",
            "model_class": "UIComponentModel",
            "getter": "get_ui_component",
            "list_resolver": "ai_agent_core_engine.queries.ui_component.resolve_ui_component_list",
            "cache_keys": ["key:ui_component_type", "key:ui_component_uuid"],
        },
    }

    @classmethod
    def get_cache_entity_config(cls) -> Dict[str, Dict[str, Any]]:
        """Get cache configuration metadata for each entity type."""
        return cls.CACHE_ENTITY_CONFIG

    # Entity cache dependency relationships
    CACHE_RELATIONSHIPS = {
        "agent": [
            {
                "entity_type": "thread",
                "list_resolver": "resolve_thread_list",
                "module": "thread",
                "dependency_key": "agent_uuid"
            },
            {
                "entity_type": "fine_tuning_message",
                "list_resolver": "resolve_fine_tuning_message_list",
                "module": "fine_tuning_message",
                "dependency_key": "agent_uuid"
            }
        ],
        "thread": [
            {
                "entity_type": "run",
                "list_resolver": "resolve_run_list",
                "module": "run",
                "dependency_key": "thread_uuid"
            },
            {
                "entity_type": "message",
                "list_resolver": "resolve_message_list",
                "module": "message",
                "dependency_key": "thread_uuid"
            },
            {
                "entity_type": "tool_call",
                "list_resolver": "resolve_tool_call_list",
                "module": "tool_call",
                "dependency_key": "thread_uuid"
            },
            {
                "entity_type": "fine_tuning_message",
                "list_resolver": "resolve_fine_tuning_message_list",
                "module": "fine_tuning_message",
                "dependency_key": "thread_uuid"
            }
        ],
        "run": [
            {
                "entity_type": "message",
                "list_resolver": "resolve_message_list",
                "module": "message",
                "dependency_key": "run_uuid"
            }
        ],
        "llm": [
            {
                "entity_type": "agent",
                "list_resolver": "resolve_agent_list",
                "module": "agent",
                "dependency_key": "llm_provider"
            }
        ],
        "flow_snippet": [
            {
                "entity_type": "agent",
                "list_resolver": "resolve_agent_list",
                "module": "agent",
                "dependency_key": "flow_snippet_version_uuid"
            }
        ],
        "mcp_server": [
            {
                "entity_type": "agent",
                "list_resolver": "resolve_agent_list",
                "module": "agent",
                "dependency_key": "mcp_server_uuids",
                "parent_key": "mcp_server_uuid"
            }
        ],
        "wizard_group": [
            {
                "entity_type": "wizard",
                "list_resolver": "resolve_wizard_list",
                "module": "wizard",
                "dependency_key": "wizard_group_uuid",
                "parent_key": "wizard_uuids",
                "direct_clear_parent_ids": True
            }
        ],
        "wizard": [
            {
                "entity_type": "element",
                "list_resolver": "resolve_element_list",
                "module": "element",
                "dependency_key": "element_uuid",
                "parent_key": "element_uuids",
                "direct_clear_parent_ids": True
            }
        ],
        "prompt_template": [
            {
                "entity_type": "ui_component",
                "list_resolver": "resolve_ui_component_list",
                "module": "ui_component",
                "dependency_key": "prompt_uuid"
            },
            {
                "entity_type": "flow_snippet",
                "list_resolver": "resolve_flow_snippet_list",
                "module": "flow_snippet",
                "dependency_key": "prompt_uuid"
            }
        ]
    }

    @classmethod
    def initialize(cls, logger: logging.Logger, **setting: Dict[str, Any]) -> None:
        """
        Initialize configuration setting.
        Args:
            logger (logging.Logger): Logger instance for logging.
            **setting (Dict[str, Any]): Configuration dictionary.
        """
        try:
            cls._set_parameters(setting)
            cls._initialize_aws_services(setting)
            cls._initialize_task_queue(setting)
            cls._initialize_apigw_client(setting)
            if setting.get("test_mode") == "local_for_all":
                cls._initialize_tables(logger)
            logger.info("Configuration initialized successfully.")
        except Exception as e:
            logger.exception("Failed to initialize configuration.")
            raise e

    @classmethod
    def _set_parameters(cls, setting: Dict[str, Any]) -> None:
        """
        Set application-level parameters.
        Args:
            setting (Dict[str, Any]): Configuration dictionary.
        """
        cls.xml_convert = setting.get("xml_convert", False)

    @classmethod
    def _initialize_aws_services(cls, setting: Dict[str, Any]) -> None:
        """
        Initialize AWS services, such as the S3 client.
        Args:
            setting (Dict[str, Any]): Configuration dictionary.
        """
        if all(
            setting.get(k)
            for k in ["region_name", "aws_access_key_id", "aws_secret_access_key"]
        ):
            aws_credentials = {
                "region_name": setting["region_name"],
                "aws_access_key_id": setting["aws_access_key_id"],
                "aws_secret_access_key": setting["aws_secret_access_key"],
            }
        else:
            aws_credentials = {}

        cls.aws_lambda = boto3.client("lambda", **aws_credentials)
        cls.aws_sqs = boto3.resource("sqs", **aws_credentials)
        cls.aws_s3 = boto3.client(
            "s3",
            **aws_credentials,
            config=boto3.session.Config(signature_version="s3v4"),
        )

    @classmethod
    def _initialize_task_queue(cls, setting: Dict[str, Any]) -> None:
        """
        Initialize SQS task queue if task_queue_name is provided in settings.
        Args:
            setting (Dict[str, Any]): Configuration dictionary containing task queue settings.
        """
        if "task_queue_name" in setting:
            cls.task_queue = cls.aws_sqs.get_queue_by_name(
                QueueName=setting["task_queue_name"]
            )

    @classmethod
    def _initialize_apigw_client(cls, setting: Dict[str, Any]) -> None:
        """
        Initialize API Gateway Management API client if required settings are present.
        Args:
            setting (Dict[str, Any]): Configuration dictionary containing API Gateway settings
                                    including api_id, api_stage, region_name and AWS credentials.
        """
        if all(
            setting.get(k)
            for k in [
                "api_id",
                "api_stage",
                "region_name",
                "aws_access_key_id",
                "aws_secret_access_key",
            ]
        ):
            cls.apigw_client = boto3.client(
                "apigatewaymanagementapi",
                endpoint_url=f"https://{setting['api_id']}.execute-api.{setting['region_name']}.amazonaws.com/{setting['api_stage']}",
                region_name=setting["region_name"],
                aws_access_key_id=setting["aws_access_key_id"],
                aws_secret_access_key=setting["aws_secret_access_key"],
            )

    @classmethod
    def _initialize_tables(cls, logger: logging.Logger) -> None:
        """
        Initialize database tables by calling the utils._initialize_tables() method.
        This is an internal method used during configuration setup.
        """
        utils._initialize_tables(logger)

    @classmethod
    def get_cache_name(cls, module_type: str, model_name: str) -> str:
        """
        Generate standardized cache names.

        Args:
            module_type: 'models' or 'queries'
            model_name: Name of the model (e.g., 'agent', 'thread')

        Returns:
            Standardized cache name string
        """
        base_name = cls.CACHE_NAMES.get(
            module_type, f"ai_agent_core_engine.{module_type}"
        )
        return f"{base_name}.{model_name}"

    @classmethod
    def get_cache_ttl(cls) -> int:
        """Get the configured cache TTL."""
        return cls.CACHE_TTL

    @classmethod
    def is_cache_enabled(cls) -> bool:
        """Check if caching is enabled."""
        return cls.CACHE_ENABLED

    @classmethod
    def get_cache_relationships(cls) -> Dict[str, List[Dict[str, str]]]:
        """Get entity cache dependency relationships."""
        return cls.CACHE_RELATIONSHIPS

    @classmethod
    def get_entity_children(cls, entity_type: str) -> List[Dict[str, str]]:
        """Get child entities for a specific entity type."""
        return cls.CACHE_RELATIONSHIPS.get(entity_type, [])

    # Fetches and caches GraphQL schema for a given function
    @classmethod
    def fetch_graphql_schema(
        cls,
        logger: logging.Logger,
        endpoint_id: str,
        function_name: str,
        setting: Dict[str, Any] = {},
    ) -> Dict[str, Any]:
        """
        Fetches and caches a GraphQL schema for a given function.

        Args:
            logger: Logger instance for error reporting
            endpoint_id: ID of the endpoint to fetch schema from
            function_name: Name of function to get schema for
            setting: Optional settings dictionary

        Returns:
            Dict containing the GraphQL schema
        """
        # Check if schema exists in cache, if not fetch and store it
        if Config.schemas.get(function_name) is None:
            Config.schemas[function_name] = Utility.fetch_graphql_schema(
                logger,
                endpoint_id,
                function_name,
                setting=setting,
                aws_lambda=Config.aws_lambda,
                test_mode=setting.get("test_mode"),
            )
        return Config.schemas[function_name]
