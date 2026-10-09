from pathlib import Path

from execution.backends.native import NativeFilterBackend
from execution.contracts import DocumentRequest, JobStatus
from execution.job import JobCoordinator
from execution.registry import FilterDescriptor, FilterRegistry
from execution.resolver import FilterResolver
from execution.service import ExecutionService
from filters.markdown.filter import MarkdownFilter


def test_execution_service_runs_real_native_markdown_filter(tmp_path: Path):
    source = tmp_path / "input.md"
    output = tmp_path / "output.md"
    source.write_text("# Hello\n\nBody", encoding="utf-8")

    registry = FilterRegistry(
        [
            FilterDescriptor(
                id="native.markdown",
                backend_id="native",
                format="markdown",
                extensions=(".md", ".markdown"),
                priority=100,
            )
        ]
    )
    service = ExecutionService(
        resolver=FilterResolver(registry),
        backends={"native": NativeFilterBackend({"native.markdown": MarkdownFilter}, source_modes={"native.markdown": "text"})},
        coordinator=JobCoordinator(),
    )

    result = service.execute(
        DocumentRequest(
            document_id="doc-1",
            input_path=source,
            format="markdown",
            filter_id="native.markdown",
        ),
        output_path=output,
    )

    assert result.status is JobStatus.COMPLETED
    assert result.units_processed == 3
    assert output.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
