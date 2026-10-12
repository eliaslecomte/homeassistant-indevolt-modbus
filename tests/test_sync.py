"""Keep release metadata intact when refreshing generated integration files."""

import importlib.util
import json
from pathlib import Path

import pytest


@pytest.mark.parametrize("existing_version", [None, "0.1.1"])
def test_sync_preserves_manifest_version(tmp_path, monkeypatch, existing_version):
    spec = importlib.util.spec_from_file_location(
        "indevolt_sync", Path(__file__).resolve().parents[1] / "scripts/sync.py"
    )
    sync = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sync)
    core = tmp_path / "core"
    library = tmp_path / "library"
    target = tmp_path / "target"
    for path in (core, target, library / "src/indevolt_modbus"):
        path.mkdir(parents=True)
    (core / "manifest.json").write_text(json.dumps({"domain": "indevolt"}))
    (core / "strings.json").write_text("{}")
    (library / "LICENSE").write_text("Test library license")
    previous = {
        "documentation": "https://example.com/docs",
        "issue_tracker": "https://example.com/issues",
        "codeowners": ["@example"],
    }
    if existing_version is not None:
        previous["version"] = existing_version
    (target / "manifest.json").write_text(json.dumps(previous))
    monkeypatch.setattr(sync, "CORE", core)
    monkeypatch.setattr(sync, "LIBRARY", library)
    monkeypatch.setattr(sync, "TARGET", target)
    sync.main()
    result = json.loads((target / "manifest.json").read_text())
    assert result["version"] == (existing_version or "0.1.0")
    assert result["domain"] == "indevolt_modbus"
    assert result["requirements"] == ["modbus-connection[tmodbus]>=4.12.4"]
    for key in ("documentation", "issue_tracker", "codeowners"):
        assert result[key] == previous[key]
