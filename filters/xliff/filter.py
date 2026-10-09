from __future__ import annotations

from html import escape
from pathlib import Path
import re
from xml.etree import ElementTree as ET

from core.document.model import Markup, TextFragment, TextUnit
from core.events.model import Event, EventType, StartDocument

NS = "{urn:oasis:names:tc:xliff:document:1.2}"


class XLIFFFilter:
    """Small native XLIFF 1.2 filter preserving source inline markup."""

    name = "xliff"
    version = "1.0"
    mime_types = ("application/xliff+xml", "application/xml")
    extensions = (".xlf", ".xliff")
    features = ("text", "xml_stream")
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
        for trans_unit in root.findall(f".//{NS}trans-unit"):
            source_element = trans_unit.find(f"{NS}source")
            if source_element is None:
                continue
            parts = tuple(self._element_parts(source_element))
            target_element = trans_unit.find(f"{NS}target")
            target_parts = tuple(self._element_parts(target_element)) if target_element is not None else None
            metadata = {
                "part": "xliff",
                "trans_unit_id": trans_unit.get("id", ""),
                "source_language": self._ancestor_attr(trans_unit, "source-language"),
                "target_language": self._ancestor_attr(trans_unit, "target-language"),
                "source_original": self._serialize_parts(parts),
            }
            yield Event(
                EventType.TEXT_UNIT,
                TextUnit(
                    trans_unit.get("id", ""),
                    (TextFragment(parts),),
                    metadata,
                    target_fragments=(TextFragment(target_parts),) if target_parts is not None else None,
                ),
            )
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
            unit_id = metadata.get("trans_unit_id", unit.id)
            source_replacement = self._serialize_parts(
                tuple(part for fragment in unit.fragments for part in fragment.parts)
            )
            target_fragments = unit.target_fragments
            target_replacement = (
                self._serialize_parts(tuple(part for fragment in target_fragments for part in fragment.parts))
                if target_fragments is not None else None
            )
            start = self._find_open_tag(output, "trans-unit")
            while start >= 0:
                end = output.find(">", start)
                close = self._find_close_tag(output, "trans-unit", end)
                if end < 0 or close < 0:
                    break
                header = output[start:end]
                if f'id="{escape(unit_id, quote=True)}"' in header or f"id='{escape(unit_id, quote=True)}'" in header:
                    source_start = self._find_open_tag(output, "source", end, close)
                    source_end = output.find(">", source_start, close)
                    source_close = self._find_close_tag(output, "source", source_end, close)
                    if (
                        source_start >= 0 and source_end >= 0 and source_close >= 0
                        and source_replacement != metadata.get("source_original", source_replacement)
                    ):
                        output = output[:source_end + 1] + source_replacement + output[source_close:]
                        end = output.find(">", start)
                        close = self._find_close_tag(output, "trans-unit", end)
                    if target_replacement is not None:
                        target_start = self._find_open_tag(output, "target", end, close)
                        target_end = output.find(">", target_start, close)
                        target_close = self._find_close_tag(output, "target", target_end, close)
                        if target_start >= 0 and target_end >= 0 and target_close >= 0:
                            output = output[:target_end + 1] + target_replacement + output[target_close:]
                        else:
                            close = self._find_close_tag(output, "trans-unit", end)
                            if close >= 0:
                                prefix = self._tag_prefix(output, start)
                                output = output[:close] + f"<{prefix}target>{target_replacement}</{prefix}target>" + output[close:]
                    break
                start = self._find_open_tag(output, "trans-unit", close + 1)
        if target is not None:
            Path(target).write_text(output, encoding="utf-8")
        return output

    def round_trip(self, source: str | Path) -> str:
        events = tuple(self.read(source))
        return self.write(events)

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
        output: list[str] = []
        for part in parts:
            if isinstance(part, str):
                output.append(escape(part))
            elif isinstance(part, Markup):
                if part.kind == "start":
                    attrs = "".join(f' {escape(k, quote=True)}="{escape(v, quote=True)}"' for k, v in part.attributes)
                    output.append(f"<{part.name}{attrs}>")
                elif part.kind == "end":
                    output.append(f"</{part.name}>")
                else:
                    attrs = "".join(f' {escape(k, quote=True)}="{escape(v, quote=True)}"' for k, v in part.attributes)
                    output.append(f"<{part.name}{attrs}/>")
            else:
                output.append(getattr(part, "data", ""))
        return "".join(output)

    @staticmethod
    def _ancestor_attr(element: ET.Element, name: str) -> str:
        parent = element
        # ET does not expose parents; XLIFF file attrs are optional metadata.
        return ""
