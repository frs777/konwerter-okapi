from pathlib import Path

from execution.contracts import DocumentRequest, JobStatus
from execution.job import JobCoordinator
from execution.native_catalog import build_native_execution
from execution.resolver import FilterResolver
from execution.service import ExecutionService


def test_native_txt_preserves_exact_utf8_round_trip(tmp_path: Path):
    source = tmp_path / "input.txt"
    output = tmp_path / "output.txt"
    payload = "Pierwsza linia\n\nDruga: ąćęłńóśźż / 日本語 / 😀  \n"
    source.write_text(payload, encoding="utf-8")

    registry, backend = build_native_execution()
    service = ExecutionService(
        resolver=FilterResolver(registry),
        backends={"native": backend},
        coordinator=JobCoordinator(),
    )
    result = service.execute(
        DocumentRequest(document_id="doc-txt", input_path=source, format="txt"),
        output_path=output,
    )

    assert result.status is JobStatus.COMPLETED
    assert result.units_processed == 1
    assert output.read_text(encoding="utf-8") == payload


def test_native_txt_is_selected_from_extension():
    registry, _ = build_native_execution()
    assert FilterResolver(registry).resolve(Path("example.txt")).id == "native.txt"
