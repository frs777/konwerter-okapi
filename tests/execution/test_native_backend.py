from pathlib import Path

from core.document.model import TextFragment, TextUnit
from core.events.model import Event, EventType
from execution.backends.native import NativeFilterBackend
from execution.contracts import DocumentRequest, JobStatus


class FakeFilter:
    def __init__(self):
        self.sources = []

    def read(self, source):
        self.sources.append(source)
        return (
            Event(EventType.START_DOCUMENT, None),
            Event(EventType.TEXT_UNIT, TextUnit("unit-1", (TextFragment(("unit",)),))),
            Event(EventType.END_DOCUMENT, None),
        )

    def write(self, events, target=None):
        payload = "|".join(
            event.resource.fragments[0].parts[0]
            if event.type is EventType.TEXT_UNIT
            else event.type.value.lower()
            for event in events
        )
        if target is not None:
            Path(target).write_text(payload, encoding="utf-8")
        return payload


def test_native_backend_runs_filter_lifecycle_and_writes_output(tmp_path):
    source = tmp_path / "source.md"
    output = tmp_path / "out.md"
    source.write_text("hello", encoding="utf-8")
    backend = NativeFilterBackend({"markdown": FakeFilter})

    request = DocumentRequest(
        document_id="doc-1",
        input_path=source,
        format="markdown",
        filter_id="markdown",
    )

    result = backend.execute(request, job_id="job-1", output_path=output)

    assert result.status is JobStatus.COMPLETED
    assert result.output_path == output
    assert result.units_processed == 1
    assert output.read_text(encoding="utf-8") == "start_document|unit|end_document"
