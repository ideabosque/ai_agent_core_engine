#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Standalone script to run chatbot tests individually.

Usage:
    python run_chatbot.py --mode local
    python run_chatbot.py --mode request
    python run_chatbot.py --mode local --agent-uuid agent-1764104706-a4356066
    python run_chatbot.py --mode local --user-id user@example.com --updated-by admin
"""

from __future__ import print_function

__author__ = "bibow"

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Add parent directory to path to allow imports when running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../openai_agent_handler")
    ),
)
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../ai_agent_handler")
    ),
)
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../mcp_http_client")
    ),
)
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../silvaengine_utility")
    ),
)
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../silvaengine_dynamodb_base")
    ),
)

# Setup logging
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()

from ai_agent_core_engine import AIAgentCoreEngine
from silvaengine_utility import Graphql, Serializer


class ChatbotRunner:
    """Runner class for chatbot tests."""

    def __init__(self, agent_uuid=None, user_id=None, updated_by=None):
        """Initialize the chatbot runner."""
        self.setting = {
            "region_name": os.getenv("region_name"),
            "aws_access_key_id": os.getenv("aws_access_key_id"),
            "aws_secret_access_key": os.getenv("aws_secret_access_key"),
            "api_id": os.getenv("api_id"),
            "api_stage": os.getenv("api_stage"),
            "funct_bucket_name": os.getenv("funct_bucket_name"),
            "funct_zip_path": os.getenv("funct_zip_path"),
            "funct_extract_path": os.getenv("funct_extract_path"),
            "task_queue_name": os.getenv("task_queue_name"),
            "functs_on_local": {
                "ai_marketing_graphql": {
                    "module_name": "ai_marketing_engine",
                    "class_name": "AIMarketingEngine",
                },
                "ai_agent_build_graphql_query": {
                    "module_name": "ai_agent_core_engine",
                    "class_name": "AIAgentCoreEngine",
                },
                "ai_agent_core_graphql": {
                    "module_name": "ai_agent_core_engine",
                    "class_name": "AIAgentCoreEngine",
                },
                "async_execute_ask_model": {
                    "module_name": "ai_agent_core_engine",
                    "class_name": "AIAgentCoreEngine",
                },
                "async_insert_update_tool_call": {
                    "module_name": "ai_agent_core_engine",
                    "class_name": "AIAgentCoreEngine",
                },
                "send_data_to_websocket": {
                    "module_name": "ai_agent_core_engine",
                    "class_name": "AIAgentCoreEngine",
                },
            },
            "xml_convert": os.getenv("xml_convert", False),
            "internal_mcp": {
                "base_url": os.getenv("mcp_server_url"),
                "bearer_token": os.getenv("bearer_token"),
                "headers": {
                    "x-api-key": os.getenv("x-api-key"),
                    "Content-Type": "application/json",
                },
            },
            "connection_id": os.getenv("connection_id"),
            "endpoint_id": os.getenv("endpoint_id"),
            "part_id": os.getenv("part_id"),
            "execute_mode": os.getenv("execute_mode"),
            "initialize_tables": int(os.getenv("initialize_tables", "0")),
        }

        self.ai_agent_core_engine = AIAgentCoreEngine(logger, **self.setting)
        context = {
            "endpoint_id": self.setting.get("endpoint_id"),
            "setting": self.setting,
            "logger": logger,
        }
        self.schema = Graphql.fetch_graphql_schema(
            context,
            "ai_agent_core_graphql",
        )

        # Set default parameters or use provided ones
        self.agent_uuid = agent_uuid or os.getenv(
            "DEFAULT_AGENT_UUID", "agent-1764104706-a4356066"
        )
        self.user_id = user_id or os.getenv("DEFAULT_USER_ID", "bibo72@outlook.com")
        self.updated_by = updated_by or os.getenv("DEFAULT_UPDATED_BY", "XYZ")

    def run_chatbot_on_local(self):
        """Run chatbot test on local mode."""
        thread_uuid = None

        while True:
            user_input = input("User: ")
            if user_input.strip().lower() in ["exit", "quit"]:
                logger.info("User requested exit. Stopping the chatbot.")
                print("Chatbot: Goodbye!")
                break

            query = Graphql.generate_graphql_operation("askModel", "Query", self.schema)
            payload = {
                "query": query,
                "variables": {
                    "agentUuid": self.agent_uuid,
                    "threadUuid": thread_uuid,
                    "userQuery": user_input,
                    "userId": self.user_id,
                    "stream": True,
                    "updatedBy": self.updated_by,
                },
            }
            response = self.ai_agent_core_engine.ai_agent_core_graphql(**payload)
            response = Serializer.json_loads(response["body"])

            if response["askModel"]["threadUuid"] is not None:
                thread_uuid = response["askModel"]["threadUuid"]

            query = Graphql.generate_graphql_operation(
                "asyncTask", "Query", self.schema
            )
            payload = {
                "query": query,
                "variables": {
                    "functionName": "async_execute_ask_model",
                    "asyncTaskUuid": response["askModel"]["asyncTaskUuid"],
                },
            }

            response = self.ai_agent_core_engine.ai_agent_core_graphql(**payload)
            response = Serializer.json_loads(response["body"])

            # Print response to user
            print(f"Chatbot: {response['asyncTask']['result']}\n")

    def run_chatbot_by_request(self):
        """Run chatbot test by request mode."""
        import requests

        url = os.getenv("api_url")
        headers = {
            "x-api-key": os.getenv("api_key"),
            "Content-Type": "application/json",
        }

        ask_model_query = """query askModel($agentUuid: String!, $threadUuid: String, $userId: String, $userQuery: String!, $stream: Boolean, $updatedBy: String!) {
            askModel(agentUuid: $agentUuid, threadUuid: $threadUuid, userId: $userId, userQuery: $userQuery, stream: $stream, updatedBy: $updatedBy) {
                agentUuid threadUuid userQuery functionName asyncTaskUuid currentRunUuid
            }
        }"""
        async_task_query = """query asyncTask($functionName: String!, $asyncTaskUuid: String!) {
            asyncTask(functionName: $functionName, asyncTaskUuid: $asyncTaskUuid) {
                functionName asyncTaskUuid endpointId arguments result status notes timeSpent updatedBy createdAt updatedAt
            }
        }"""

        thread_uuid = None
        while True:
            user_input = input("User: ")
            if user_input.strip().lower() in ["exit", "quit"]:
                logger.info("User requested exit. Stopping the chatbot.")
                print("Chatbot: Goodbye!")
                break

            payload = {
                "query": ask_model_query,
                "variables": {
                    "agentUuid": self.agent_uuid,
                    "threadUuid": thread_uuid,
                    "userQuery": user_input,
                    "userId": self.user_id,
                    "stream": True,
                    "updatedBy": self.updated_by,
                },
            }

            response = requests.post(url, headers=headers, json=payload)
            response = response.json()

            if response["data"]["askModel"]["threadUuid"] is not None:
                thread_uuid = response["data"]["askModel"]["threadUuid"]

            payload = {
                "query": async_task_query,
                "variables": {
                    "functionName": "async_execute_ask_model",
                    "asyncTaskUuid": response["data"]["askModel"]["asyncTaskUuid"],
                },
            }

            while True:
                response = requests.post(url, headers=headers, json=payload)
                response = response.json()
                if response["data"]["asyncTask"]["status"] in ["completed", "failed"]:
                    break

            # Print response to user
            print(f"Chatbot: {response['data']['asyncTask']['result']}\n")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Run chatbot tests individually",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --mode local
  %(prog)s --mode request
  %(prog)s --mode local --agent-uuid agent-1764104706-a4356066
  %(prog)s --mode request --agent-uuid agent-1758131053-92b0e475
  %(prog)s --mode local --agent-uuid agent-123 --user-id user@example.com --updated-by admin
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["local", "request"],
        default=os.getenv("RUN_CHATBOT_MODE", "local"),
        help="Test mode: 'local' for local execution or 'request' for API requests",
    )
    parser.add_argument(
        "--agent-uuid",
        default=os.getenv("DEFAULT_AGENT_UUID"),
        help="Agent UUID to use for testing (overrides default)",
    )
    parser.add_argument(
        "--user-id",
        default=os.getenv("DEFAULT_USER_ID"),
        help="User ID for the chatbot session (overrides default)",
    )
    parser.add_argument(
        "--updated-by",
        default=os.getenv("DEFAULT_UPDATED_BY"),
        help="Updated by field for tracking changes (overrides default)",
    )

    args = parser.parse_args()

    try:
        runner = ChatbotRunner(
            agent_uuid=args.agent_uuid,
            user_id=args.user_id,
            updated_by=args.updated_by,
        )

        if args.mode == "local":
            runner.run_chatbot_on_local()
        elif args.mode == "request":
            runner.run_chatbot_by_request()

    except KeyboardInterrupt:
        logger.info("\nChatbot stopped by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running chatbot: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
