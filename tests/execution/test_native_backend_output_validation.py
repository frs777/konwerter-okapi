from pathlib import Path

import pytest

from execution.backends.native import NativeFilterBackend
from execution.contracts import DocumentRequest


class SilentTargetFilter:
    def read(self, source):
        return ()

    def write(self, events, target=None):
        return None


def test_native_backend_rejects_writer_that_does_not_create_target(tmp_path: Path):
    source = tmp_path / "source.txt"
    output = tmp_path / "missing.txt"
    source.write_text("hello", encoding="utf-8")

    backend = NativeFilterBackend({"silent": SilentTargetFilter})
    request = DocumentRequest(
        document_id="doc-1", input_path=source, format="txt", filter_id="silent"
    )

    with pytest.raises(ValueError, match="did not produce output"):
        backend.execute(request, job_id="job-1", output_path=output)
