from __future__ import annotations

from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

from core.document.model import Markup, TextFragment, TextUnit
from core.events.model import Event, EventType, StartDocument

NS = "{urn:oasis:names:tc:xliff:document:2.0}"


class XLIFF2Filter:
    """Small native XLIFF 2.x filter preserving segment inline markup."""

    name = "xliff2"
    version = "1.0"
    mime_types = ("application/xliff+xml", "application/xml")
    extensions = (".xlf", ".xliff")
    features = ("text",)
    framework_contract = "net.sf.okapi.common.filters.IFilter"

    def __init__(self) -> None:
        self._source: str | None = None

    def read(self, source: str | Path):
        if isinstance(source, Path) or (isinstance(source, str) and "<" not in source[:100]):
            path = Path(source)
            self._source = path.read_text(encoding="utf-8")
            document_name = path.name
        else:
            self._source = str(source)
            document_name = "memory.xlf"
        root = ET.fromstring(self._source)
        yield Event(EventType.START_DOCUMENT, StartDocument(document_name, document_name))
        for unit in root.findall(f".//{NS}unit"):
            segment = unit.find(f"{NS}segment")
            source_element = segment.find(f"{NS}source") if segment is not None else None
            if source_element is None:
                continue
            parts = tuple(self._element_parts(source_element))
            unit_id = unit.get("id", "")
            yield Event(EventType.TEXT_UNIT, TextUnit(
                unit_id, (TextFragment(parts),),
                {"part": "xliff2", "unit_id": unit_id, "source_original": self._serialize_parts(parts)},
            ))
        yield Event(EventType.END_DOCUMENT, None)

    def write(self, events, target: str | Path | None = None) -> str:
        if self._source is None:
            raise RuntimeError("read() must be called before write()")
        output = self._source
        for event in events:
            if event.type is not EventType.TEXT_UNIT:
                continue
            unit = event.resource
            unit_id = (unit.metadata or {}).get("unit_id", unit.id)
            replacement = self._serialize_parts(tuple(part for fragment in unit.fragments for part in fragment.parts))
            start = output.find("<unit", 0)
            while start >= 0:
                end = output.find(">", start)
                close = output.find("</unit>", end)
                if end < 0 or close < 0:
                    break
                header = output[start:end]
                if f'id="{escape(unit_id, quote=True)}"' in header or f"id='{escape(unit_id, quote=True)}'" in header:
                    source_start = output.find("<source", end, close)
                    source_end = output.find(">", source_start, close)
                    source_close = output.find("</source>", source_end, close)
                    if source_start >= 0 and source_end >= 0 and source_close >= 0:
                        output = output[:source_end + 1] + replacement + output[source_close:]
                    break
                start = output.find("<unit", close + 1)
        if target is not None:
            Path(target).write_text(output, encoding="utf-8")
        return output

    def round_trip(self, source: str | Path) -> str:
        return self.write(tuple(self.read(source)))

    def _element_parts(self, element: ET.Element):
        if element.text:
            yield element.text
        for child in element:
            attrs = tuple((key.split("}")[-1], value) for key, value in child.attrib.items())
            yield Markup.empty(child.tag.split("}")[-1], attrs)
            if child.tail:
                yield child.tail

    @staticmethod
    def _serialize_parts(parts) -> str:
        output = []
        for part in parts:
            if isinstance(part, str):
                output.append(escape(part))
            elif isinstance(part, Markup):
                attrs = "".join(f' {escape(k, quote=True)}="{escape(v, quote=True)}"' for k, v in part.attributes)
                if part.kind == "empty":
                    output.append(f"<{part.name}{attrs}/>")
                elif part.kind == "start":
                    output.append(f"<{part.name}{attrs}>")
                else:
                    output.append(f"</{part.name}>")
            else:
                output.append(getattr(part, "data", ""))
        return "".join(output)
