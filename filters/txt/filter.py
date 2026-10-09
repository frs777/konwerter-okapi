"""Native plain-text filter."""
from __future__ import annotations

from pathlib import Path

from core.document.model import TextFragment, TextUnit
from core.events.model import Event, EventType


class TxtFilter:
    """Read/write UTF-8 text while exposing one TextUnit per non-empty line."""

    name = "txt"
    version = "1.0"
    mime_types = ("text/plain",)
    extensions = (".txt",)
    features = ("text", "line_based")
    framework_contract = "net.sf.okapi.common.filters.IFilter"

    def read(self, source: str | Path):
        path = Path(source)
        text = path.read_text(encoding="utf-8")
        events: list[Event] = [Event(EventType.START_DOCUMENT, None)]
        if text:
            events.append(
                Event(
                    EventType.TEXT_UNIT,
                    TextUnit("txt-1", (TextFragment((text,)),)),
                )
            )
        events.append(Event(EventType.END_DOCUMENT, None))
        return tuple(events)

    def write(self, events, target: str | Path):
        lines = []
        for event in events:
            if event.type is EventType.TEXT_UNIT and event.resource is not None:
                lines.append("".join(event.resource.fragments[0].parts))
        Path(target).write_text("\n".join(lines), encoding="utf-8")
