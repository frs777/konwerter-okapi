from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DependencyReport:
    declared: tuple[str, ...]
    jar_files: tuple[Path, ...]


class DependencyAnalyzer:
    """Zestawia zależności deklarowane z faktycznie dostarczonymi JAR-ami."""

    def analyze(self, metadata_path: str | Path, jar_files: list[str | Path] | tuple[str | Path, ...]) -> DependencyReport:
        path = Path(metadata_path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Nie można odczytać metadanych zależności: {path}") from exc
        declared = tuple(
            str(item["artifact"]).strip()
            for item in data.get("dependencies", [])
            if isinstance(item, dict) and item.get("artifact")
        )
        files = tuple(Path(item) for item in jar_files)
        return DependencyReport(declared, files)
