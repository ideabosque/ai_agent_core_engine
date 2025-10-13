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
from .mutations.ai_agent import ExecuteAskModel, UploadFile
from .mutations.async_task import DeleteAsyncTask, InsertUpdateAsyncTask
from .mutations.element import DeleteElement, InsertUpdateElement
from .mutations.fine_tuning_message import (
    DeleteFineTuningMessage,
    InsertUpdateFineTuningMessage,
)
from .mutations.flow_snippet import DeleteFlowSnippet, InsertUpdateFlowSnippet
from .mutations.llm import DeleteLlm, InsertUpdateLlm
from .mutations.mcp_server import DeleteMCPServer, InsertUpdateMCPServer
from .mutations.message import DeleteMessage, InsertUpdateMessage
from .mutations.prompt_template import DeletePromptTemplate, InsertUpdatePromptTemplate
from .mutations.run import DeleteRun, InsertUpdateRun
from .mutations.thread import DeleteThread, InsertThread
from .mutations.tool_call import DeleteToolCall, InsertUpdateToolCall
from .mutations.ui_component import DeleteUIComponent, InsertUpdateUIComponent
from .mutations.wizard import DeleteWizard, InsertUpdateWizard
from .mutations.wizard_schema import DeleteWizardSchema, InsertUpdateWizardSchema
from .mutations.wizard_group import DeleteWizardGroup, InsertUpdateWizardGroup
from .queries.agent import resolve_agent, resolve_agent_list
from .queries.ai_agent import (
    resolve_ask_model,
    resolve_output_file,
    resolve_presigned_aws_s3_url,
    resolve_uploaded_file,
)
from .queries.async_task import resolve_async_task, resolve_async_task_list
from .queries.element import resolve_element, resolve_element_list
from .queries.fine_tuning_message import (
    resolve_fine_tuning_message,
    resolve_fine_tuning_message_list,
)
from .queries.flow_snippet import resolve_flow_snippet, resolve_flow_snippet_list
from .queries.llm import resolve_llm, resolve_llm_list
from .queries.mcp_server import resolve_mcp_server, resolve_mcp_server_list
from .queries.message import resolve_message, resolve_message_list
from .queries.prompt_template import (
    resolve_prompt_template,
    resolve_prompt_template_list,
)
from .queries.run import resolve_run, resolve_run_list
from .queries.thread import resolve_thread, resolve_thread_list
from .queries.tool_call import resolve_tool_call, resolve_tool_call_list
from .queries.ui_component import resolve_ui_component, resolve_ui_component_list
from .queries.wizard import resolve_wizard, resolve_wizard_list
from .queries.wizard_schema import resolve_wizard_schema, resolve_wizard_schema_list
from .queries.wizard_group import resolve_wizard_group, resolve_wizard_group_list
from .types.agent import AgentListType, AgentType
from .types.ai_agent import AskModelType, FileType, PresignedAWSS3UrlType
from .types.async_task import AsyncTaskListType, AsyncTaskType
from .types.element import ElementListType, ElementType
from .types.fine_tuning_message import FineTuningMessageListType, FineTuningMessageType
from .types.flow_snippet import FlowSnippetListType, FlowSnippetType
from .types.llm import LlmListType, LlmType
from .types.mcp_server import MCPServerListType, MCPServerType
from .types.message import MessageListType, MessageType
from .types.prompt_template import PromptTemplateListType, PromptTemplateType
from .types.run import RunListType, RunType
from .types.thread import ThreadListType, ThreadType
from .types.tool_call import ToolCallListType, ToolCallType
from .types.ui_component import UIComponentListType, UIComponentType
from .types.wizard import WizardListType, WizardType
from .types.wizard_schema import WizardSchemaListType, WizardSchemaType
from .types.wizard_group import WizardGroupListType, WizardGroupType


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
        ElementType,
        ElementListType,
        WizardType,
        WizardListType,
        WizardSchemaType,
        WizardSchemaListType,
        WizardGroupType,
        WizardGroupListType,
        MCPServerType,
        MCPServerListType,
        UIComponentType,
        UIComponentListType,
        FlowSnippetType,
        FlowSnippetListType,
        PromptTemplateType,
        PromptTemplateListType,
        AskModelType,
        FileType,
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
        statuses=List(String, required=False),
        flow_snippet_version_uuid=String(required=False),
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
        input_files=List(JSON, required=False),
        stream=Boolean(required=False),
        updated_by=String(required=True),
    )

    uploaded_file = Field(
        FileType,
        agent_uuid=String(required=True),
        arguments=JSON(required=True),
    )

    output_file = Field(
        FileType,
        agent_uuid=String(required=True),
        arguments=JSON(required=True),
    )

    element = Field(
        ElementType,
        element_uuid=String(required=True),
    )

    element_list = Field(
        ElementListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        data_type=String(required=False),
        attribute_name=String(required=False),
    )

    wizard = Field(
        WizardType,
        wizard_uuid=String(required=True),
    )

    wizard_list = Field(
        WizardListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        wizard_type=String(required=False),
        wizard_title=String(required=False),
    )

    wizard_schema = Field(
        WizardSchemaType,
        wizard_schema_type=String(required=True),
        wizard_schema_name=String(required=True),
    )

    wizard_schema_list = Field(
        WizardSchemaListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        wizard_schema_type=String(required=False),
        wizard_schema_name=String(required=False),
    )

    wizard_group = Field(
        WizardGroupType,
        wizard_group_uuid=String(required=True),
    )

    wizard_group_list = Field(
        WizardGroupListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        wizard_group_name=String(required=False),
    )

    mcp_server = Field(
        MCPServerType,
        mcp_server_uuid=String(required=True),
    )

    mcp_server_list = Field(
        MCPServerListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        mcp_label=String(required=False),
    )

    ui_component = Field(
        UIComponentType,
        ui_component_type=String(required=True),
        ui_component_uuid=String(required=True),
    )

    ui_component_list = Field(
        UIComponentListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        ui_component_type=String(required=False),
        tag_name=String(required=False),
    )

    flow_snippet = Field(
        FlowSnippetType,
        flow_snippet_version_uuid=String(required=False),
        flow_snippet_uuid=String(required=False),
    )

    flow_snippet_list = Field(
        FlowSnippetListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        flow_snippet_uuid=String(required=False),
        prompt_uuid=String(required=False),
        flow_name=String(required=False),
        statuses=List(String, required=False),
    )

    prompt_template = Field(
        PromptTemplateType,
        prompt_version_uuid=String(required=False),
        prompt_uuid=String(required=False),
    )

    prompt_template_list = Field(
        PromptTemplateListType,
        page_number=Int(required=False),
        limit=Int(required=False),
        prompt_uuid=String(required=False),
        prompt_type=String(required=False),
        prompt_name=String(required=False),
        statuses=List(String, required=False),
    )

    presigned_aws_s3_url = Field(
        PresignedAWSS3UrlType,
        required=True,
        client_method=String(required=False),
        object_key=String(required=True),
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

    def resolve_uploaded_file(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> FileType:
        return resolve_uploaded_file(info, **kwargs)

    def resolve_output_file(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> FileType:
        return resolve_output_file(info, **kwargs)

    def resolve_element(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> ElementType:
        return resolve_element(info, **kwargs)

    def resolve_element_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> ElementListType:
        return resolve_element_list(info, **kwargs)

    def resolve_wizard(self, info: ResolveInfo, **kwargs: Dict[str, Any]) -> WizardType:
        return resolve_wizard(info, **kwargs)

    def resolve_wizard_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> WizardListType:
        return resolve_wizard_list(info, **kwargs)

    def resolve_wizard_schema(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> WizardSchemaType:
        return resolve_wizard_schema(info, **kwargs)

    def resolve_wizard_schema_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> WizardSchemaListType:
        return resolve_wizard_schema_list(info, **kwargs)

    def resolve_wizard_group(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> WizardGroupType:
        return resolve_wizard_group(info, **kwargs)

    def resolve_wizard_group_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> WizardGroupListType:
        return resolve_wizard_group_list(info, **kwargs)

    def resolve_mcp_server(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> MCPServerType:
        return resolve_mcp_server(info, **kwargs)

    def resolve_mcp_server_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> MCPServerListType:
        return resolve_mcp_server_list(info, **kwargs)

    def resolve_ui_component(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> UIComponentType:
        return resolve_ui_component(info, **kwargs)

    def resolve_ui_component_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> UIComponentListType:
        return resolve_ui_component_list(info, **kwargs)

    def resolve_flow_snippet(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> FlowSnippetType:
        return resolve_flow_snippet(info, **kwargs)

    def resolve_flow_snippet_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> FlowSnippetListType:
        return resolve_flow_snippet_list(info, **kwargs)

    def resolve_prompt_template(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> PromptTemplateType:
        return resolve_prompt_template(info, **kwargs)

    def resolve_prompt_template_list(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> PromptTemplateListType:
        return resolve_prompt_template_list(info, **kwargs)

    def resolve_presigned_aws_s3_url(
        self, info: ResolveInfo, **kwargs: Dict[str, Any]
    ) -> PresignedAWSS3UrlType:
        return resolve_presigned_aws_s3_url(info, **kwargs)


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
    upload_file = UploadFile.Field()
    insert_update_element = InsertUpdateElement.Field()
    delete_element = DeleteElement.Field()
    insert_update_wizard = InsertUpdateWizard.Field()
    delete_wizard = DeleteWizard.Field()
    insert_update_wizard_schema = InsertUpdateWizardSchema.Field()
    delete_wizard_schema = DeleteWizardSchema.Field()
    insert_update_wizard_group = InsertUpdateWizardGroup.Field()
    delete_wizard_group = DeleteWizardGroup.Field()
    insert_update_mcp_server = InsertUpdateMCPServer.Field()
    delete_mcp_server = DeleteMCPServer.Field()
    insert_update_ui_component = InsertUpdateUIComponent.Field()
    delete_ui_component = DeleteUIComponent.Field()
    insert_update_flow_snippet = InsertUpdateFlowSnippet.Field()
    delete_flow_snippet = DeleteFlowSnippet.Field()
    insert_update_prompt_template = InsertUpdatePromptTemplate.Field()
    delete_prompt_template = DeletePromptTemplate.Field()
