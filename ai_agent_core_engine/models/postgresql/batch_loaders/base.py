# -*- coding: utf-8 -*-
"""SafeDataLoader for PostgreSQL — batch loading with error isolation.

Copies the contract from models/dynamodb/batch_loaders/base.py:
- Subclasses implement _batch_load_fn(keys) -> Dict[key, normalized_dict]
- .load(key) returns a Promise that resolves to the normalized dict or None
- Errors for individual keys are isolated (one bad key doesn't break the batch)
- Results are cached per-loader-instance (request-scoped)
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional
from promise import Promise


class SafeDataLoader:
    """Base class for PostgreSQL DataLoaders with error isolation."""

    def __init__(self, context: Dict[str, Any], cache_enabled: bool = True) -> None:
        self._context = context
        self._cache_enabled = cache_enabled
        self._cache: Dict[str, Any] = {}
        self._batch: Dict[str, Any] = {}
        self._scheduled: bool = False

    def _batch_load_fn(self, keys: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """Override: given a list of keys, return a dict mapping key -> normalized row dict.

        Keys that are not found should map to None. This method is called
        once per batch tick with all queued keys.
        """
        raise NotImplementedError("Subclasses must implement _batch_load_fn")

    def load(self, key: str) -> Promise:
        """Queue a key for batch loading and return a Promise."""
        if key in self._cache and self._cache_enabled:
            return Promise.resolve(self._cache[key])

        # Create a Promise with an executor that captures resolve/reject
        # so _dispatch_batch can resolve it later.
        resolver_holder: Dict[str, Any] = {}

        def _executor(resolve, reject):
            resolver_holder["resolve"] = resolve
            resolver_holder["reject"] = reject

        promise = Promise(_executor)
        self._batch[key] = (promise, resolver_holder)

        if not self._scheduled:
            self._scheduled = True
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.call_soon(self._dispatch_batch)
                else:
                    # Loop exists but isn't running — dispatch synchronously
                    self._dispatch_batch()
            except RuntimeError:
                # No event loop — dispatch synchronously
                self._dispatch_batch()

        return promise

    def _dispatch_batch(self) -> None:
        """Execute the batch load for all queued keys."""
        self._scheduled = False
        keys = list(self._batch.keys())
        if not keys:
            return

        entries = {k: self._batch.pop(k) for k in keys}
        try:
            results = self._batch_load_fn(keys)
            for key in keys:
                val = results.get(key)
                if self._cache_enabled:
                    self._cache[key] = val
                entries[key][1]["resolve"](val)
        except Exception as exc:
            for key in keys:
                entries[key][1]["reject"](exc)

    def clear(self, key: str) -> None:
        """Clear a single key from the cache."""
        self._cache.pop(key, None)

    def clear_all(self) -> None:
        """Clear the entire cache."""
        self._cache.clear()


class Key:
    """Composite key helper for DataLoader keys."""

    def __init__(self, *parts: str) -> None:
        self._parts = parts
        self._key = "#".join(str(p) for p in parts)

    def __str__(self) -> str:
        return self._key

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Key):
            return self._key == other._key
        if isinstance(other, str):
            return self._key == other
        return False

    def __hash__(self) -> int:
        return hash(self._key)


__all__ = ["SafeDataLoader", "Key"]