#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import prompt_template
from ..types.prompt_template import PromptTemplateListType, PromptTemplateType


def resolve_prompt_template(info: ResolveInfo, **kwargs: Dict[str, Any]) -> PromptTemplateType:
    return prompt_template.resolve_prompt_template(info, **kwargs)


def resolve_prompt_template_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> PromptTemplateListType:
    return prompt_template.resolve_prompt_template_list(info, **kwargs)