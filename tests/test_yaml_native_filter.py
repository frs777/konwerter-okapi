from core.events.model import EventType
from filters.yaml.filter import YamlFilter


def _text_units(events):
    return [e.resource for e in events if e.type is EventType.TEXT_UNIT]


def test_yaml_filter_extracts_mapping_values_but_not_keys():
    source = "title: Hello\nname: World\n"

    events = YamlFilter().read(source)

    units = _text_units(events)
    assert [unit.metadata["yaml_path"] for unit in units] == ["title", "name"]
    assert [unit.fragments[0].parts[0] for unit in units] == ["Hello", "World"]


def test_yaml_filter_extracts_nested_mapping_and_sequence_values():
    source = "root:\n  title: Hello\n  items:\n    - One\n    - Two\n"

    units = _text_units(YamlFilter().read(source))

    assert [unit.metadata["yaml_path"] for unit in units] == [
        "root/title",
        "root/items/0",
        "root/items/1",
    ]
    assert [unit.fragments[0].parts[0] for unit in units] == ["Hello", "One", "Two"]


def test_yaml_filter_round_trip_preserves_original_source_exactly():
    source = "# keep me\ntitle: Hello  # inline comment\nitems:\n  - One\n"

    assert YamlFilter().round_trip(source) == source


def test_yaml_filter_writer_replaces_only_translatable_scalar_spans():
    source = "title: Hello  # keep this\nitems:\n  - One\n"

    events = list(YamlFilter().read(source))
    units = _text_units(events)
    replacement = "Witaj"
    from dataclasses import replace

    changed = replace(
        units[0],
        fragments=(replace(units[0].fragments[0], parts=(replacement,)),),
    )
    events = tuple(
        replace(e, resource=changed)
        if e.type is EventType.TEXT_UNIT and e.resource.id == changed.id
        else e
        for e in events
    )

    assert YamlFilter().write(events) == "title: Witaj  # keep this\nitems:\n  - One\n"


def test_yaml_filter_preserves_quote_style_when_value_changes():
    from dataclasses import replace

    source = "title: \"Hello\"\n"
    events = list(YamlFilter().read(source))
    unit = _text_units(events)[0]
    changed = replace(unit, fragments=(replace(unit.fragments[0], parts=("Witaj \"świecie\"",)),))
    events = tuple(
        replace(e, resource=changed)
        if e.type is EventType.TEXT_UNIT
        else e
        for e in events
    )

    assert YamlFilter().write(events) == 'title: "Witaj \\"świecie\\""\n'


def test_yaml_filter_preserves_literal_block_structure_when_value_changes():
    from dataclasses import replace

    source = "text: |\n  line one\n  line two\n"
    events = list(YamlFilter().read(source))
    unit = _text_units(events)[0]
    changed = replace(
        unit,
        fragments=(replace(unit.fragments[0], parts=("nowa linia\ndruga linia\n",)),),
    )
    events = tuple(
        replace(e, resource=changed)
        if e.type is EventType.TEXT_UNIT
        else e
        for e in events
    )

    assert YamlFilter().write(events) == "text: |\n  nowa linia\n  druga linia\n"
