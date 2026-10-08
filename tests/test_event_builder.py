from core.events.builder import EventBuilder
from core.events.model import EventType
from core.document.model import Code


def test_event_builder_builds_start_text_unit_code_and_end_document():
    builder = EventBuilder()
    builder.start_document("sample.md")
    builder.start_text_unit("Hello ")
    builder.add_text("world")
    builder.add_code(Code("inline", "inline"), end_code_now=True)
    builder.end_text_unit()
    builder.end_document()

    events = list(builder)
    assert [event.type for event in events] == [EventType.START_DOCUMENT, EventType.TEXT_UNIT, EventType.END_DOCUMENT]
    unit = events[1].resource
    assert unit.fragments[0].parts == ("Hello ", "world", Code("inline", "inline"))


def test_event_builder_queues_document_parts_and_preserves_order():
    builder = EventBuilder()
    builder.start_document("sample.md")
    builder.start_document_part("---\\n")
    builder.end_document_part()
    builder.start_text_unit("Text")
    builder.end_text_unit()
    builder.end_document()

    events = list(builder)
    assert [event.type for event in events] == [EventType.START_DOCUMENT, EventType.DOCUMENT_PART, EventType.TEXT_UNIT, EventType.END_DOCUMENT]
    assert events[1].resource.content == "---\\n"


def test_event_builder_rejects_nested_text_units():
    builder = EventBuilder()
    builder.start_document("x")
    builder.start_text_unit("one")
    try:
        builder.start_text_unit("two")
    except RuntimeError:
        pass
    else:
        raise AssertionError("nested TextUnit must be rejected")


def test_event_builder_supports_nested_groups_and_group_skeletons():
    builder = EventBuilder(); builder.start_document('x'); outer = builder.start_group('<table>', 'table'); inner = builder.start_group('<tr>', 'row'); builder.start_text_unit('cell'); builder.end_text_unit(); builder.end_group('</tr>'); builder.end_group('</table>'); builder.end_document(); events=list(builder)
    assert [e.type for e in events] == [EventType.START_DOCUMENT, EventType.START_GROUP, EventType.START_GROUP, EventType.TEXT_UNIT, EventType.END_GROUP, EventType.END_GROUP, EventType.END_DOCUMENT]
    assert events[2].resource.parent_id == outer.id and events[1].resource.skeleton.parts == ('<table>',) and events[5].skeleton.parts == ('</table>',)

def test_event_builder_supports_subdocument_lifecycle():
    builder=EventBuilder(); builder.start_document('x'); start=builder.start_subdocument(); builder.start_text_unit('sub'); builder.end_text_unit(); end=builder.end_subdocument(); builder.end_document(); events=list(builder)
    assert [e.type for e in events] == [EventType.START_DOCUMENT, EventType.START_SUBDOCUMENT, EventType.TEXT_UNIT, EventType.END_SUBDOCUMENT, EventType.END_DOCUMENT]
    assert start.id.startswith('subdoc-') and end.id.startswith('subdoc-')

def test_event_builder_supports_subfilter_as_group_lifecycle():
    builder=EventBuilder(); builder.start_document('x'); start=builder.start_subfilter('html'); builder.start_text_unit('inner'); builder.end_text_unit(); end=builder.end_subfilter(); builder.end_document(); events=list(builder)
    assert [e.type for e in events] == [EventType.START_DOCUMENT, EventType.START_SUBFILTER, EventType.TEXT_UNIT, EventType.END_SUBFILTER, EventType.END_DOCUMENT]
    assert start.filter_name == 'html' and end.id.startswith('subfilter-')

def test_event_builder_rejects_unbalanced_group_and_subdocument():
    builder=EventBuilder(); builder.start_document('x')
    try: builder.end_group('</x>')
    except RuntimeError: pass
    else: raise AssertionError('unbalanced group must be rejected')
    builder.start_subdocument()
    try: builder.end_document()
    except RuntimeError: pass
    else: raise AssertionError('open subdocument must block document end')
