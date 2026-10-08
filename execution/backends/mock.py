from pathlib import Path

from ..contracts import DocumentRequest, ExecutionResult, JobStatus


class MockFilterBackend:
    """Deterministic backend used to exercise the execution boundary."""

    def execute(
        self,
        request: DocumentRequest,
        *,
        job_id: str,
        output_path: Path,
    ) -> ExecutionResult:
        if not request.input_path.is_file():
            raise FileNotFoundError(request.input_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(request.input_path.read_bytes())

        return ExecutionResult(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            output_path=output_path,
            units_processed=1,
        )
