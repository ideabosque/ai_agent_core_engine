#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import functools
import logging
import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import (
    ListAttribute,
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
from silvaengine_utility import Utility, method_cache

from ..handlers.config import Config
from ..types.wizard import WizardListType, WizardType
from .utils import _get_element


class WizardModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-wizards"

    endpoint_id = UnicodeAttribute(hash_key=True)
    wizard_uuid = UnicodeAttribute(range_key=True)
    wizard_title = UnicodeAttribute()
    wizard_description = UnicodeAttribute(null=True)
    wizard_type = UnicodeAttribute()
    form_schema = UnicodeAttribute(null=True)
    priority = NumberAttribute(default=0)
    element_uuids = ListAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


def purge_cache():
    def actual_decorator(original_function):
        @functools.wraps(original_function)
        def wrapper_function(*args, **kwargs):
            try:
                # Use cascading cache purging for wizards
                from ..models.cache import purge_entity_cascading_cache

                try:
                    wizard = resolve_wizard(args[0], **kwargs)
                except Exception as e:
                    wizard = None

                endpoint_id = args[0].context.get("endpoint_id") or kwargs.get(
                    "endpoint_id"
                )
                entity_keys = {}
                if kwargs.get("wizard_uuid"):
                    entity_keys["wizard_uuid"] = kwargs.get("wizard_uuid")
                if wizard and wizard.elements:
                    entity_keys["element_uuids"] = [
                        element["element_uuid"] for element in wizard.elements
                    ]

                result = purge_entity_cascading_cache(
                    args[0].context.get("logger"),
                    entity_type="wizard",
                    context_keys={"endpoint_id": endpoint_id} if endpoint_id else None,
                    entity_keys=entity_keys if entity_keys else None,
                    cascade_depth=3,
                )

                ## Original function.
                result = original_function(*args, **kwargs)

                return result
            except Exception as e:
                log = traceback.format_exc()
                args[0].context.get("logger").error(log)
                raise e

        return wrapper_function

    return actual_decorator


def create_wizard_table(logger: logging.Logger) -> bool:
    """Create the Wizard table if it doesn't exist."""
    if not WizardModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        WizardModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The Wizard table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(
    ttl=Config.get_cache_ttl(), cache_name=Config.get_cache_name("models", "wizard")
)
def get_wizard(endpoint_id: str, wizard_uuid: str) -> WizardModel:
    return WizardModel.get(endpoint_id, wizard_uuid)


def get_wizard_count(endpoint_id: str, wizard_uuid: str) -> int:
    return WizardModel.count(endpoint_id, WizardModel.wizard_uuid == wizard_uuid)


def get_wizard_type(info: ResolveInfo, wizard: WizardModel) -> WizardType:
    try:
        elements = [
            _get_element(wizard.endpoint_id, element_uuid)
            for element_uuid in wizard.element_uuids
        ]
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    wizard = wizard.__dict__["attribute_values"]
    wizard["elements"] = elements
    wizard.pop("element_uuids")
    return WizardType(**Utility.json_normalize(wizard))


def resolve_wizard(info: ResolveInfo, **kwargs: Dict[str, Any]) -> WizardType:
    count = get_wizard_count(info.context["endpoint_id"], kwargs["wizard_uuid"])
    if count == 0:
        return None

    return get_wizard_type(
        info, get_wizard(info.context["endpoint_id"], kwargs["wizard_uuid"])
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["endpoint_id", "wizard_uuid"],
    list_type_class=WizardListType,
    type_funct=get_wizard_type,
)
def resolve_wizard_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    endpoint_id = info.context["endpoint_id"]
    wizard_type = kwargs.get("wizard_type")
    wizard_title = kwargs.get("wizard_title")

    args = []
    inquiry_funct = WizardModel.scan
    count_funct = WizardModel.count
    if endpoint_id:
        args = [endpoint_id, None]
        inquiry_funct = WizardModel.query

    the_filters = None
    if wizard_type:
        the_filters &= WizardModel.wizard_type == wizard_type
    if wizard_title:
        the_filters &= WizardModel.wizard_title == wizard_title
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@purge_cache()
@insert_update_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "wizard_uuid",
    },
    model_funct=get_wizard,
    count_funct=get_wizard_count,
    type_funct=get_wizard_type,
)
def insert_update_wizard(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:

    endpoint_id = kwargs.get("endpoint_id")
    wizard_uuid = kwargs.get("wizard_uuid")

    if kwargs.get("entity") is None:
        cols = {
            "wizard_title": kwargs["wizard_title"],
            "wizard_description": kwargs.get("wizard_description"),
            "wizard_type": kwargs["wizard_type"],
            "form_schema": kwargs.get("form_schema"),
            "priority": kwargs.get("priority", 0),
            "element_uuids": kwargs.get("element_uuids", []),
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        WizardModel(
            endpoint_id,
            wizard_uuid,
            **cols,
        ).save()
        return

    wizard = kwargs.get("entity")
    actions = [
        WizardModel.updated_by.set(kwargs["updated_by"]),
        WizardModel.updated_at.set(pendulum.now("UTC")),
    ]

    field_map = {
        "wizard_title": WizardModel.wizard_title,
        "wizard_description": WizardModel.wizard_description,
        "wizard_type": WizardModel.wizard_type,
        "form_schema": WizardModel.form_schema,
        "priority": WizardModel.priority,
        "element_uuids": WizardModel.element_uuids,
    }

    for key, field in field_map.items():
        if key in kwargs:
            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    wizard.update(actions=actions)

    return


@purge_cache()
@delete_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "wizard_uuid",
    },
    model_funct=get_wizard,
)
def delete_wizard(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:

    kwargs["entity"].delete()
    return True
