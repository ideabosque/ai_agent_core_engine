import os
import uuid

from dotenv import load_dotenv
from locust import HttpUser, between, task

GRAPHQL_QUERY = """
query askModel(
    $agentUuid: String!,
    $threadUuid: String,
    $userQuery: String!,
    $inputFiles: [JSONCamelCase],
    $threadLifeMinutes: Int,
    $userId: String,
    $stream: Boolean,
    $updatedBy: String!
) {
    askModel(
        agentUuid: $agentUuid,
        threadUuid: $threadUuid,
        userQuery: $userQuery,
        inputFiles: $inputFiles,
        threadLifeMinutes: $threadLifeMinutes,
        userId: $userId,
        stream: $stream,
        updatedBy: $updatedBy
    ) {
        agentUuid
        threadUuid
        userQuery
        functionName
        asyncTaskUuid
        currentRunUuid
    }
}
"""

load_dotenv()


class AIAgentUser(HttpUser):
    # Base domain only. Do not include the full path here.
    host = os.getenv("api_url")
    wait_time = between(1, 3)

    def on_start(self):
        self.headers = {
            "x-api-key": os.getenv("x-api-key"),
            "Part-Id": os.getenv("part_id"),
            "Content-Type": "application/json",
        }

        self.agent_uuid = "agent-1758131053-92b0e475"
        self.updated_by = "XYZ"

    @task
    def ask_model(self):
        payload = {
            "query": GRAPHQL_QUERY,
            "variables": {
                "agentUuid": self.agent_uuid,
                "threadUuid": None,
                "userQuery": "Hello",
                "inputFiles": None,
                "threadLifeMinutes": 0,
                "userId": f"user-{uuid.uuid4()}",
                "stream": False,
                "updatedBy": self.updated_by,
            },
        }

        with self.client.post(
            "",
            headers=self.headers,
            json=payload,
            catch_response=True,
            name="askModel",
        ) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}: {response.text}")
                return

            try:
                data = response.json()
            except Exception as e:
                response.failure(f"Invalid JSON response: {e}; body={response.text}")
                return

            if "errors" in data:
                response.failure(f"GraphQL errors: {data['errors']}")
                return

            result = data.get("data", {}).get("askModel")
            if not result:
                response.failure(f"Missing data.askModel in response: {data}")
                return

            required_fields = [
                "agentUuid",
                "threadUuid",
                "userQuery",
                "currentRunUuid",
            ]
            missing = [field for field in required_fields if field not in result]
            if missing:
                response.failure(f"Missing fields in askModel result: {missing}")
                return

            response.success()
