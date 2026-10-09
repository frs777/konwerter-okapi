"""Execution adapter for the native DOCX reader/writer pair."""
from __future__ import annotations

from pathlib import Path

from .reader import DocxReader
from .writer import DocxWriter


class DocxFilter:
    """Expose the DOCX reader/writer pair through the common filter boundary."""

    name = "docx"
    version = "1.0"
    mime_types = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    extensions = (".docx",)
    features = ("text", "zip_package")
    framework_contract = "net.sf.okapi.common.filters.IFilter"

    def __init__(self) -> None:
        self.reader = DocxReader()
        self.writer = DocxWriter()

    def read(self, source: str | Path):
        return self.reader.read(source)

    def write(self, events, target: str | Path):
        return self.writer.write(events, target=target)
