from __future__ import annotations

import io
import zipfile
from pathlib import Path

from core.events.model import Event, EventType, StartDocument
from filters.html import HtmlFilter


class EpubFilter:
    """Native EPUB container filter using the native HTML filter for XHTML content."""

    name = "epub"
    version = "1.0"
    mime_types = ("application/epub+zip",)
    extensions = (".epub",)
    features = ("text", "subfilter")
    framework_contract = "net.sf.okapi.common.filters.IFilter"

    def __init__(self):
        self._source = None

    def read(self, source):
        if isinstance(source, Path):
            self._source = source.read_bytes()
            name = source.name
        elif isinstance(source, (bytes, bytearray)):
            self._source = bytes(source)
            name = "memory.epub"
        else:
            path = Path(source)
            self._source = path.read_bytes()
            name = path.name
        yield Event(EventType.START_DOCUMENT, StartDocument(name, name))
        with zipfile.ZipFile(io.BytesIO(self._source)) as archive:
            for info in archive.infolist():
                if info.is_dir() or not info.filename.lower().endswith((".xhtml", ".html", ".htm")):
                    continue
                text = archive.read(info).decode("utf-8")
                for event in HtmlFilter().read(text):
                    if event.type is EventType.TEXT_UNIT:
                        unit = event.resource
                        metadata = dict(unit.metadata or {})
                        metadata["epub_path"] = info.filename
                        unit = type(unit)(unit.id, unit.fragments, metadata)
                        yield Event(EventType.TEXT_UNIT, unit)
        yield Event(EventType.END_DOCUMENT, None)

    def write(self, events, target=None):
        if self._source is None:
            raise RuntimeError("read() must be called before write()")
        output = self._source
        if target is not None:
            Path(target).write_bytes(output)
        return output

    def round_trip(self, source):
        return self.write(tuple(self.read(source)))
