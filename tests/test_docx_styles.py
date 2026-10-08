from filters.docx.styles import StyleDefinition, StyleRegistry


def test_registry_resolves_based_on_inheritance_and_direct_override():
    registry = StyleRegistry(
        [
            StyleDefinition("Normal", "paragraph", run_properties={"font": "Serif", "bold": "false"}),
            StyleDefinition(
                "Heading",
                "paragraph",
                based_on="Normal",
                run_properties={"font": "Sans"},
            ),
            StyleDefinition(
                "Heading2",
                "paragraph",
                based_on="Heading",
                run_properties={"size": "28"},
            ),
        ],
        document_defaults={"font": "Default", "italic": "false"},
    )

    resolved = registry.resolve_run_properties("Heading2")

    assert resolved == {
        "font": "Sans",
        "bold": "false",
        "italic": "false",
        "size": "28",
    }


def test_registry_keeps_explicit_false_toggle_from_child_style():
    registry = StyleRegistry(
        [
            StyleDefinition("Normal", "paragraph", run_properties={"bold": "true", "italic": "true"}),
            StyleDefinition(
                "Child",
                "paragraph",
                based_on="Normal",
                run_properties={"bold": "false"},
            ),
        ]
    )

    assert registry.resolve_run_properties("Child") == {
        "bold": "false",
        "italic": "true",
    }


def test_registry_uses_default_style_for_missing_style():
    registry = StyleRegistry(
        [
            StyleDefinition(
                "Normal",
                "paragraph",
                default=True,
                run_properties={"font": "Serif"},
            )
        ],
        document_defaults={"size": "24"},
    )

    assert registry.resolve_run_properties(None) == {
        "size": "24",
        "font": "Serif",
    }


def test_registry_ignores_parent_of_different_style_type():
    registry = StyleRegistry(
        [
            StyleDefinition("CharBase", "character", run_properties={"italic": "true"}),
            StyleDefinition(
                "Paragraph",
                "paragraph",
                based_on="CharBase",
                run_properties={"bold": "true"},
            ),
        ]
    )

    assert registry.resolve_run_properties("Paragraph") == {"bold": "true"}


def test_registry_detects_cycles_in_based_on():
    registry = StyleRegistry(
        [
            StyleDefinition("A", "paragraph", based_on="B"),
            StyleDefinition("B", "paragraph", based_on="A"),
        ]
    )

    try:
        registry.resolve_run_properties("A")
    except ValueError as exc:
        assert "cycle" in str(exc).lower()
    else:
        raise AssertionError("expected a basedOn cycle error")


def test_registry_parses_real_okapi_fixture_styles():
    from zipfile import ZipFile

    with ZipFile("fixtures/docx/okapi/1313-numbering-1.docx") as archive:
        registry = StyleRegistry.from_xml(archive.read("word/styles.xml"))

    resolved = registry.resolve_run_properties("Heading")
    assert resolved["font"] == "Liberation Sans"
    assert resolved["size"] == "28"
    assert "bold" not in resolved

def test_reader_uses_style_registry_for_run_style_resolution():
    from filters.docx.reader import DocxReader

    events = list(DocxReader().read("fixtures/docx/okapi/1313-numbering-1.docx"))
    heading_units = [
        event.resource
        for event in events
        if getattr(event, "resource", None) is not None
        and getattr(event.resource, "metadata", None)
        and event.resource.metadata.get("style") == "Normal"
    ]
    assert heading_units
    assert any(
        fragment.style and fragment.style.get("resolved_font") == "Liberation Serif"
        for unit in heading_units
        for fragment in unit.fragments
    )

def test_character_style_linked_to_paragraph_style_is_combined():
    registry = StyleRegistry(
        [
            StyleDefinition("Paragraph", "paragraph", run_properties={"font": "Serif"}),
            StyleDefinition(
                "Character",
                "character",
                linked_style="Paragraph",
                run_properties={"italic": "true"},
            ),
        ]
    )

    assert registry.resolve_character_run_properties(None, "Character") == {
        "font": "Serif",
        "italic": "true",
    }
