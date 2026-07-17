from __future__ import annotations

from pathlib import Path

from cursorforge.builder import BuildResult
from cursorforge.root_build import (
    build_privileged_command,
    deserialize_result,
    format_progress,
    format_result,
    parse_output_line,
    serialize_result,
)


def test_build_privileged_command_includes_pkexec_and_arguments(tmp_path: Path) -> None:
    command = build_privileged_command(
        "/usr/bin/python3",
        tmp_path / "theme" / "cursors",
        "MyTheme",
        tmp_path / "out",
        [16, 32],
    )

    assert command[:3] == ["pkexec", "/usr/bin/python3", "-m"]
    assert "cursorforge.root_build" in command
    assert "--cursor-path" in command
    assert "--source-name" in command
    assert "--output-path" in command
    assert command.count("--new-size") == 2


def test_progress_line_round_trips() -> None:
    line = format_progress("Working…", 3, 10)
    kind, payload = parse_output_line(line)

    assert kind == "progress"
    assert payload == ("Working…", 3, 10)


def test_result_line_round_trips(tmp_path: Path) -> None:
    result = BuildResult(
        success=True,
        output_path=tmp_path / "out",
        sizes_added=[16, 32],
        cursors_processed=4,
        cursors_failed=0,
        errors=[],
    )

    line = format_result(result)
    kind, payload = parse_output_line(line)

    assert kind == "result"
    assert payload == result


def test_result_serialization_is_json_safe(tmp_path: Path) -> None:
    result = BuildResult(
        success=False,
        output_path=tmp_path / "out",
        sizes_added=[24],
        cursors_processed=1,
        cursors_failed=1,
        errors=["boom"],
    )

    payload = serialize_result(result)
    rebuilt = deserialize_result(payload)

    assert rebuilt == result
