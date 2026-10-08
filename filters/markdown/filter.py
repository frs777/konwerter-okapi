from __future__ import annotations

import re

from core.document.model import Code, TextFragment, TextUnit
from core.events.model import DocumentPart, Event, EventType


class MarkdownFilter:
    _FENCE = re.compile(r"^(\s*" + chr(96)*3 + r"[^\n]*\n)(.*?)(^\s*" + chr(96)*3 + r"[ \t]*(?:\n|$))", re.MULTILINE | re.DOTALL)
    _INLINE = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|" + chr(96) + r"[^" + chr(96) + r"]+" + chr(96) + r"|!\[[^\]]+\]\([^)]*\)|\[[^\]]+\]\([^)]*\))")

    def read(self, source: str):
        events = [Event(EventType.START_DOCUMENT, source)]
        position = 0
        unit_index = 0
        for match in self._FENCE.finditer(source):
            block = source[position:match.start()]
            block_events = self._read_blocks(block, unit_index)
            events.extend(block_events)
            unit_index += sum(e.type is EventType.TEXT_UNIT for e in block_events)
            events.append(Event(EventType.DOCUMENT_PART, DocumentPart(match.group(1))))
            events.append(Event(EventType.TEXT_UNIT, TextUnit(f"markdown-{unit_index + 1}", (TextFragment((Code(match.group(2), "protected"),)),))))
            unit_index += 1
            events.append(Event(EventType.DOCUMENT_PART, DocumentPart(match.group(3))))
            position = match.end()
        block_events = self._read_blocks(source[position:], unit_index)
        events.extend(block_events)
        events.append(Event(EventType.END_DOCUMENT, None))
        return tuple(events)

    def _read_blocks(self, source: str, offset: int):
        events = []
        if source.startswith("---\n"):
            end = source.find("\n---", 4)
            if end >= 0:
                header_end = end + 4
                events.append(Event(EventType.DOCUMENT_PART, DocumentPart(source[:header_end] + ("\n" if header_end < len(source) else ""))))
                rest = source[header_end + (1 if header_end < len(source) else 0):]
                events.extend(self._read_blocks(rest, offset + len(events)))
                return events
        for line in source.splitlines(keepends=True):
            stripped = line.rstrip("\\r\\n")
            ending = line[len(stripped):]
            if not stripped:
                events.append(Event(EventType.DOCUMENT_PART, DocumentPart(ending or "\\n")))
                continue
            heading = re.match(r"^(#{1,6}\\s+)(.*)$", stripped)
            item = re.match(r"^(\\s*(?:[-*+] |\\d+\\. ))(.*)$", stripped)
            if heading or item:
                prefix, text = (heading or item).groups()
                events.append(Event(EventType.DOCUMENT_PART, DocumentPart(prefix)))
                events.append(self._text_event(text, offset + len(events)))
                events.append(Event(EventType.DOCUMENT_PART, DocumentPart(ending)))
            elif re.match(r"^\\s*---\\s*$", stripped):
                events.append(Event(EventType.DOCUMENT_PART, DocumentPart(line)))
            else:
                events.append(self._text_event(stripped, offset + len(events)))
                events.append(Event(EventType.DOCUMENT_PART, DocumentPart(ending)))
        return events

    def _text_event(self, text: str, index: int) -> Event:
        parts, position = [], 0
        for match in self._INLINE.finditer(text):
            parts.append(text[position:match.start()]) if match.start() > position else None
            token = match.group(0)
            if token.startswith("**"):
                parts.extend((Code("**", "bold"), token[2:-2], Code("**", "bold")))
            elif token.startswith("*"):
                parts.extend((Code("*", "italic"), token[1:-1], Code("*", "italic")))
            elif token.startswith(chr(96)):
                parts.append(Code(token, "inline_code"))
            elif token.startswith("!["):
                target = token[token.find("](") + 2:-1]
                parts.append(Code(token, "image", target))
            else:
                close = token.find("](")
                target = token[close + 2:-1]
                parts.extend((Code("[", "link"), token[1:close], Code("](" + target + ")", "link", target)))
            position = match.end()
        if position < len(text): parts.append(text[position:])
        return Event(EventType.TEXT_UNIT, TextUnit(f"markdown-{index + 1}", (TextFragment(tuple(parts or [text])),)))

    def write(self, events) -> str:
        output = []
        for event in events:
            if event.type is EventType.DOCUMENT_PART:
                output.append(event.resource.content if hasattr(event.resource, "content") else str(event.resource))
            elif event.type is EventType.TEXT_UNIT:
                for fragment in event.resource.fragments:
                    for part in fragment.parts:
                        output.append(part.data if isinstance(part, Code) else part)
        return "".join(output)

    def round_trip(self, source: str) -> str:
        return self.write(self.read(source))
