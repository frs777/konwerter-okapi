from pathlib import Path

from execution.backends.native import NativeFilterBackend
from execution.contracts import DocumentRequest, JobStatus
from execution.job import JobCoordinator
from execution.native_catalog import build_native_execution
from execution.service import ExecutionService


def test_native_catalog_builds_ready_to_execute_service():
    from execution.native_catalog import build_native_execution_service


def test_execution_package_exports_native_service_factory():
    from execution import build_native_execution_service

    service = build_native_execution_service()

    assert isinstance(service, ExecutionService)

    service = build_native_execution_service()

    assert isinstance(service, ExecutionService)
    assert "native" in service.backends


def test_native_catalog_factory_executes_json_without_manual_backend_wiring(tmp_path: Path):
    from execution import build_native_execution_service

    source = tmp_path / "input.json"
    output = tmp_path / "output.json"
    source.write_text('{"title": "Hello", "count": 2}\n', encoding="utf-8")

    service = build_native_execution_service()
    result = service.execute(
        DocumentRequest(document_id="doc-json", input_path=source, format="json"),
        output_path=output,
    )

    assert result.status is JobStatus.COMPLETED
    assert result.units_processed == 1
    assert output.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")


def test_native_catalog_contains_confirmed_direct_filters():
    registry, backend = build_native_execution()

    ids = {descriptor.id for descriptor in registry.find_by_extension(".md")}
    assert ids == {"native.markdown"}

    assert isinstance(backend, NativeFilterBackend)


def test_native_catalog_resolves_xliff_versions_by_content(tmp_path: Path):
    from execution.resolver import FilterResolver

    v12 = tmp_path / "input-12.xlf"
    v12.write_text(
        '<?xml version="1.0"?><xliff xmlns="urn:oasis:names:tc:xliff:document:1.2"><file><body><trans-unit id="1"><source>Hello</source></trans-unit></body></file></xliff>',
        encoding="utf-8",
    )
    v20 = tmp_path / "input-20.xlf"
    v20.write_text(
        '<?xml version="1.0"?><xliff xmlns="urn:oasis:names:tc:xliff:document:2.0"><file><unit id="1"><segment><source>Hello</source></segment></unit></file></xliff>',
        encoding="utf-8",
    )

    registry, _ = build_native_execution()
    resolver = FilterResolver(registry)

    assert resolver.resolve(v12).id == "native.xliff"
    assert resolver.resolve(v20).id == "native.xliff2"


def test_native_catalog_runs_yaml_automatically(tmp_path: Path):
    source = tmp_path / "input.yaml"
    output = tmp_path / "output.yaml"
    source.write_text("title: Hello\ncount: 2\n", encoding="utf-8")

    registry, backend = build_native_execution()
    service = ExecutionService(
        resolver=__import__("execution.resolver", fromlist=["FilterResolver"]).FilterResolver(registry),
        backends={"native": backend},
        coordinator=JobCoordinator(),
    )

    result = service.execute(
        DocumentRequest(
            document_id="doc-yaml",
            input_path=source,
            format="yaml",
        ),
        output_path=output,
    )

    assert result.status is JobStatus.COMPLETED
    assert result.units_processed == 2
    assert output.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")


def test_native_catalog_uses_path_mode_for_epub(tmp_path: Path):
    source = tmp_path / "input.epub"
    output = tmp_path / "output.epub"
    source.write_bytes(b"not a real epub")

    registry, backend = build_native_execution()
    descriptor = registry.find_by_extension(".epub")[0]
    assert descriptor.id == "native.epub"

    request = DocumentRequest(
        document_id="doc-epub",
        input_path=source,
        format="epub",
        filter_id=descriptor.id,
    )

    try:
        backend.execute(request, job_id="job-epub", output_path=output)
    except Exception as exc:
        assert "File is not a zip file" in str(exc)
    else:
        raise AssertionError("invalid EPUB should be rejected by the real filter")


def test_native_catalog_contains_xliff_1_and_2_and_resolves_explicit_format(tmp_path: Path):
    from execution.resolver import FilterResolver

    registry, backend = build_native_execution()
    resolver = FilterResolver(registry)

    source12 = tmp_path / "source.xlf"
    source12.write_text(
        '<xliff xmlns="urn:oasis:names:tc:xliff:document:1.2"><file><body><trans-unit id="1"><source>Hello</source></trans-unit></body></file></xliff>',
        encoding="utf-8",
    )
    source20 = tmp_path / "source2.xlf"
    source20.write_text(
        '<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0" version="2.0"><file><unit id="u1"><segment><source>Hello</source></segment></unit></file></xliff>',
        encoding="utf-8",
    )

    assert resolver.resolve(source12, format="xliff").id == "native.xliff"
    assert resolver.resolve(source20, format="xliff2").id == "native.xliff2"
    assert backend is not None


def test_native_catalog_executes_xliff_1_without_java(tmp_path: Path):
    source = tmp_path / "input.xlf"
    output = tmp_path / "output.xlf"
    source.write_text(
        '<?xml version="1.0"?><xliff xmlns="urn:oasis:names:tc:xliff:document:1.2"><file source-language="en"><body><trans-unit id="1"><source>Hello</source></trans-unit></body></file></xliff>',
        encoding="utf-8",
    )

    registry, backend = build_native_execution()
    service = ExecutionService(
        resolver=__import__("execution.resolver", fromlist=["FilterResolver"]).FilterResolver(registry),
        backends={"native": backend},
        coordinator=JobCoordinator(),
    )
    result = service.execute(
        DocumentRequest(document_id="doc-xlf", input_path=source, format="xliff"),
        output_path=output,
    )

    assert result.status is JobStatus.COMPLETED
    assert result.units_processed == 1
    assert output.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")


def test_native_catalog_executes_xliff_2_without_java(tmp_path: Path):
    source = tmp_path / "input.xlf"
    output = tmp_path / "output.xlf"
    source.write_text(
        '<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0" version="2.0"><file id="f1"><unit id="u1"><segment><source>Hello</source></segment></unit></file></xliff>',
        encoding="utf-8",
    )

    registry, backend = build_native_execution()
    service = ExecutionService(
        resolver=__import__("execution.resolver", fromlist=["FilterResolver"]).FilterResolver(registry),
        backends={"native": backend},
        coordinator=JobCoordinator(),
    )
    result = service.execute(
        DocumentRequest(document_id="doc-xlf2", input_path=source, format="xliff2"),
        output_path=output,
    )

    assert result.status is JobStatus.COMPLETED
    assert result.units_processed == 1
    assert output.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
