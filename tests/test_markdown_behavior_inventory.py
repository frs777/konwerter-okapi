from pathlib import Path

ROOT = Path('/home/frs/Projekty/Okapi-main/okapi/filters/markdown/src/main/java/net/sf/okapi/filters/markdown')


def test_markdown_behavior_inventory_covers_parser_skeleton_writer_and_subfilters():
    source = (ROOT / 'MarkdownFilter.java').read_text(encoding='utf-8')
    required = [
        'MarkdownParser', 'MarkdownEventBuilder', 'MarkdownSkeletonWriter',
        'HtmlFilter', 'YamlFilter', 'processByHtmlFilter', 'processByYamlFilter',
        'getTranslateUrls', 'getUseCodeFinder', 'generateSkeleton',
        'FENCED_CODE_BLOCK', 'YAML_METADATA_HEADER', 'HTML_INLINE',
    ]
    missing = [item for item in required if item not in source]
    assert not missing, f'Brak zachowania w inwentarzu: {missing}'
