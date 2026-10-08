from pathlib import Path

from execution.capabilities import FilterCapabilities
from execution.registry import FilterDescriptor, FilterRegistry
from execution.resolver import FilterResolver


def test_resolver_selects_highest_priority_candidate():
    registry = FilterRegistry()
    registry.register(
        FilterDescriptor(
            id="native.docx",
            backend_id="native",
            format="docx",
            extensions=(".docx",),
            capabilities=FilterCapabilities(),
            priority=10,
        )
    )
    registry.register(
        FilterDescriptor(
            id="okapi.openxml",
            backend_id="okapi",
            format="docx",
            extensions=(".docx",),
            capabilities=FilterCapabilities(supports_skeleton=True),
            priority=100,
        )
    )

    resolved = FilterResolver(registry).resolve(Path("source.docx"))

    assert resolved.id == "okapi.openxml"


def test_resolver_rejects_unknown_extension():
    registry = FilterRegistry()

    try:
        FilterResolver(registry).resolve(Path("source.unknown"))
    except ValueError as exc:
        assert "unsupported" in str(exc).lower()
    else:
        raise AssertionError("resolver should reject unsupported format")
