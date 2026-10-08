from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FilterMetadata:
    name: str
    entry_class: str
    dependencies: tuple[str, ...]


class FilterMetadataExtractor:
    """Odczytuje deklaratywne metadane filtra bez wykonywania Javy."""

    def extract(self, path: str | Path) -> FilterMetadata:
        source = Path(path)
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Nie można odczytać metadanych filtra: {source}") from exc
        name = str(data.get("name", "")).strip()
        entry_class = str(data.get("entry_class", "")).strip()
        if not name or not entry_class:
            raise ValueError("filter.json musi zawierać name i entry_class")
        dependencies = tuple(
            str(item.get("artifact", "")).strip()
            for item in data.get("dependencies", [])
            if isinstance(item, dict) and item.get("artifact")
        )
        return FilterMetadata(name, entry_class, dependencies)
