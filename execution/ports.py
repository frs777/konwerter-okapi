from pathlib import Path
from typing import Protocol

from .contracts import DocumentRequest, ExecutionResult


class FilterExecutionPort(Protocol):
    def execute(
        self,
        request: DocumentRequest,
        *,
        job_id: str,
        output_path: Path,
    ) -> ExecutionResult:
        """Execute one document job through a filter backend."""
        ...
