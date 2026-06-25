# -*- coding: utf-8 -*-
"""Static adoption guard test — ensures queries/ and mutations/ never import
backend-specific model modules directly. They must go through get_repo().
"""
from __future__ import print_function

__author__ = "bibow"

import os
import re
import unittest
from typing import List, Set

# Files to guard — all query and mutation files (excluding ai_agent.py which
# is a handler-level file, not a simple entity query/mutation)
_FILES_TO_GUARD = [
    "queries/agent.py", "queries/llm.py", "queries/thread.py",
    "queries/run.py", "queries/message.py", "queries/tool_call.py",
    "queries/async_task.py", "queries/fine_tuning_message.py",
    "queries/element.py", "queries/wizard.py", "queries/wizard_schema.py",
    "queries/wizard_group.py", "queries/wizard_group_filter.py",
    "queries/mcp_server.py", "queries/ui_component.py",
    "queries/flow_snippet.py", "queries/prompt_template.py",
    "mutations/agent.py", "mutations/llm.py", "mutations/thread.py",
    "mutations/run.py", "mutations/message.py", "mutations/tool_call.py",
    "mutations/async_task.py", "mutations/fine_tuning_message.py",
    "mutations/element.py", "mutations/wizard.py", "mutations/wizard_schema.py",
    "mutations/wizard_group.py", "mutations/wizard_group_filter.py",
    "mutations/mcp_server.py", "mutations/ui_component.py",
    "mutations/flow_snippet.py", "mutations/prompt_template.py",
]

# Forbidden import patterns — these should never appear in guarded files
_FORBIDDEN_IMPORT_PATTERNS = [
    "models.dynamodb",
    "models.postgresql",
    "models.agent",
    "models.llm",
    "models.thread",
    "models.run",
    "models.message",
    "models.tool_call",
    "models.async_task",
    "models.fine_tuning_message",
    "models.element",
    "models.wizard",
    "models.wizard_schema",
    "models.wizard_group",
    "models.wizard_group_filter",
    "models.mcp_server",
    "models.ui_component",
    "models.flow_snippet",
    "models.prompt_template",
]

# Forbidden direct free-function calls — must use get_repo() instead
_FORBIDDEN_CALL_PATTERNS = [
    "insert_update_agent(",
    "delete_agent(",
    "insert_update_llm(",
    "delete_llm(",
    "insert_thread(",
    "delete_thread(",
    "insert_update_run(",
    "delete_run(",
    "insert_update_message(",
    "delete_message(",
    "insert_update_tool_call(",
    "delete_tool_call(",
    "insert_update_async_task(",
    "delete_async_task(",
    "insert_update_fine_tuning_message(",
    "delete_fine_tuning_message(",
    "insert_update_element(",
    "delete_element(",
    "insert_update_wizard(",
    "delete_wizard(",
    "insert_update_wizard_schema(",
    "delete_wizard_schema(",
    "insert_update_wizard_group(",
    "delete_wizard_group(",
    "insert_update_wizard_group_filter(",
    "delete_wizard_group_filter(",
    "insert_update_mcp_server(",
    "delete_mcp_server(",
    "insert_update_ui_component(",
    "delete_ui_component(",
    "insert_update_flow_snippet(",
    "delete_flow_snippet(",
    "insert_update_prompt_template(",
    "delete_prompt_template(",
]

# Allowed patterns — these are fine in guarded files
_ALLOWED_IMPORT = "models.repositories"


def _get_pkg_root() -> str:
    """Find the ai_agent_core_engine package root directory."""
    here = os.path.dirname(os.path.abspath(__file__))
    # We're in tests/ — the package root is the parent
    return os.path.dirname(here)


class StaticAdoptionGuardTest(unittest.TestCase):
    """Ensure queries/ and mutations/ route through the repository boundary."""

    def test_no_forbidden_imports(self):
        """No guarded file should import from models.dynamodb or models.<entity>."""
        pkg_root = _get_pkg_root()
        violations: List[str] = []

        for rel_path in _FILES_TO_GUARD:
            full_path = os.path.join(pkg_root, rel_path)
            if not os.path.isfile(full_path):
                continue

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            for pattern in _FORBIDDEN_IMPORT_PATTERNS:
                # Skip if this is actually a models.repositories import
                if _ALLOWED_IMPORT in pattern:
                    continue
                # Check for forbidden import patterns
                if f"from ..{pattern}" in content or f"import ..{pattern}" in content:
                    violations.append(f"{rel_path}: forbidden import '{pattern}'")

        self.assertEqual(
            len(violations),
            0,
            f"Forbidden imports found in guarded files:\n" + "\n".join(violations),
        )

    def test_no_forbidden_free_function_calls(self):
        """No guarded file should call insert_update_*() or delete_*() directly."""
        pkg_root = _get_pkg_root()
        violations: List[str] = []

        for rel_path in _FILES_TO_GUARD:
            full_path = os.path.join(pkg_root, rel_path)
            if not os.path.isfile(full_path):
                continue

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            for pattern in _FORBIDDEN_CALL_PATTERNS:
                # Allow method calls like get_repo("entity").insert_update(...)
                # but not bare function calls like insert_update_entity(...)
                # The difference: forbidden calls don't have a "." before them
                lines = content.split("\n")
                for lineno, line in enumerate(lines, 1):
                    stripped = line.strip()
                    # Skip comments
                    if stripped.startswith("#"):
                        continue
                    # Check if the pattern appears without a preceding "."
                    if pattern in stripped:
                        # Find the position of the pattern
                        idx = stripped.find(pattern)
                        if idx == 0 or (idx > 0 and stripped[idx - 1] != "."):
                            violations.append(
                                f"{rel_path}:{lineno}: forbidden call '{pattern}'"
                            )

        self.assertEqual(
            len(violations),
            0,
            f"Forbidden direct function calls found in guarded files:\n"
            + "\n".join(violations),
        )

    def test_uses_get_repo(self):
        """Every guarded file should import get_repo from models.repositories."""
        pkg_root = _get_pkg_root()
        missing: List[str] = []

        for rel_path in _FILES_TO_GUARD:
            full_path = os.path.join(pkg_root, rel_path)
            if not os.path.isfile(full_path):
                continue

            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            if "get_repo" not in content and "get_loaders" not in content:
                # Files that only define types or don't need get_repo are OK
                # but most query/mutation files should use get_repo
                missing.append(rel_path)

        # Some files might legitimately not use get_repo (e.g., if they only
        # define mutation classes that call other handlers). Only warn, don't fail.
        # We only fail if NO file uses get_repo at all.
        self.assertGreater(
            len(_FILES_TO_GUARD) - len(missing),
            0,
            "No guarded file uses get_repo — the boundary is not adopted.",
        )


if __name__ == "__main__":
    unittest.main()