from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analyzer.jar_inspector.inspector import JarInspector

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Inspekcja JAR filtra Okapi bez uruchamiania kodu.')
    parser.add_argument('jar')
    args = parser.parse_args(argv)
    result = JarInspector().inspect(Path(args.jar))
    print(json.dumps({'path': str(result.path), 'manifest': result.manifest, 'classes': result.classes}, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
