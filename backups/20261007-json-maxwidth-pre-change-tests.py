from dataclasses import replace

from core.events.model import EventType
from filters.json.filter import JsonFilter


def _units(events):
    return [event.resource for event in events if event.type is EventType.TEXT_UNIT]


def test_json_filter_extracts_string_values_and_uses_keys_as_names():
    source = '{"key1": "Text1", "key2": "Text2"}'

    units = _units(JsonFilter().read(source))

    assert [unit.metadata["json_path"] for unit in units] == ["/key1", "/key2"]
    assert [unit.metadata["name"] for unit in units] == ["key1", "key2"]
    assert [unit.fragments[0].parts[0] for unit in units] == ["Text1", "Text2"]


def test_json_filter_round_trip_is_lossless():
    source = '{\n  "key": "Text",\n  "nested": ["One", "Two"]\n}\n'

    assert JsonFilter().round_trip(source) == source


def test_json_filter_writer_replaces_only_string_value_span():
    source = '{"key": "Hello", "keep": "World"}'
    events = list(JsonFilter().read(source))
    unit = _units(events)[0]
    changed = replace(unit, fragments=(replace(unit.fragments[0], parts=("Witaj",)),))
    events = tuple(
        replace(event, resource=changed)
        if event.type is EventType.TEXT_UNIT and event.resource.id == changed.id
        else event
        for event in events
    )

    assert JsonFilter().write(events) == '{"key": "Witaj", "keep": "World"}'


def test_json_filter_respects_extract_all_pairs_and_standalone_parameters():
    source = '{"name": "Named", "items": ["One", "Two"]}'

    units = _units(JsonFilter(parameters={"extractAllPairs": False}).read(source))
    assert [unit.fragments[0].parts[0] for unit in units] == []

    units = _units(JsonFilter(parameters={"extractAllPairs": False, "extractStandalone": True}).read(source))
    assert [unit.fragments[0].parts[0] for unit in units] == ["One", "Two"]


def test_json_filter_respects_full_key_path_and_leading_slash_parameters():
    source = '{"root": {"title": "Hello"}}'

    units = _units(JsonFilter(parameters={"useFullKeyPath": True, "useLeadingSlashOnKeyPath": False}).read(source))
    assert units[0].metadata["name"] == "root/title"

    units = _units(JsonFilter(parameters={"useFullKeyPath": True, "useLeadingSlashOnKeyPath": True}).read(source))
    assert units[0].metadata["name"] == "/root/title"


def test_json_filter_does_not_treat_numeric_object_keys_as_array_items():
    source = '{"123": "Named", "items": ["Standalone"]}'

    units = _units(JsonFilter(parameters={"extractAllPairs": True, "extractStandalone": False}).read(source))
    assert [unit.fragments[0].parts[0] for unit in units] == ["Named"]


def test_json_filter_id_rules_override_text_unit_name_and_do_not_extract_id_value():
    source = '{"id": "1234567890", "foo": "Extract me"}'
    units = _units(JsonFilter(parameters={"idRules": "id"}).read(source))
    assert [unit.fragments[0].parts[0] for unit in units] == ["Extract me"]
    assert units[0].metadata["name"] == "1234567890"


def test_json_filter_note_rules_attach_note_metadata_to_object_text_units():
    source = '{"description": "blah blah blah", "foo": "Extract me"}'
    units = _units(JsonFilter(parameters={"noteRules": "description"}).read(source))
    assert len(units) == 1
    assert units[0].metadata["notes"] == '[{"from": "description", "text": "blah blah blah"}]'


def test_json_filter_generic_meta_rules_attach_metadata_to_object_text_units():
    source = '{"name": "value", "foo": "generic meta"}'
    units = _units(JsonFilter(parameters={"genericMetaRules": "foo"}).read(source))
    assert len(units) == 1
    assert units[0].fragments[0].parts[0] == "value"
    assert units[0].metadata["generic_meta"] == '{"foo": "generic meta"}'


def test_json_filter_extraction_rules_override_extract_all_pairs():
    source = '{"name": "value", "foo": "extract me"}'
    units = _units(JsonFilter(parameters={"extractAllPairs": True, "extractionRules": "foo"}).read(source))
    assert [unit.fragments[0].parts[0] for unit in units] == ["extract me"]


def test_json_filter_use_id_stack_builds_nested_id_name():
    source = '{"id": "1234567890", "content": {"id": "id2", "foo": "Extract me"}}'
    units = _units(JsonFilter(parameters={"idRules": "id", "useIdStack": True}).read(source))
    assert len(units) == 1
    assert units[0].metadata["name"] == "1234567890/id2"


class _FakeSubfilter:
    name = "fake"

    def read(self, source: str):
        from core.events.model import Event, EventType
        from core.document.model import TextFragment, TextUnit
        return (
            Event(EventType.START_DOCUMENT, source),
            Event(
                EventType.TEXT_UNIT,
                TextUnit(
                    id="sub-1",
                    fragments=(TextFragment((source.upper(),)),),
                    metadata={"subfilter": "fake"},
                ),
            ),
            Event(EventType.END_DOCUMENT, source),
        )


def test_json_filter_subfilter_rules_gate_injected_subfilter_and_wrap_its_events():
    source = '{"html": "Hello", "plain": "World"}'
    events = list(JsonFilter(parameters={
        "subfilter": _FakeSubfilter(),
        "subfilterRules": "html",
    }).read(source))

    assert [event.type for event in events] == [
        EventType.START_DOCUMENT,
        EventType.START_SUBFILTER,
        EventType.TEXT_UNIT,
        EventType.END_SUBFILTER,
        EventType.TEXT_UNIT,
        EventType.END_DOCUMENT,
    ]
    assert events[1].resource.filter_name == "fake"
    assert events[2].resource.fragments[0].parts == ("HELLO",)
    assert events[4].resource.fragments[0].parts == ("World",)


def test_json_filter_subfilter_without_rules_applies_to_each_extractable_string():
    source = '{"first": "One", "second": "Two"}'
    events = list(JsonFilter(parameters={"subfilter": _FakeSubfilter()}).read(source))

    assert [event.type for event in events].count(EventType.START_SUBFILTER) == 2
    assert [event.type for event in events].count(EventType.END_SUBFILTER) == 2
