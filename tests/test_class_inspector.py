from pathlib import Path

JAR = Path('testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar')


def test_class_inspector_reads_class_header_and_constant_pool():
    from analyzer.class_inspector.inspector import ClassInspector
    result = ClassInspector().inspect_jar_class(JAR, 'net.sf.okapi.filters.markdown.MarkdownFilter')
    assert result.class_name == 'net.sf.okapi.filters.markdown.MarkdownFilter'
    assert result.super_name
    assert 'net/sf/okapi/filters/markdown/MarkdownFilter' in result.this_class
    assert result.constant_pool_count > 0


def test_class_inspector_exposes_methods():
    from analyzer.class_inspector.inspector import ClassInspector
    result = ClassInspector().inspect_jar_class(JAR, "net.sf.okapi.filters.markdown.MarkdownFilter")
    assert result.methods
