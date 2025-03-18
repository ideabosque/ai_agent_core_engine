#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import time
from typing import Any, Dict

from graphene import (
    Boolean,
    DateTime,
    Field,
    Int,
    List,
    ObjectType,
    ResolveInfo,
    String,
)

from silvaengine_utility import JSON

from .mutations.agent import DeleteAgent, InsertUpdateAgent
from .mutations.ai_agent import ExecuteAskModel
from .mutations.async_task import DeleteAsyncTask, InsertUpdateAsyncTask
from .mutations.fine_tuning_message import (
    DeleteFineTuningMessage,
    InsertUpdateFineTuningMessage,
)
from .mutations.llm import DeleteLlm, InsertUpdateLlm
from .mutations.message import DeleteMessage, InsertUpdateMessage
from .mutations.run import DeleteRun, InsertUpdateRun
from .mutations.thread import DeleteThread, InsertThread
from .mutations.tool_call import DeleteToolCall, InsertUpdateToolCall
from .queries.agent import resolve_agent, resolve_agent_list
from .queries.ai_agent import resolve_ask_model
from .queries.async_task import resolve_async_task, resolve_async_task_list
from .queries.fine_tuning_message import (
    resolve_fine_tuning_message,
    resolve_fine_tuning_message_list,
)
from .queries.llm import resolve_llm, resolve_llm_list
from .queries.message import resolve_message, resolve_message_list
from .queries.run import resolve_run, resolve_run_list
from .queries.thread import resolve_thread, resolve_thread_list
from .queries.tool_call import resolve_tool_call, resolve_tool_call_list
from .types.agent import AgentListType, AgentType
from .types.ai_agent import AskModelType
from .types.async_task import AsyncTaskListType, AsyncTaskType
from .types.fine_tuning_message import FineTuningMessageListType, FineTuningMessageType
from .types.llm import LlmListType, LlmType
from .types.message import MessageListType, MessageType
from .types.run import RunListType, RunType
from .types.thread import ThreadListType, ThreadType
from .types.tool_call import ToolCallListType, ToolCallType


def type_class():
    return [
        LlmType,
        LlmListType,
        AgentListType,
        AgentType,
        ThreadType,
        ThreadListType,
        RunType,
        RunListType,
        ToolCallType,
        ToolCallListType,
        MessageType,
        MessageListType,
        AsyncTaskType,
        AsyncTaskListType,
        FineTuningMessageType,
        FineTuningMessageListType,
        AskModelType,
    ]


class Query(ObjectType):
    ping = String()

    llm = Field(
        LlmType,
        llm_provider=String(required=True),
        llm_name=String(required=True),
    )

    llm_list = Field(
        LlmListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        llm_provider=String(required=False),
        module_name=String(required=False),
        class_name=String(required=False),
    )

    agent = Field(
        AgentType,
        agent_uuid=String(required=False),
        agent_version_uuid=String(required=False),
    )

    agent_list = Field(
        AgentListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        agent_uuid=String(required=False),
        agent_name=String(required=False),
        llm_provider=String(required=False),
        llm_name=String(required=False),
        model=String(required=False),
        statues=List(String, required=False),
    )

    thread = Field(
        ThreadType,
        thread_uuid=String(required=True),
    )

    thread_list = Field(
        ThreadListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        agent_uuid=String(required=False),
        user_id=String(required=False),
    )

    run = Field(
        RunType,
        thread_uuid=String(required=True),
        run_uuid=String(required=True),
    )

    run_list = Field(
        RunListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        thread_uuid=String(required=False),
        run_id=String(required=False),
        token_type=String(required=False),
        great_token=Int(required=False),
        less_token=Int(required=False),
    )

    tool_call = Field(
        ToolCallType,
        thread_uuid=String(required=True),
        tool_call_uuid=String(required=True),
    )

    tool_call_list = Field(
        ToolCallListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        thread_uuid=String(required=False),
        run_uuid=String(required=False),
        tool_call_id=String(required=False),
        tool_type=Int(required=False),
        name=Int(required=False),
        statues=List(String, required=False),
    )

    message = Field(
        MessageType,
        thread_uuid=String(required=True),
        message_uuid=String(required=True),
    )

    message_list = Field(
        MessageListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        thread_uuid=String(required=False),
        run_uuid=String(required=False),
        message_id=String(required=False),
        roles=List(String, required=False),
    )

    async_task = Field(
        AsyncTaskType,
        function_name=String(required=True),
        async_task_uuid=String(required=True),
    )

    async_task_list = Field(
        AsyncTaskListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        function_name=String(required=False),
        statues=List(String, required=False),
    )

    fine_tuning_message = Field(
        FineTuningMessageType,
        agent_uuid=String(required=True),
        message_uuid=String(required=True),
    )

    fine_tuning_message_list = Field(
        FineTuningMessageListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        agent_uuid=String(required=False),
        thread_uuid=String(required=False),
        roles=List(String, required=False),
        trained=Boolean(required=False),
        from_date=DateTime(required=False),
        to_date=DateTime(required=False),
    )

    ask_model = Field(
        AskModelType,
        agent_uuid=String(required=True),
        thread_uuid=String(required=False),
        user_query=String(required=True),
        stream=Boolean(required=False),
        updated_by=String(required=True),
    )

    def resolve_ping(self, info: ResolveInfo) -> str:
        return f"Hello at {time.strftime('%X')}!!"

    def resolve_llm(self, info: ResolveInfo, **kwargs: Dict[str, Any]) -> LlmType:
        return resolve_llm(info, **kwargs)

    def resolve_llm_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> LlmListType:
        return resolve_llm_list(info, **kwargs)

    def resolve_agent(self, info: ResolveInfo, **kwargs: Dict[str, Any]) -> AgentType:
        return resolve_agent(info, **kwargs)

    def resolve_agent_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> AgentListType:
        return resolve_agent_list(info, **kwargs)

    def resolve_thread(self, info: ResolveInfo, **kwargs: Dict[str, Any]) -> ThreadType:
        return resolve_thread(info, **kwargs)

    def resolve_thread_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> ThreadListType:
        return resolve_thread_list(info, **kwargs)

    def resolve_run(self, info: ResolveInfo, **kwargs: Dict[str, Any]) -> RunType:
        return resolve_run(info, **kwargs)

    def resolve_run_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> RunListType:
        return resolve_run_list(info, **kwargs)

    def resolve_tool_call(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> ToolCallType:
        return resolve_tool_call(info, **kwargs)

    def resolve_tool_call_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> ToolCallListType:
        return resolve_tool_call_list(info, **kwargs)

    def resolve_message(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> MessageType:
        return resolve_message(info, **kwargs)

    def resolve_message_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> MessageListType:
        return resolve_message_list(info, **kwargs)

    def resolve_async_task(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> AsyncTaskType:
        return resolve_async_task(info, **kwargs)

    def resolve_async_task_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> AsyncTaskListType:
        return resolve_async_task_list(info, **kwargs)

    def resolve_fine_tuning_message(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> FineTuningMessageType:
        return resolve_fine_tuning_message(info, **kwargs)

    def resolve_fine_tuning_message_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> FineTuningMessageListType:
        return resolve_fine_tuning_message_list(info, **kwargs)

    def resolve_ask_model(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> AskModelType:
        return resolve_ask_model(info, **kwargs)


class Mutations(ObjectType):
    insert_update_llm = InsertUpdateLlm.Field()
    delete_llm = DeleteLlm.Field()
    insert_update_agent = InsertUpdateAgent.Field()
    delete_agent = DeleteAgent.Field()
    insert_thread = InsertThread.Field()
    delete_thread = DeleteThread.Field()
    insert_update_run = InsertUpdateRun.Field()
    delete_run = DeleteRun.Field()
    insert_update_message = InsertUpdateMessage.Field()
    delete_message = DeleteMessage.Field()
    insert_update_tool_call = InsertUpdateToolCall.Field()
    delete_tool_call = DeleteToolCall.Field()
    insert_update_fine_tuning_message = InsertUpdateFineTuningMessage.Field()
    delete_fine_tuning_message = DeleteFineTuningMessage.Field()
    insert_update_async_task = InsertUpdateAsyncTask.Field()
    delete_async_task = DeleteAsyncTask.Field()
    execute_ask_model = ExecuteAskModel.Field()
