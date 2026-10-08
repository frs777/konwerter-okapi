import json
from pathlib import Path

from importer.pipeline import OkapiConversionPipeline


def test_catalog_conversion_records_java_runtime_evidence(tmp_path):
    results = OkapiConversionPipeline().convert_catalog(
        Path("testdata/okapi-filters-java"),
        tmp_path,
        source_root=Path("/home/frs/Projekty/Okapi-main"),
    )

    assert len(results) == 9
    openxml = next(item for item in results if item.ir.name == "openxml")
    report = json.loads(
        (openxml.output_dir / "conversion_report.json").read_text(encoding="utf-8")
    )

    assert report["java_evidence"]["class_name"] == (
        "net.sf.okapi.filters.openxml.OpenXMLFilter"
    )
    assert "net.sf.okapi.common.filters.IFilter" in report["java_evidence"]["interfaces"]
    assert report["java_evidence"]["classpath_jars"]
    assert "net.sf.okapi.common.filters.IFilter" not in report["java_evidence"]["missing_classes"]
    assert report["java_evidence"]["resolved_dependency_jars"]
