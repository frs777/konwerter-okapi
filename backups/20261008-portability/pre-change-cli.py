from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from importer.pipeline import OkapiConversionPipeline


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Automatycznie analizuje filtr Okapi i generuje pakiet Pythonowy."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("jar", nargs="?", type=Path, help="plik JAR filtra Okapi")
    source.add_argument("--catalog", type=Path, help="katalog zawierający podkatalogi filtrów z filter.json")
    parser.add_argument("--metadata", type=Path, help="plik filter.json dla pojedynczego JAR-a")
    parser.add_argument("--output", required=True, type=Path, help="katalog wyjściowy")
    args = parser.parse_args()

    pipeline = OkapiConversionPipeline()
    if args.catalog is not None:
        if args.metadata is not None:
            parser.error("--metadata nie może być użyte razem z --catalog")
        results = pipeline.convert_catalog(args.catalog, args.output)
        payload = [
            {
                "filter": result.ir.name,
                "output_dir": str(result.output_dir),
                "adapter_features": list(result.adapter_report.required_features),
                "status": "generated",
            }
            for result in results
        ]
    else:
        if args.metadata is None:
            parser.error("--metadata jest wymagane przy konwersji pojedynczego JAR-a")
        result = pipeline.convert(args.jar, args.metadata, args.output)
        payload = {
            "filter": result.ir.name,
            "output_dir": str(result.output_dir),
            "adapter_features": list(result.adapter_report.required_features),
            "status": "generated",
        }

    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
