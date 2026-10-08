"""Job coordination and duplicate-operation prevention."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import uuid4


class JobState(str, Enum):
    CREATED = "created"
    RESOLVING = "resolving"
    PROBING = "probing"
    OPENING = "opening"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    TRANSLATING = "translating"
    APPLYING = "applying"
    RECONSTRUCTING = "reconstructing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"
    TIMEOUT = "timeout"
    EXECUTOR_CRASHED = "executor_crashed"


TERMINAL_STATES = frozenset({
    JobState.COMPLETED,
    JobState.CANCELED,
    JobState.FAILED,
    JobState.TIMEOUT,
    JobState.EXECUTOR_CRASHED,
})


@dataclass
class JobStateRecord:
    job_id: str
    document_id: str
    operation: str
    state: JobState = JobState.CREATED


class JobCoordinator:
    def __init__(self) -> None:
        self._jobs: dict[tuple[str, str], JobStateRecord] = {}

    def create(self, document_id: str, operation: str) -> JobStateRecord:
        key = (document_id, operation)
        current = self._jobs.get(key)
        if current is not None and current.state not in TERMINAL_STATES:
            return current
        job = JobStateRecord(uuid4().hex, document_id, operation)
        self._jobs[key] = job
        return job

    def transition(self, job_id: str, state: JobState) -> JobStateRecord:
        for job in self._jobs.values():
            if job.job_id == job_id:
                job.state = state
                return job
        raise KeyError(f"unknown job: {job_id}")
