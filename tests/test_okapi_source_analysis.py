from pathlib import Path

ROOT = Path('/home/frs/Projekty/Okapi-main')


def test_okapi_markdown_source_is_available_for_behavioral_analysis():
    source = ROOT / 'okapi/filters/markdown/src/main/java/net/sf/okapi/filters/markdown/MarkdownFilter.java'
    parser = ROOT / 'okapi/filters/markdown/src/main/java/net/sf/okapi/filters/markdown/parser/MarkdownParser.java'
    assert source.exists()
    assert parser.exists()
    text = source.read_text(encoding='utf-8')
    assert 'createSkeletonWriter' in text
    assert 'MarkdownEventBuilder' in text


def test_okapi_markdown_has_official_test_corpus():
    corpus = ROOT / 'okapi/filters/markdown/src/test/resources/net/sf/okapi/filters/markdown'
    files = list(corpus.glob('*.md'))
    assert len(files) >= 20


def test_abstract_filter_contract_is_discovered_as_framework_layer():
    source = ROOT / 'okapi/core/src/main/java/net/sf/okapi/common/filters/AbstractFilter.java'
    assert source.exists()
    text = source.read_text(encoding='utf-8')
    required = [
        'public abstract class AbstractFilter implements IFilter',
        'createStartFilterEvent', 'createEndFilterEvent',
        'setOptions', 'setFilterConfigurationMapper',
        'createFilterWriter', 'createSkeletonWriter',
    ]
    missing = [item for item in required if item not in text]
    assert not missing, f'Brak kontraktu warstwy bazowej: {missing}'


def test_markdown_behavior_exposes_framework_contract():
    from analyzer.metadata.source_extractor import JavaSourceBehaviorExtractor

    source = ROOT / 'okapi/filters/markdown/src/main/java/net/sf/okapi/filters/markdown/MarkdownFilter.java'
    behavior = JavaSourceBehaviorExtractor().extract_markdown_filter(source)
    assert behavior.superclass == 'AbstractFilter'
    assert 'open' in behavior.lifecycle_methods
    assert 'next' in behavior.lifecycle_methods
    assert 'close' in behavior.lifecycle_methods
    assert behavior.framework_contract == 'net.sf.okapi.common.filters.AbstractFilter'


def test_markdown_parameter_inventory_excludes_inline_finder_runtime_fields():
    from analyzer.metadata.source_extractor import JavaSourceBehaviorExtractor
    s=ROOT / 'okapi/filters/markdown/src/main/java/net/sf/okapi/filters/markdown/MarkdownFilter.java'
    b=JavaSourceBehaviorExtractor().extract_markdown_filter(s)
    names={r.name for r in b.parameter_rules}
    assert 'sample' not in names and 'useAllRulesWhenTesting' not in names
    assert 'translateCodeBlocks' in names and 'nonTranslateBlocks' in names
