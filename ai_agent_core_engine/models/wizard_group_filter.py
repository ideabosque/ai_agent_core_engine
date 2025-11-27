#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import traceback
from typing import Any, Dict, List

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import (
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
)
from tenacity import retry, stop_after_attempt, wait_exponential

from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Utility


class WizardGroupFilterModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-wizard_group_filters"

    endpoint_id = UnicodeAttribute(hash_key=True)
    wizard_group_filter_uuid = UnicodeAttribute(range_key=True)
    wizard_group_filter_name = UnicodeAttribute()
    wizard_group_filter_description = UnicodeAttribute(null=True)
    region = UnicodeAttribute()
    criteria = MapAttribute()
    weight = NumberAttribute(default=0)
    wizard_group_uuid = UnicodeAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
