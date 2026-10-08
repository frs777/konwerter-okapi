from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile


@dataclass(frozen=True, slots=True)
class JarInspection:
    path: Path
    manifest: dict[str, str]
    classes: tuple[str, ...]


class JarInspector:
    """Read-only inspector JAR; nie uruchamia kodu Java."""

    def inspect(self, path: str | Path) -> JarInspection:
        jar_path = Path(path)
        try:
            with ZipFile(jar_path) as archive:
                names = archive.namelist()
                manifest = self._manifest(archive.read("META-INF/MANIFEST.MF")) if "META-INF/MANIFEST.MF" in names else {}
                classes = tuple(sorted(name[:-6].replace("/", ".") for name in names if name.endswith(".class") and not name.endswith("module-info.class")))
        except (BadZipFile, FileNotFoundError, OSError) as exc:
            raise ValueError(f"Niepoprawny JAR: {jar_path}") from exc
        return JarInspection(jar_path, manifest, classes)

    def _manifest(self, raw: bytes) -> dict[str, str]:
        result: dict[str, str] = {}
        current = None
        for line in raw.decode("utf-8", errors="replace").splitlines():
            if line.startswith(" ") and current is not None:
                result[current] += line[1:]
                continue
            if ": " in line:
                key, value = line.split(": ", 1)
                result[key] = value
                current = key
        return result
