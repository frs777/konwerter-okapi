from pathlib import Path

import pytest

from execution.backends.mock import MockFilterBackend
from execution.contracts import DocumentRequest, ExecutionResult, JobStatus
from execution.job import JobCoordinator
from execution.registry import FilterDescriptor, FilterRegistry
from execution.resolver import FilterResolver
from execution.service import ExecutionService


def make_service() -> ExecutionService:
    registry = FilterRegistry(
        [
            FilterDescriptor(
                id="native.txt",
                backend_id="mock",
                format="txt",
                extensions=(".txt",),
            )
        ]
    )
    return ExecutionService(
        resolver=FilterResolver(registry),
        backends={"mock": MockFilterBackend()},
        coordinator=JobCoordinator(),
    )


def test_execution_service_runs_one_document_through_resolved_backend(tmp_path: Path):
    source = tmp_path / "input.txt"
    source.write_text("Hello", encoding="utf-8")
    output = tmp_path / "output.txt"
    request = DocumentRequest(
        document_id="doc-1",
        input_path=source,
        format="txt",
    )

    result = make_service().execute(request, output_path=output)

    assert result.status is JobStatus.COMPLETED
    assert result.output_path == output
    assert output.read_text(encoding="utf-8") == "Hello"


def test_execution_service_returns_failed_result_and_records_failed_job(tmp_path: Path):
    request = DocumentRequest(
        document_id="doc-1",
        input_path=tmp_path / "missing.txt",
        format="txt",
    )
    service = make_service()

    result = service.execute(request, output_path=tmp_path / "output.txt")

    assert result.status is JobStatus.FAILED
    assert result.error_code == "INPUT_NOT_FOUND"


def test_execution_service_preserves_terminal_failure_from_backend(tmp_path: Path):
    class FailedBackend:
        def execute(self, request, *, job_id, output_path):
            return ExecutionResult(
                job_id=job_id,
                status=JobStatus.FAILED,
                error_code="FILTER_FAILED",
            )

    registry = FilterRegistry(
        [
            FilterDescriptor(
                id="failing.txt",
                backend_id="failing",
                format="txt",
                extensions=(".txt",),
            )
        ]
    )
    service = ExecutionService(
        resolver=FilterResolver(registry),
        backends={"failing": FailedBackend()},
        coordinator=JobCoordinator(),
    )
    source = tmp_path / "input.txt"
    source.write_text("Hello", encoding="utf-8")

    result = service.execute(
        DocumentRequest("doc-1", source, "txt"),
        output_path=tmp_path / "output.txt",
    )

    assert result.status is JobStatus.FAILED
    assert result.error_code == "FILTER_FAILED"


def test_execution_service_rejects_unknown_backend_configuration(tmp_path: Path):
    registry = FilterRegistry(
        [
            FilterDescriptor(
                id="broken.txt",
                backend_id="missing",
                format="txt",
                extensions=(".txt",),
            )
        ]
    )
    service = ExecutionService(
        resolver=FilterResolver(registry),
        backends={},
        coordinator=JobCoordinator(),
    )
    source = tmp_path / "input.txt"
    source.write_text("Hello", encoding="utf-8")

    with pytest.raises(ValueError, match="backend"):
        service.execute(
            DocumentRequest("doc-1", source, "txt"),
            output_path=tmp_path / "output.txt",
        )
