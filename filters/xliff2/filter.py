from __future__ import annotations

from html import escape
from pathlib import Path
import re
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
            segments = unit.findall(f"{NS}segment")
            unit_id = unit.get("id", "")
            for segment_index, segment in enumerate(segments):
                source_element = segment.find(f"{NS}source")
                if source_element is None:
                    continue
                parts = tuple(self._element_parts(source_element))
                target_element = segment.find(f"{NS}target")
                target_parts = tuple(self._element_parts(target_element)) if target_element is not None else None
                segment_id = segment.get("id", "")
                unique_id = unit_id if len(segments) == 1 else f"{unit_id}:{segment_id or segment_index}"
                yield Event(EventType.TEXT_UNIT, TextUnit(
                    unique_id, (TextFragment(parts),),
                    {
                        "part": "xliff2", "unit_id": unit_id, "segment_id": segment_id,
                        "segment_index": str(segment_index), "source_original": self._serialize_parts(parts),
                    },
                    target_fragments=(TextFragment(target_parts),) if target_parts is not None else None,
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
            metadata = unit.metadata or {}
            unit_id = metadata.get("unit_id", unit.id)
            segment_id = metadata.get("segment_id", "")
            segment_index = int(metadata.get("segment_index", "0"))
            source_replacement = self._serialize_parts(
                tuple(part for fragment in unit.fragments for part in fragment.parts)
            )
            target_fragments = unit.target_fragments
            target_replacement = (
                self._serialize_parts(tuple(part for fragment in target_fragments for part in fragment.parts))
                if target_fragments is not None else None
            )
            start = self._find_open_tag(output, "unit")
            while start >= 0:
                end = output.find(">", start)
                close = self._find_close_tag(output, "unit", end)
                if end < 0 or close < 0:
                    break
                header = output[start:end]
                if f'id="{escape(unit_id, quote=True)}"' in header or f"id='{escape(unit_id, quote=True)}'" in header:
                    segment_start = self._find_open_tag(output, "segment", end, close)
                    for _ in range(segment_index):
                        if segment_start < 0:
                            break
                        segment_start = self._find_open_tag(output, "segment", segment_start + 1, close)
                    if segment_id and segment_start >= 0:
                        while segment_start >= 0:
                            segment_end = output.find(">", segment_start, close)
                            if segment_end < 0:
                                segment_start = -1
                                break
                            segment_header = output[segment_start:segment_end]
                            if f'id="{escape(segment_id, quote=True)}"' in segment_header or f"id='{escape(segment_id, quote=True)}'" in segment_header:
                                break
                            segment_start = self._find_open_tag(output, "segment", segment_end + 1, close)
                    if segment_start < 0:
                        break
                    segment_end = output.find(">", segment_start, close)
                    segment_close = self._find_close_tag(output, "segment", segment_end, close)
                    source_start = self._find_open_tag(output, "source", segment_end, segment_close)
                    source_end = output.find(">", source_start, segment_close)
                    source_close = self._find_close_tag(output, "source", source_end, segment_close)
                    if (
                        source_start >= 0 and source_end >= 0 and source_close >= 0
                        and source_replacement != metadata.get("source_original", source_replacement)
                    ):
                        output = output[:source_end + 1] + source_replacement + output[source_close:]
                        end = output.find(">", start)
                        close = self._find_close_tag(output, "unit", end)
                        segment_start = self._find_open_tag(output, "segment", end, close)
                        for _ in range(segment_index):
                            if segment_start < 0:
                                break
                            segment_start = self._find_open_tag(output, "segment", segment_start + 1, close)
                        if segment_id and segment_start >= 0:
                            while segment_start >= 0:
                                segment_end = output.find(">", segment_start, close)
                                if segment_end < 0:
                                    segment_start = -1
                                    break
                                segment_header = output[segment_start:segment_end]
                                if f'id="{escape(segment_id, quote=True)}"' in segment_header or f"id='{escape(segment_id, quote=True)}'" in segment_header:
                                    break
                                segment_start = self._find_open_tag(output, "segment", segment_end + 1, close)
                        segment_end = output.find(">", segment_start, close)
                        segment_close = self._find_close_tag(output, "segment", segment_end, close)
                    if target_replacement is not None and segment_start >= 0 and segment_end >= 0 and segment_close >= 0:
                        target_start = self._find_open_tag(output, "target", segment_end, segment_close)
                        target_end = output.find(">", target_start, segment_close)
                        target_close = self._find_close_tag(output, "target", target_end, segment_close)
                        if target_start >= 0 and target_end >= 0 and target_close >= 0:
                            output = output[:target_end + 1] + target_replacement + output[target_close:]
                        else:
                            prefix = self._tag_prefix(output, segment_start)
                            output = output[:segment_close] + f"<{prefix}target>{target_replacement}</{prefix}target>" + output[segment_close:]
                    break
                start = self._find_open_tag(output, "unit", close + 1)
        if target is not None:
            Path(target).write_text(output, encoding="utf-8")
        return output

    def round_trip(self, source: str | Path) -> str:
        return self.write(tuple(self.read(source)))

    @staticmethod
    def _find_open_tag(source: str, local_name: str, start: int = 0, end: int | None = None) -> int:
        limit = len(source) if end is None else end
        match = re.search(rf"<(?:[A-Za-z_][\w.-]*:)?{re.escape(local_name)}(?=[\s>/])", source[start:limit])
        return start + match.start() if match else -1

    @staticmethod
    def _find_close_tag(source: str, local_name: str, start: int = 0, end: int | None = None) -> int:
        limit = len(source) if end is None else end
        match = re.search(rf"</(?:[A-Za-z_][\w.-]*:)?{re.escape(local_name)}\s*>", source[start:limit])
        return start + match.start() if match else -1

    @staticmethod
    def _tag_prefix(source: str, start: int) -> str:
        match = re.match(r"<[A-Za-z_][\w.-]*:", source[start:])
        return match.group(0)[1:] if match else ""

    def _element_parts(self, element: ET.Element):
        if element.text:
            yield element.text
        for child in element:
            attrs = tuple((key.split("}")[-1], value) for key, value in child.attrib.items())
            name = child.tag.split("}")[-1]
            if len(child) == 0 and not child.text:
                yield Markup.empty(name, attrs)
            else:
                yield Markup.start(name, attrs)
                yield from self._element_parts(child)
                yield Markup.end(name)
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
