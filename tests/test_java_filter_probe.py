from pathlib import Path

import pytest

from analyzer.java_probe.probe import JavaFilterProbe


OPENXML_JAR = Path(
    "testdata/okapi-filters-java/openxml/runtime-openxml-1.49.0-SNAPSHOT.jar"
)


def test_java_probe_reports_runtime_class_contract():
    result = JavaFilterProbe().probe(
        OPENXML_JAR,
        "net.sf.okapi.filters.openxml.OpenXMLFilter",
        classpath=[OPENXML_JAR, Path('/home/frs/Projekty/Okapi-main/okapi/core/target/okapi-core-1.49.0-SNAPSHOT.jar')],
    )

    assert result.class_name == "net.sf.okapi.filters.openxml.OpenXMLFilter"
    assert "net.sf.okapi.common.filters.IFilter" in result.interfaces
    assert result.superclass == "java.lang.Object"
    assert "getName" in result.public_methods
    assert "open" in result.public_methods
    assert "next" in result.public_methods


def test_java_probe_reports_classpath_dependencies():
    result = JavaFilterProbe().probe(
        OPENXML_JAR,
        "net.sf.okapi.filters.openxml.OpenXMLFilter",
        classpath=[OPENXML_JAR, Path('/home/frs/Projekty/Okapi-main/okapi/core/target/okapi-core-1.49.0-SNAPSHOT.jar')],
    )

    assert "net.sf.okapi.common.filters.IFilter" in result.referenced_classes
    assert any(dep.endswith("runtime-openxml-1.49.0-SNAPSHOT.jar") for dep in result.classpath_jars)
    assert result.missing_classes
