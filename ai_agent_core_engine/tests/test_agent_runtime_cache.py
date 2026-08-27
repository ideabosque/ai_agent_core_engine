# -*- coding: utf-8 -*-
from __future__ import print_function

from types import SimpleNamespace

from ai_agent_core_engine.handlers.ai_agent import _get_agent, clear_cached_agent
from ai_agent_core_engine.handlers.ai_agent_utility import _handler_cache


def test_clear_cached_agent_removes_matching_agent_and_handler_cache():
    _get_agent._cache = {
        ("endpoint-a", "part-a", "agent-1"): (SimpleNamespace(agent_uuid="agent-1"), 1),
        ("endpoint-a", "part-a", "agent-2"): (SimpleNamespace(agent_uuid="agent-2"), 1),
        ("endpoint-b", "part-b", "agent-1"): (SimpleNamespace(agent_uuid="agent-1"), 1),
    }
    _handler_cache.clear()
    _handler_cache.update(
        {
            ("endpoint-a", "part-a", "agent-1"): (object(), 1),
            ("endpoint-a", "part-a", "agent-2"): (object(), 1),
            ("endpoint-b", "part-b", "agent-1"): (object(), 1),
        }
    )

    clear_cached_agent(
        agent_uuid="agent-1",
        partition_key="endpoint-a#part-a",
    )

    assert ("endpoint-a", "part-a", "agent-1") not in _get_agent._cache
    assert ("endpoint-a", "part-a", "agent-1") not in _handler_cache
    assert ("endpoint-a", "part-a", "agent-2") in _get_agent._cache
    assert ("endpoint-a", "part-a", "agent-2") in _handler_cache
    assert ("endpoint-b", "part-b", "agent-1") in _get_agent._cache
    assert ("endpoint-b", "part-b", "agent-1") in _handler_cache


def test_clear_cached_agent_falls_back_to_agent_uuid_when_tenant_unknown():
    _get_agent._cache = {
        ("endpoint-a", "part-a", "agent-1"): (SimpleNamespace(agent_uuid="agent-1"), 1),
        ("endpoint-b", "part-b", "agent-1"): (SimpleNamespace(agent_uuid="agent-1"), 1),
        ("endpoint-a", "part-a", "agent-2"): (SimpleNamespace(agent_uuid="agent-2"), 1),
    }
    _handler_cache.clear()
    _handler_cache.update(
        {
            ("endpoint-a", "part-a", "agent-1"): (object(), 1),
            ("endpoint-b", "part-b", "agent-1"): (object(), 1),
            ("endpoint-a", "part-a", "agent-2"): (object(), 1),
        }
    )

    clear_cached_agent(agent_uuid="agent-1")

    assert ("endpoint-a", "part-a", "agent-1") not in _get_agent._cache
    assert ("endpoint-b", "part-b", "agent-1") not in _get_agent._cache
    assert ("endpoint-a", "part-a", "agent-1") not in _handler_cache
    assert ("endpoint-b", "part-b", "agent-1") not in _handler_cache
    assert ("endpoint-a", "part-a", "agent-2") in _get_agent._cache
    assert ("endpoint-a", "part-a", "agent-2") in _handler_cache


def test_prompt_template_loader_uses_active_prompt_cache(monkeypatch):
    from ai_agent_core_engine.models.dynamodb.batch_loaders import prompt_template_loader

    cache_names = []

    class DummyCache:
        def __init__(self, cache_name):
            cache_names.append(cache_name)

    monkeypatch.setattr(prompt_template_loader, "HybridCacheEngine", DummyCache)

    prompt_template_loader.PromptTemplateLoader(cache_enabled=True)

    assert cache_names == ["ai_agent_core_engine.models.dynamodb.dynamodb.active_prompt_template"]


def test_tool_calls_by_thread_loader_reads_generated_cache_key():
    from ai_agent_core_engine.models.dynamodb.batch_loaders.tool_calls_by_thread_loader import (
        ToolCallsByThreadLoader,
    )

    loader = ToolCallsByThreadLoader(cache_enabled=False)
    calls = []

    def fake_get_cache_data(key):
        calls.append(key)
        return [{"thread_uuid": key, "tool_call_uuid": "tc-1"}]

    loader.cache_enabled = True
    loader.get_cache_data = fake_get_cache_data

    result = loader.batch_load_fn(["thread-1"]).get()

    assert calls == ["thread-1"]
    assert result == [[{"thread_uuid": "thread-1", "tool_call_uuid": "tc-1"}]]
