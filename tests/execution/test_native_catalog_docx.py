from pathlib import Path

from execution.backends.native import NativeFilterBackend
from execution.contracts import DocumentRequest, JobStatus
from execution.job import JobCoordinator
from execution.native_catalog import build_native_execution
from execution.service import ExecutionService


def test_native_catalog_executes_docx_through_reader_writer_boundary(tmp_path: Path):
    source = Path("fixtures/docx/reference.docx")
    output = tmp_path / "output.docx"

    registry, backend = build_native_execution()
    service = ExecutionService(
        resolver=__import__("execution.resolver", fromlist=["FilterResolver"]).FilterResolver(registry),
        backends={"native": backend},
        coordinator=JobCoordinator(),
    )

    result = service.execute(
        DocumentRequest(
            document_id="doc-docx",
            input_path=source,
            format="docx",
        ),
        output_path=output,
    )

    assert result.status is JobStatus.COMPLETED
    assert result.units_processed > 0
    assert output.is_file()
