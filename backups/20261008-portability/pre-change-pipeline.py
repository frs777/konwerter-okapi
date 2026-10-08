from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json

from importer.extraction.metadata import extract_filter
from importer.ir_generation.generator import filter_ir_from_extracted
from importer.python_generation.generator import PythonFilterGenerator
from importer.validation.report import AdapterReport


@dataclass(frozen=True, slots=True)
class ConversionResult:
    output_dir: Path
    ir: object
    adapter_report: AdapterReport


class OkapiConversionPipeline:
    """Orkiestruje analizę JAR → ekstrakcję → Filter IR → generator Python."""

    def convert(
        self,
        jar: str | Path,
        metadata: str | Path,
        destination: str | Path,
    ) -> ConversionResult:
        jar_path = Path(jar)
        metadata_path = Path(metadata)
        if not jar_path.is_file():
            raise FileNotFoundError(jar_path)
        if not metadata_path.is_file():
            raise FileNotFoundError(metadata_path)

        extracted = extract_filter(jar_path, metadata_path)
        ir = filter_ir_from_extracted(extracted)
        adapter_report = AdapterReport.from_ir(ir)
        output_dir = PythonFilterGenerator().generate(
            ir, destination, adapter_report=adapter_report,
        )
        return ConversionResult(output_dir, ir, adapter_report)

    def convert_catalog(
        self,
        catalog: str | Path,
        destination: str | Path,
    ) -> list[ConversionResult]:
        catalog_path = Path(catalog)
        if not catalog_path.is_dir():
            raise FileNotFoundError(catalog_path)

        results: list[ConversionResult] = []
        for metadata_path in sorted(catalog_path.glob("*/filter.json")):
            filter_name = json.loads(metadata_path.read_text(encoding="utf-8"))["name"]
            candidates = sorted(metadata_path.parent.glob(f"runtime-{filter_name}-*.jar"))
            if not candidates:
                raise FileNotFoundError(
                    f"Nie znaleziono runtime JAR dla filtra {filter_name!r} w {metadata_path.parent}"
                )
            results.append(self.convert(candidates[0], metadata_path, destination))
        return results


def write_conversion_report(result: ConversionResult) -> Path:
    path = result.output_dir / "conversion_report.json"
    payload = {
        "filter": result.ir.name,
        "output_dir": str(result.output_dir),
        "adapter_features": list(result.adapter_report.required_features),
        "status": "generated",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
