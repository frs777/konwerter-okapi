from okapi_markdown_port.events import (
    DocumentPart,
    Ending,
    Event,
    EventType,
    StartDocument,
    TextUnit,
)


def test_event_stream_has_okapi_core_events() -> None:
    stream = [
        Event(EventType.START_DOCUMENT, StartDocument("test.md")),
        Event(EventType.TEXT_UNIT, TextUnit("u1", "Tekst")),
        Event(EventType.DOCUMENT_PART, DocumentPart("skeleton")),
        Event(EventType.END_DOCUMENT, Ending()),
    ]
    assert [event.type for event in stream] == [
        EventType.START_DOCUMENT,
        EventType.TEXT_UNIT,
        EventType.DOCUMENT_PART,
        EventType.END_DOCUMENT,
    ]


def test_text_unit_keeps_text_separate_from_document_part() -> None:
    unit = TextUnit("u1", "Ala <b>ma</b> kota")
    part = DocumentPart("oryginalny fragment")
    assert unit.source == "Ala <b>ma</b> kota"
    assert part.content == "oryginalny fragment"


def test_start_document_keeps_document_name() -> None:
    resource = StartDocument("przyklad.md")
    assert resource.name == "przyklad.md"
