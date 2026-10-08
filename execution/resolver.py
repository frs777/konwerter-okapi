"""Resolve an input document to a filter descriptor."""
from __future__ import annotations

from pathlib import Path

from .registry import FilterDescriptor, FilterRegistry


class FilterResolver:
    def __init__(self, registry: FilterRegistry) -> None:
        self.registry = registry

    def resolve(self, source_path: Path) -> FilterDescriptor:
        extension = source_path.suffix.lower()
        candidates = self.registry.find_by_extension(extension)
        if not candidates:
            raise ValueError(f"unsupported document extension: {extension or '<none>'}")
        return candidates[0]
