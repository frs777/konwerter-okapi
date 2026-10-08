from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


_JAVA_SOURCE = Path(__file__).with_name("JavaFilterProbe.java")


@dataclass(frozen=True, slots=True)
class JavaMethod:
    name: str
    modifiers: str
    return_type: str
    parameter_types: tuple[str, ...]
    signature: str


@dataclass(frozen=True, slots=True)
class JavaEvidence:
    class_name: str
    superclass: str | None
    interfaces: tuple[str, ...]
    methods: tuple[JavaMethod, ...]
    public_methods: tuple[str, ...]
    constructors: tuple[str, ...]
    referenced_classes: tuple[str, ...]
    resolved_dependency_jars: tuple[str, ...]
    classpath_jars: tuple[str, ...]
    missing_classes: tuple[str, ...]
    reflection_complete: bool = True

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "JavaEvidence":
        methods = tuple(
            JavaMethod(
                name=str(item["name"]),
                modifiers=str(item["modifiers"]),
                return_type=str(item["return_type"]),
                parameter_types=tuple(str(value) for value in item["parameter_types"]),
                signature=str(item["signature"]),
            )
            for item in payload["methods"]
        )
        return cls(
            class_name=str(payload["class_name"]),
            superclass=payload.get("superclass") and str(payload["superclass"]),
            interfaces=tuple(str(value) for value in payload["interfaces"]),
            methods=methods,
            public_methods=tuple(str(value) for value in payload["public_methods"]),
            constructors=tuple(str(value) for value in payload["constructors"]),
            referenced_classes=tuple(str(value) for value in payload["referenced_classes"]),
            resolved_dependency_jars=tuple(
                str(value) for value in payload["resolved_dependency_jars"]
            ),
            classpath_jars=tuple(str(value) for value in payload["classpath_jars"]),
            missing_classes=tuple(str(value) for value in payload["missing_classes"]),
            reflection_complete=bool(payload.get("reflection_complete", True)),
        )


class JavaFilterProbe:
    """Uruchamia mały introspektor Java na rzeczywistym JAR-ze filtra."""

    def probe(
        self,
        jar: str | Path,
        class_name: str,
        *,
        classpath: list[str | Path] | tuple[str | Path, ...] = (),
    ) -> JavaEvidence:
        jar_path = Path(jar).resolve()
        if not jar_path.is_file():
            raise FileNotFoundError(jar_path)

        classpath_paths = {jar_path}
        for item in classpath:
            path = Path(item).resolve()
            if path.is_dir():
                classpath_paths.update(path.glob("*.jar"))
            elif path.is_file():
                classpath_paths.add(path)
            else:
                raise FileNotFoundError(path)

        # Filtr JAR zwykle ma komplet zależności obok siebie w testdata.
        classpath_paths.update(jar_path.parent.glob("*.jar"))
        ordered = sorted(classpath_paths, key=lambda path: str(path))
        payload = self._run(jar_path, class_name, ordered)
        return JavaEvidence.from_payload(payload)

    def _run(
        self,
        jar_path: Path,
        class_name: str,
        classpath: list[Path],
    ) -> dict[str, object]:
        if not _JAVA_SOURCE.is_file():
            raise RuntimeError(f"Brak źródła Java probe: {_JAVA_SOURCE}")

        with tempfile.TemporaryDirectory(prefix="okapi-java-probe-") as tmp:
            build_dir = Path(tmp) / "classes"
            build_dir.mkdir()
            compile_result = subprocess.run(
                ["javac", "-d", str(build_dir), str(_JAVA_SOURCE)],
                text=True,
                capture_output=True,
                check=False,
            )
            if compile_result.returncode:
                raise RuntimeError(
                    "Nie udało się skompilować Java probe:\n"
                    + compile_result.stderr
                )

            cp = str(build_dir) + ":" + ":".join(str(path) for path in classpath)
            result = subprocess.run(
                ["java", "-cp", cp, "okapi.probe.JavaFilterProbe", str(jar_path), class_name, *[str(path) for path in classpath]],
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )
            if result.returncode:
                raise RuntimeError(
                    f"Java probe zakończył się kodem {result.returncode}:\n"
                    + result.stderr
                )
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    "Java probe zwrócił niepoprawny JSON:\n" + result.stdout
                ) from exc
