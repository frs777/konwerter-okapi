"""Application-level orchestration for filter execution."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Mapping

from .contracts import DocumentRequest, ExecutionResult, JobStatus
from .job import JobCoordinator, JobState
from .ports import FilterExecutionPort
from .resolver import FilterResolver


class ExecutionService:
    """Coordinate resolution, job lifecycle, and one filter backend execution."""

    def __init__(
        self,
        *,
        resolver: FilterResolver,
        backends: Mapping[str, FilterExecutionPort],
        coordinator: JobCoordinator,
    ) -> None:
        self.resolver = resolver
        self.backends = backends
        self.coordinator = coordinator

    def execute(
        self,
        request: DocumentRequest,
        *,
        output_path: Path,
        operation: str = "translate",
    ) -> ExecutionResult:
        descriptor = self.resolver.resolve(
            request.input_path, format=request.format, filter_id=request.filter_id
        )
        backend = self.backends.get(descriptor.backend_id)
        if backend is None:
            raise ValueError(
                f"no execution backend configured: {descriptor.backend_id}"
            )

        job = self.coordinator.create(request.document_id, operation)
        self.coordinator.transition(job.job_id, JobState.RESOLVING)
        self.coordinator.transition(job.job_id, JobState.PROBING)
        self.coordinator.transition(job.job_id, JobState.OPENING)
        self.coordinator.transition(job.job_id, JobState.EXTRACTING)

        effective_request = request
        if request.filter_id is None:
            effective_request = replace(request, filter_id=descriptor.id)

        try:
            result = backend.execute(
                effective_request,
                job_id=job.job_id,
                output_path=output_path,
            )
        except FileNotFoundError:
            self.coordinator.transition(job.job_id, JobState.FAILED)
            return ExecutionResult(
                job_id=job.job_id,
                status=JobStatus.FAILED,
                error_code="INPUT_NOT_FOUND",
                error_message=f"input file not found: {request.input_path}",
            )
        except Exception as exc:
            self.coordinator.transition(job.job_id, JobState.FAILED)
            return ExecutionResult(
                job_id=job.job_id,
                status=JobStatus.FAILED,
                error_code="EXECUTION_FAILED",
                error_message=str(exc),
            )

        if result.status is not JobStatus.COMPLETED:
            self.coordinator.transition(job.job_id, JobState(result.status))
            return result

        self.coordinator.transition(job.job_id, JobState.EXTRACTED)
        self.coordinator.transition(job.job_id, JobState.TRANSLATING)
        self.coordinator.transition(job.job_id, JobState.APPLYING)
        self.coordinator.transition(job.job_id, JobState.RECONSTRUCTING)
        self.coordinator.transition(job.job_id, JobState.VALIDATING)
        self.coordinator.transition(job.job_id, JobState.COMPLETED)
        return result
