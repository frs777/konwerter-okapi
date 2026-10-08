from core.events.model import Event, EventType
from core.filter import Filter
from core.reader.base import Reader
from core.writer.base import Writer


class MemoryReader(Reader):
    def read(self, source: str):
        return (
            Event(EventType.START_DOCUMENT, source),
            Event(EventType.END_DOCUMENT, None),
        )


class MemoryWriter(Writer):
    def __init__(self):
        self.events = []

    def write(self, event: Event) -> None:
        self.events.append(event)


def test_filter_runs_reader_events_through_writer():
    writer = MemoryWriter()
    filter_ = Filter(reader=MemoryReader(), writer=writer)

    result = filter_.run("document.md")

    assert result == 2
    assert [event.type for event in writer.events] == [
        EventType.START_DOCUMENT,
        EventType.END_DOCUMENT,
    ]


def test_filter_exposes_okapi_style_open_has_next_next_close_lifecycle():
    from core.filter import Filter

    class Reader:
        def read(self, source):
            return iter(["event-1", "event-2"])

    class Writer:
        def __init__(self):
            self.events = []

        def write(self, event):
            self.events.append(event)

    writer = Writer()
    filter_ = Filter(Reader(), writer)
    filter_.open('source')
    assert filter_.has_next() is True
    assert filter_.next() == 'event-1'
    assert filter_.next() == 'event-2'
    assert filter_.has_next() is False
    filter_.close()
