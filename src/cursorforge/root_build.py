from __future__ import annotations

import argparse
import json
import sys
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from cursorforge.builder import BuildResult, ThemeBuilder
from cursorforge.models import CursorTheme, ThemeSource

PROGRESS_PREFIX = "PROGRESS"
RESULT_PREFIX = "RESULT"


def build_privileged_command(
    python_executable: str,
    cursor_path: Path,
    source_name: str,
    output_path: Path,
    new_sizes: list[int],
    pythonpath: str | None = None,
) -> list[str]:
    cmd = [
        python_executable,
        "-m",
        "cursorforge.root_build",
        "--cursor-path",
        str(cursor_path),
        "--source-name",
        source_name,
        "--output-path",
        str(output_path),
    ]
    for size in new_sizes:
        cmd.extend(["--new-size", str(size)])
    if pythonpath:
        return ["pkexec", "env", f"PYTHONPATH={pythonpath}", *cmd]
    return ["pkexec", *cmd]


def serialize_result(result: BuildResult) -> dict[str, Any]:
    return {
        "success": result.success,
        "output_path": str(result.output_path),
        "sizes_added": list(result.sizes_added),
        "cursors_processed": result.cursors_processed,
        "cursors_failed": result.cursors_failed,
        "errors": list(result.errors),
    }


def deserialize_result(payload: dict[str, Any]) -> BuildResult:
    return BuildResult(
        success=bool(payload.get("success", False)),
        output_path=Path(str(payload.get("output_path", ""))),
        sizes_added=[int(size) for size in payload.get("sizes_added", [])],
        cursors_processed=int(payload.get("cursors_processed", 0)),
        cursors_failed=int(payload.get("cursors_failed", 0)),
        errors=[str(err) for err in payload.get("errors", [])],
    )


def format_progress(message: str, current: int, total: int) -> str:
    return f"{PROGRESS_PREFIX}\t{current}\t{total}\t{message}"


def format_result(result: BuildResult) -> str:
    return f"{RESULT_PREFIX}\t{json.dumps(serialize_result(result), ensure_ascii=False)}"


def parse_output_line(line: str) -> tuple[str, object] | None:
    if not line:
        return None
    if line.startswith(f"{PROGRESS_PREFIX}\t"):
        parts = line.split("\t", 3)
        if len(parts) != 4:
            return None
        try:
            current = int(parts[1])
            total = int(parts[2])
        except ValueError:
            return None
        return "progress", (parts[3], current, total)
    if line.startswith(f"{RESULT_PREFIX}\t"):
        try:
            payload = json.loads(line.split("\t", 1)[1])
        except JSONDecodeError:
            return None
        return "result", deserialize_result(payload)
    return None


def _build_theme(cursor_path: Path, source_name: str, output_path: Path, new_sizes: list[int]) -> BuildResult:
    theme = CursorTheme(
        name=source_name,
        directory_name=source_name,
        path=cursor_path.parent,
        cursor_path=cursor_path,
        source_type=ThemeSource.SYSTEM,
        existing_sizes=(),
        inspected_files=0,
        failed_inspections=0,
    )

    builder = ThemeBuilder()

    def on_progress(message: str, current: int, total: int) -> None:
        print(format_progress(message, current, total), flush=True)

    result = builder.build(theme, new_sizes, output_path, on_progress=on_progress)
    print(format_result(result), flush=True)
    return result


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a CursorForge build as root.")
    parser.add_argument("--cursor-path", type=Path, required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    parser.add_argument("--new-size", type=int, action="append", dest="new_sizes", required=True)
    args = parser.parse_args(argv)

    try:
        result = _build_theme(args.cursor_path, args.source_name, args.output_path, args.new_sizes)
    except Exception as exc:  # pragma: no cover - defensive guard for privileged helper
        failure = BuildResult(success=False, output_path=args.output_path, errors=[str(exc)])
        print(format_result(failure), flush=True)
        return 1

    return 0 if result.success else 1


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
