#!/usr/bin/python
# -*- coding: utf-8 -*-
"""DynamoDB usage models and helpers (usage_limit / usage_summary).

This module is the DynamoDB backend for the usage-tracking facade in
``ai_agent_core_engine.models.usage``.  It is only imported when
``Config.DB_BACKEND == "dynamodb"`` (or by the DynamoDB table initializer).
"""
from __future__ import print_function

__author__ = "jeffreyw"

import pendulum
from pynamodb.attributes import (
    BooleanAttribute,
    NumberAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.exceptions import UpdateError

from silvaengine_dynamodb_base import BaseModel


class UsageLimitModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-usage_limit"

    partition_key = UnicodeAttribute(hash_key=True)
    usage_key = UnicodeAttribute(range_key=True)

    usage_limit = NumberAttribute()
    allow_overage = BooleanAttribute()
    period_start = UTCDateTimeAttribute()
    period_end = UTCDateTimeAttribute()

    created_from = UnicodeAttribute()
    status = UnicodeAttribute()

    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


class UsageSummaryModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-usage_summary"

    partition_key = UnicodeAttribute(hash_key=True)
    usage_key_period_start = UnicodeAttribute(range_key=True)

    usage_key = UnicodeAttribute()
    total = NumberAttribute()


def add_usage_summary(
    partition_key: str, usage_key: str, usage_key_period_start: str, limit: int
) -> None:
    """Atomically increment the period total, rejecting once it reaches ``limit``."""
    try:
        UsageSummaryModel(partition_key, usage_key_period_start).update(
            actions=[
                UsageSummaryModel.usage_key.set(usage_key),
                UsageSummaryModel.total.add(1),
            ],
            condition=(UsageSummaryModel.total < limit)
            | (UsageSummaryModel.total.does_not_exist()),
        )
    except UpdateError:
        raise Exception("Usage Limit Exceeded")


def get_usage_limit(partition_key: str, usage_key: str):
    """Return the usage_limit row (or ``None`` when absent)."""
    try:
        return UsageLimitModel.get(partition_key, usage_key)
    except Exception:
        return None


def insert_update_usage_limit(**kwargs):
    partition_key = kwargs.get("partition_key")
    usage_key = kwargs.get("usage_key")
    entity = get_usage_limit(partition_key, usage_key)
    if entity is None:
        cols = {
            "usage_limit": kwargs.get("usage_limit"),
            "allow_overage": kwargs.get("allow_overage"),
            "period_start": kwargs.get("period_start"),
            "period_end": kwargs.get("period_end"),
            "created_from": kwargs.get("created_from"),
            "status": kwargs.get("status"),
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }

        UsageLimitModel(
            partition_key,
            usage_key,
            **cols,
        ).save()
        return

    actions = [
        UsageLimitModel.updated_at.set(pendulum.now("UTC")),
    ]
    field_map = {
        "usage_limit": UsageLimitModel.usage_limit,
        "allow_overage": UsageLimitModel.allow_overage,
        "period_start": UsageLimitModel.period_start,
        "period_end": UsageLimitModel.period_end,
        "created_from": UsageLimitModel.created_from,
        "status": UsageLimitModel.status,
    }

    for key, field in field_map.items():
        if key in kwargs:
            actions.append(field.set(kwargs[key]))

    entity.update(actions=actions)
    return


__all__ = [
    "UsageLimitModel",
    "UsageSummaryModel",
    "add_usage_summary",
    "get_usage_limit",
    "insert_update_usage_limit",
]
