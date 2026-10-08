from core.document.model import Code, Skeleton, TextFragment, TextUnit
from core.events.model import Event, EventType, StartDocument, Ending


def test_event_normalizer_produces_stable_representation():
    from differential.event_normalizer.normalizer import EventNormalizer
    events = [
        Event(EventType.START_DOCUMENT, StartDocument("x.docx")),
        Event(EventType.TEXT_UNIT, TextUnit("1", (TextFragment(("A", Code("B", "hyperlink", "https://x"))),), {"style": "Heading1"})),
        Event(EventType.DOCUMENT_PART, Skeleton(("paragraph", "table"))),
        Event(EventType.END_DOCUMENT, Ending()),
    ]
    normalized = EventNormalizer().normalize(events)
    assert normalized[0]["type"] == "START_DOCUMENT"
    assert normalized[1]["resource"]["fragments"][0]["parts"][1]["target"] == "https://x"
    assert normalized[2]["resource"]["parts"] == ["paragraph", "table"]


def test_differential_comparator_accepts_equivalent_streams():
    from differential.comparator.comparator import DifferentialComparator
    events = [Event(EventType.TEXT_UNIT, TextUnit("1", (TextFragment(("A",)),)))]
    result = DifferentialComparator().compare(events, list(events))
    assert result.equal is True
    assert result.differences == ()


def test_differential_comparator_reports_first_difference():
    from differential.comparator.comparator import DifferentialComparator
    left = [Event(EventType.TEXT_UNIT, TextUnit("1", (TextFragment(("A",)),)))]
    right = [Event(EventType.TEXT_UNIT, TextUnit("1", (TextFragment(("B",)),)))]
    result = DifferentialComparator().compare(left, right)
    assert result.equal is False
    assert result.differences
    assert "TEXT_UNIT" in result.differences[0]


def test_differential_report_renders_result():
    from differential.comparator.comparator import ComparisonResult
    from differential.reports.report import DifferentialReport
    assert DifferentialReport().render(ComparisonResult(True, ())) == 'Wyniki są równoważne.'
    assert 'Różnice:' in DifferentialReport().render(ComparisonResult(False, ('x',)))
