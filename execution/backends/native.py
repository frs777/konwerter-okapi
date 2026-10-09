"""Native Python filter backend for the execution boundary."""
from __future__ import annotations

import inspect
from pathlib import Path
from typing import Callable, Mapping

from core.events.model import Event, EventType

from ..contracts import DocumentRequest, ExecutionResult, JobStatus


class NativeFilterBackend:
    """Execute an existing native Python filter without Okapi/JVM."""

    def __init__(
        self,
        factories: Mapping[str, Callable[[], object]],
        *,
        source_modes: Mapping[str, str] | None = None,
    ) -> None:
        self._factories = dict(factories)
        self._source_modes = dict(source_modes or {})

    def execute(
        self,
        request: DocumentRequest,
        *,
        job_id: str,
        output_path: Path,
    ) -> ExecutionResult:
        filter_id = request.filter_id or request.format
        factory = self._factories.get(filter_id)
        if factory is None:
            raise ValueError(f"no native filter configured: {filter_id}")

        if not request.input_path.is_file():
            raise FileNotFoundError(request.input_path)

        filter_instance = factory()
        source_mode = self._source_modes.get(filter_id, "path")
        if source_mode == "path":
            source = str(request.input_path)
        elif source_mode == "text":
            source = request.input_path.read_text(encoding="utf-8")
        else:
            raise ValueError(f"unsupported native source mode: {source_mode}")
        events = tuple(filter_instance.read(source))
        units_processed = sum(
            event.type is EventType.TEXT_UNIT
            for event in events
            if isinstance(event, Event)
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        writer = filter_instance.write
        if "target" in inspect.signature(writer).parameters:
            writer(events, target=output_path)
        else:
            rendered = writer(events)
            if isinstance(rendered, bytes):
                output_path.write_bytes(rendered)
            elif isinstance(rendered, str):
                output_path.write_text(rendered, encoding="utf-8")
            elif not output_path.exists():
                raise ValueError(
                    f"native filter writer did not produce output: {filter_id}"
                )

        if not output_path.is_file():
            raise ValueError(f"native filter writer did not produce output: {filter_id}")

        return ExecutionResult(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            output_path=output_path,
            units_processed=units_processed,
        )
