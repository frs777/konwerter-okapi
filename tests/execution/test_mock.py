from pathlib import Path

import pytest

from execution.backends.mock import MockFilterBackend
from execution.contracts import DocumentRequest, JobStatus


def test_mock_backend_copies_document_and_returns_terminal_result(tmp_path: Path):
    source = tmp_path / "input.txt"
    source.write_text("Hello world", encoding="utf-8")
    output = tmp_path / "output.txt"
    request = DocumentRequest(
        document_id="doc-1",
        input_path=source,
        format="txt",
    )

    result = MockFilterBackend().execute(request, job_id="job-1", output_path=output)

    assert result.status is JobStatus.COMPLETED
    assert result.job_id == "job-1"
    assert result.output_path == output
    assert output.read_text(encoding="utf-8") == "Hello world"
    assert result.units_processed == 1


def test_mock_backend_rejects_missing_input(tmp_path: Path):
    request = DocumentRequest(
        document_id="doc-1",
        input_path=tmp_path / "missing.txt",
        format="txt",
    )

    with pytest.raises(FileNotFoundError):
        MockFilterBackend().execute(request, job_id="job-1", output_path=tmp_path / "out.txt")
