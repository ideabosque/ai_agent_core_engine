# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict

import boto3

from ..models import utils


class Config:
    """
    Centralized Configuration Class
    Manages shared configuration variables across the application.
    """

    aws_lambda = None
    schemas = {}

    @classmethod
    def initialize(cls, logger: logging.Logger, **setting: Dict[str, Any]) -> None:
        """
        Initialize configuration setting.
        Args:
            logger (logging.Logger): Logger instance for logging.
            **setting (Dict[str, Any]): Configuration dictionary.
        """
        try:
            cls._set_parameters(setting)
            cls._initialize_aws_services(setting)
            if setting.get("test_mode") == "local_for_all":
                cls._initialize_tables(logger)
            logger.info("Configuration initialized successfully.")
        except Exception as e:
            logger.exception("Failed to initialize configuration.")
            raise e

    @classmethod
    def _set_parameters(cls, setting: Dict[str, Any]) -> None:
        """
        Set application-level parameters.
        Args:
            setting (Dict[str, Any]): Configuration dictionary.
        """
        pass

    @classmethod
    def _initialize_aws_services(cls, setting: Dict[str, Any]) -> None:
        """
        Initialize AWS services, such as the S3 client.
        Args:
            setting (Dict[str, Any]): Configuration dictionary.
        """
        if all(
            setting.get(k)
            for k in ["region_name", "aws_access_key_id", "aws_secret_access_key"]
        ):
            aws_credentials = {
                "region_name": setting["region_name"],
                "aws_access_key_id": setting["aws_access_key_id"],
                "aws_secret_access_key": setting["aws_secret_access_key"],
            }
        else:
            aws_credentials = {}

        cls.aws_lambda = boto3.client("lambda", **aws_credentials)

    @classmethod
    def _initialize_tables(cls, logger: logging.Logger) -> None:
        """
        Initialize database tables by calling the utils._initialize_tables() method.
        This is an internal method used during configuration setup.
        """
        utils._initialize_tables(logger)
