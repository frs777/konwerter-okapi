from __future__ import annotations

from collections.abc import Iterator

from core.document.model import Code, Skeleton, TextFragment, TextUnit
from core.events.model import DocumentPart, Ending, Event, EventType, StartDocument, StartGroup, StartSubDocument, StartSubfilter, EndSubfilter


class EventBuilder(Iterator[Event]):
    """Minimalny odpowiednik kontraktu Okapi EventBuilder."""

    def __init__(self) -> None:
        self._events: list[Event] = []
        self._text_parts: list[str | Code] | None = None
        self._text_unit_id = 0
        self._document_open = False
        self._group_id = 0
        self._subdocument_id = 0
        self._subfilter_id = 0
        self._groups = []
        self._subdocuments = 0

    def __iter__(self) -> Iterator[Event]:
        while self._events:
            yield self._events.pop(0)

    def __next__(self) -> Event:
        if not self._events:
            raise StopIteration
        return self._events.pop(0)

    def has_next(self) -> bool:
        return bool(self._events)

    def start_document(self, name: str) -> None:
        if self._document_open:
            raise RuntimeError("document is already open")
        self._document_open = True
        self._events.append(Event(EventType.START_DOCUMENT, StartDocument(name)))

    def end_document(self) -> None:
        if self._text_parts is not None:
            raise RuntimeError("cannot end document while TextUnit is open")
        if self._groups or self._subdocuments: raise RuntimeError("document has open child resource")
        if not self._document_open:
            raise RuntimeError("document is not open")
        self._events.append(Event(EventType.END_DOCUMENT, Ending()))
        self._document_open = False
        self._group_id = 0
        self._subdocument_id = 0
        self._subfilter_id = 0
        self._groups = []
        self._subdocuments = 0

    def start_text_unit(self, text: str = "") -> None:
        if not self._document_open:
            raise RuntimeError("document is not open")
        if self._text_parts is not None:
            raise RuntimeError("TextUnit is already open")
        self._text_unit_id += 1
        self._text_parts = [text] if text else []

    def add_text(self, text: str) -> None:
        if self._text_parts is None:
            raise RuntimeError("TextUnit is not open")
        if text:
            self._text_parts.append(text)

    def add_code(self, code: Code, *, end_code_now: bool = False) -> None:
        if self._text_parts is None:
            raise RuntimeError("TextUnit is not open")
        self._text_parts.append(code)

    def end_text_unit(self) -> None:
        if self._text_parts is None:
            raise RuntimeError("TextUnit is not open")
        unit = TextUnit(
            id=f"tu-{self._text_unit_id}",
            fragments=(TextFragment(tuple(self._text_parts)),),
        )
        self._events.append(Event(EventType.TEXT_UNIT, unit))
        self._text_parts = None

    def start_group(self, start_marker: str, common_tag_type: str) -> StartGroup:
        if not self._document_open or self._text_parts is not None or not start_marker: raise RuntimeError("invalid group start")
        self._group_id += 1; parent = self._groups[-1].id if self._groups else None
        group = StartGroup(parent, f"group-{self._group_id}", common_tag_type, Skeleton((start_marker,)))
        self._events.append(Event(EventType.START_GROUP, group, group.skeleton)); self._groups.append(group); return group

    def end_group(self, end_marker: str | None = None) -> Ending:
        if not self._groups or isinstance(self._groups[-1], StartSubfilter): raise RuntimeError("no ordinary group is open")
        group=self._groups.pop(); ending=Ending(group.id); skeleton=Skeleton((end_marker,)) if end_marker is not None else Skeleton(())
        self._events.append(Event(EventType.END_GROUP, ending, skeleton)); return ending

    def start_subdocument(self, *, filter_id: str | None = None) -> StartSubDocument:
        if not self._document_open or self._text_parts is not None: raise RuntimeError("invalid subdocument start")
        self._subdocument_id += 1; parent=self._groups[-1].id if self._groups else None
        resource=StartSubDocument(f"subdoc-{self._subdocument_id}", parent, filter_id); self._events.append(Event(EventType.START_SUBDOCUMENT, resource)); self._subdocuments += 1; return resource

    def end_subdocument(self) -> Ending:
        if not self._subdocuments: raise RuntimeError("no subdocument is open")
        self._subdocuments -= 1; resource=Ending(f"subdoc-{self._subdocument_id}-end"); self._events.append(Event(EventType.END_SUBDOCUMENT, resource)); return resource

    def start_subfilter(self, filter_name: str) -> StartSubfilter:
        if not self._document_open or self._text_parts is not None: raise RuntimeError("invalid subfilter start")
        self._subfilter_id += 1; parent=self._groups[-1].id if self._groups else None
        resource=StartSubfilter(f"subfilter-{self._subfilter_id}", filter_name, parent, Skeleton(())); self._events.append(Event(EventType.START_SUBFILTER, resource, resource.skeleton)); self._groups.append(resource); return resource

    def end_subfilter(self) -> EndSubfilter:
        if not self._groups or not isinstance(self._groups[-1], StartSubfilter): raise RuntimeError("no subfilter is open")
        resource=self._groups.pop(); ending=EndSubfilter(f"{resource.id}-end"); self._events.append(Event(EventType.END_SUBFILTER, ending)); return ending

    def start_document_part(self, content: str = "") -> None:
        if not self._document_open:
            raise RuntimeError("document is not open")
        if self._text_parts is not None:
            raise RuntimeError("cannot start DocumentPart while TextUnit is open")
        self._events.append(Event(EventType.DOCUMENT_PART, DocumentPart(content)))

    def end_document_part(self) -> None:
        return None
