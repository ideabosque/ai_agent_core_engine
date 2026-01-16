#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models import prompt_template
from ..types.prompt_template import PromptTemplateListType, PromptTemplateType


def resolve_prompt_template(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> PromptTemplateType | None:
    return prompt_template.resolve_prompt_template(info, **kwargs)


@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("queries", "prompt_template"),
    cache_enabled=Config.is_cache_enabled,
)
def resolve_prompt_template_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> PromptTemplateListType | None:
    return prompt_template.resolve_prompt_template_list(info, **kwargs)