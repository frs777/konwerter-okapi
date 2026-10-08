"""Format-neutral execution contracts for the Okapi execution layer."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Mapping


class JobStatus(str, Enum):
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


TERMINAL_STATUSES = frozenset({
    JobStatus.COMPLETED,
    JobStatus.CANCELED,
    JobStatus.FAILED,
    JobStatus.TIMEOUT,
    JobStatus.EXECUTOR_CRASHED,
})


@dataclass(frozen=True)
class DocumentRequest:
    document_id: str
    input_path: Path
    format: str
    source_locale: str | None = None
    target_locale: str | None = None
    filter_id: str | None = None
    filter_config_id: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TranslationUnit:
    id: str
    source: str
    target: str | None = None
    translatable: bool = True
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionResult:
    job_id: str
    status: JobStatus | str
    output_path: Path | None = None
    units_processed: int = 0
    error_code: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        try:
            status = JobStatus(self.status)
        except ValueError:
            status = None
        if status not in TERMINAL_STATUSES:
            raise ValueError("ExecutionResult requires a terminal status")
        object.__setattr__(self, "status", status)
