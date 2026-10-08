from execution.capabilities import FilterCapabilities
from execution.registry import FilterDescriptor, FilterRegistry


def test_registry_returns_filter_by_format_and_extension():
    registry = FilterRegistry()
    descriptor = FilterDescriptor(
        id="okapi.openxml",
        backend_id="okapi",
        format="docx",
        extensions=(".docx",),
        mime_types=("application/vnd.openxmlformats-officedocument.wordprocessingml.document",),
        capabilities=FilterCapabilities(supports_skeleton=True, supports_inline_codes=True),
        priority=100,
    )
    registry.register(descriptor)

    result = registry.find_by_extension(".docx")

    assert result == (descriptor,)
