from pathlib import Path


def test_cli_inspects_jar_as_json(capsys):
    from tools.okapi_inspect import main
    code = main(['testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar'])
    assert code == 0
    assert 'MarkdownFilter' in capsys.readouterr().out


def test_cli_is_executable_from_repository_root():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, 'tools/okapi_inspect.py', 'testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar'],
        capture_output=True,
        text=True,
        cwd='.',
    )
    assert result.returncode == 0, result.stderr
    assert 'MarkdownFilter' in result.stdout
