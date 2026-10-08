from __future__ import annotations

from collections.abc import Iterator
from core.reader.base import Reader
from core.writer.base import Writer


class Filter:
    """Pythonowy odpowiednik kontraktu IFilter/AbstractFilter na poziomie lifecycle.

    Reader odpowiada za ekstrakcję zdarzeń, Filter za lifecycle i iterację,
    a Writer pozostaje osobną warstwą zapisu. Nie kopiuje implementacji Okapi.
    """

    def __init__(self, reader: Reader, writer: Writer) -> None:
        self.reader = reader
        self.writer = writer
        self._events: Iterator[object] | None = None
        self._next_event: object = _EMPTY
        self._opened = False

    def open(self, source: str) -> None:
        self._events = iter(self.reader.read(source))
        self._next_event = _EMPTY
        self._opened = True

    def has_next(self) -> bool:
        if not self._opened or self._events is None:
            return False
        if self._next_event is not _EMPTY:
            return True
        try:
            self._next_event = next(self._events)
        except StopIteration:
            return False
        return True

    def next(self) -> object:
        if not self.has_next():
            raise StopIteration
        event = self._next_event
        self._next_event = _EMPTY
        return event

    def close(self) -> None:
        self._events = None
        self._next_event = _EMPTY
        self._opened = False

    def run(self, source: str) -> int:
        self.open(source)
        count = 0
        try:
            while self.has_next():
                self.writer.write(self.next())
                count += 1
        finally:
            self.close()
        return count


_EMPTY = object()
