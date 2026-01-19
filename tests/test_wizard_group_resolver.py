#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Unit tests for WizardGroupType.resolve_wizards function.

This test suite validates the Promise handling and error handling
in the resolve_wizards resolver function.
"""

from __future__ import print_function

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestResolveWizardsSelfParameter(unittest.TestCase):
    """Test that the resolver correctly receives self parameter."""

    def test_resolver_has_self_parameter(self):
        """Verify the resolver method has self as first parameter."""
        from ai_agent_core_engine.types.wizard_group import WizardGroupType
        import inspect
        sig = inspect.signature(WizardGroupType.resolve_wizards)
        params = list(sig.parameters.keys())

        self.assertIn("self", params, "Resolver must have 'self' parameter")
        self.assertEqual(params[0], "self", "'self' must be first parameter")


class TestResolveWizardsEmbeddedData(unittest.TestCase):
    """Test Case 1: Wizards already embedded in parent."""

    def test_returns_embedded_wizards(self):
        """Verify embedded wizards are returned correctly."""
        from ai_agent_core_engine.types.wizard_group import WizardGroupType
        from ai_agent_core_engine.utils.normalization import normalize_to_json

        parent = MagicMock()
        parent.wizards = [{"wizard_uuid": "w1", "name": "Wizard 1"}]
        parent.wizard_group_uuid = "test-group"

        info = MagicMock()

        result = WizardGroupType.resolve_wizards(None, parent, info)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["wizard_uuid"], "w1")


class TestResolveWizardsDataLoader(unittest.TestCase):
    """Test Case 2: Loading wizards via DataLoader."""

    def test_returns_promise_for_async_loading(self):
        """Verify resolver returns Promise for async loading."""
        from ai_agent_core_engine.types.wizard_group import WizardGroupType
        from promise import Promise

        parent = MagicMock()
        parent.wizards = None
        parent.wizard_uuids = ["w1"]
        parent.partition_key = "pk-123"
        parent.wizard_group_uuid = "test-group"

        info = MagicMock()
        info.context = {}

        mock_loader = MagicMock()
        mock_loader.wizard_loader.load.return_value = Promise.resolve(
            {"wizard_uuid": "w1", "name": "Wizard 1"}
        )

        with patch('ai_agent_core_engine.types.wizard_group.get_loaders') as mock_get_loaders:
            mock_get_loaders.return_value = mock_loader

            result = WizardGroupType.resolve_wizards(None, parent, info)

            self.assertIsInstance(result, Promise)

    def test_promise_resolves_to_normalized_data(self):
        """Verify Promise resolves to normalized wizard data."""
        from ai_agent_core_engine.types.wizard_group import WizardGroupType
        from promise import Promise

        parent = MagicMock()
        parent.wizards = None
        parent.wizard_uuids = ["w1", "w2"]
        parent.partition_key = "pk-123"
        parent.wizard_group_uuid = "test-group"

        info = MagicMock()
        info.context = {}

        def load_side_effect(key):
            return Promise.resolve(
                {"wizard_uuid": key[1], "name": f"Wizard {key[1]}"}
            )

        mock_loader = MagicMock()
        mock_loader.wizard_loader.load.side_effect = load_side_effect

        with patch('ai_agent_core_engine.types.wizard_group.get_loaders') as mock_get_loaders:
            mock_get_loaders.return_value = mock_loader

            result = WizardGroupType.resolve_wizards(None, parent, info)

            wizards = result.get()

            self.assertIsInstance(wizards, list)
            self.assertEqual(len(wizards), 2)
            self.assertEqual(wizards[0]["wizard_uuid"], "w1")
            self.assertEqual(wizards[1]["wizard_uuid"], "w2")

    def test_none_values_are_filtered(self):
        """Verify None values from DataLoader are filtered out."""
        from ai_agent_core_engine.types.wizard_group import WizardGroupType
        from promise import Promise

        parent = MagicMock()
        parent.wizards = None
        parent.wizard_uuids = ["w1", "w2", "w3"]
        parent.partition_key = "pk-123"
        parent.wizard_group_uuid = "test-group"

        info = MagicMock()
        info.context = {}

        def load_side_effect(key):
            if key[1] == "w2":
                return Promise.resolve(None)
            return Promise.resolve({"wizard_uuid": key[1]})

        mock_loader = MagicMock()
        mock_loader.wizard_loader.load.side_effect = load_side_effect

        with patch('ai_agent_core_engine.types.wizard_group.get_loaders') as mock_get_loaders:
            mock_get_loaders.return_value = mock_loader

            result = WizardGroupType.resolve_wizards(None, parent, info)

            wizards = result.get()

            self.assertEqual(len(wizards), 2)
            self.assertTrue(all("wizard_uuid" in w for w in wizards))


class TestResolveWizardsErrorHandling(unittest.TestCase):
    """Test error handling in resolve_wizards."""

    def test_catch_handles_rejected_promise(self):
        """Verify .catch() handles Promise rejection gracefully."""
        from ai_agent_core_engine.types.wizard_group import WizardGroupType
        from promise import Promise

        parent = MagicMock()
        parent.wizards = None
        parent.wizard_uuids = ["w1"]
        parent.partition_key = "pk-123"
        parent.wizard_group_uuid = "test-group"

        info = MagicMock()
        info.context = {}

        mock_loader = MagicMock()
        mock_loader.wizard_loader.load.return_value = Promise.reject(
            ValueError("Database connection failed")
        )

        with patch('ai_agent_core_engine.types.wizard_group.get_loaders') as mock_get_loaders:
            mock_get_loaders.return_value = mock_loader

            result = WizardGroupType.resolve_wizards(None, parent, info)

            wizards = result.get()

            self.assertIsInstance(wizards, list)
            self.assertEqual(wizards, [])

    def test_try_catch_handles_exceptions(self):
        """Verify try-catch handles exceptions during DataLoader loading."""
        from ai_agent_core_engine.types.wizard_group import WizardGroupType

        parent = MagicMock()
        parent.wizards = None
        parent.wizard_uuids = ["w1"]
        parent.partition_key = "pk-123"
        parent.wizard_group_uuid = "test-group"

        info = MagicMock()

        with patch('ai_agent_core_engine.types.wizard_group.get_loaders') as mock_get_loaders:
            mock_get_loaders.side_effect = ImportError("Module not found")

            result = WizardGroupType.resolve_wizards(None, parent, info)

            self.assertEqual(result, [])

    def test_missing_partition_key_returns_empty(self):
        """Verify missing partition_key returns empty list."""
        from ai_agent_core_engine.types.wizard_group import WizardGroupType

        parent = MagicMock()
        parent.wizards = None
        parent.wizard_uuids = ["w1"]
        parent.partition_key = None
        parent.wizard_group_uuid = "test-group"

        info = MagicMock()

        with patch('ai_agent_core_engine.types.wizard_group.get_loaders'):
            result = WizardGroupType.resolve_wizards(None, parent, info)

            self.assertEqual(result, [])

    def test_empty_wizard_uuids_returns_empty(self):
        """Verify empty wizard_uuids returns empty list."""
        from ai_agent_core_engine.types.wizard_group import WizardGroupType

        parent = MagicMock()
        parent.wizards = None
        parent.wizard_uuids = []
        parent.wizard_group_uuid = "test-group"

        info = MagicMock()

        result = WizardGroupType.resolve_wizards(None, parent, info)

        self.assertEqual(result, [])


class TestResolveWizardsTypeAnnotations(unittest.TestCase):
    """Test type annotations in resolve_wizards."""

    def test_return_type_annotation_present(self):
        """Verify return type annotation is set."""
        from ai_agent_core_engine.types.wizard_group import WizardGroupType
        import inspect
        sig = inspect.signature(WizardGroupType.resolve_wizards)
        return_annotation = sig.return_annotation

        self.assertIn("Promise", str(return_annotation))


class TestResolveWizardsLogging(unittest.TestCase):
    """Test logging in resolve_wizards."""

    def test_logger_is_configured(self):
        """Verify logger is configured at module level."""
        from ai_agent_core_engine import types_wizard_group as wg_module
        self.assertIsNotNone(wg_module.logger)


if __name__ == "__main__":
    unittest.main()
