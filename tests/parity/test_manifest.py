"""Execute and audit the pinned parity fixture manifest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from . import builders
from .cases import CASE_BUILDERS, CASES

ROOT = Path(__file__).parent
MANIFEST_PATH = ROOT / "manifest.json"
REQUIRED_FIELDS = {
    "id",
    "source",
    "upstream_commit",
    "graph_type",
    "operation",
    "expectation",
    "risk",
    "builder",
    "expected",
    "notes",
}
PINNED_COMMIT = "7a657776dc8f5e5ba4e323edb028e2c2aaf29327"


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return json.load(source)


loaded_manifest = _load_json(MANIFEST_PATH)
if not isinstance(loaded_manifest, list):
    raise RuntimeError("parity manifest must contain a JSON array")
MANIFEST: list[dict[str, Any]] = []
for index, entry in enumerate(loaded_manifest):
    if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
        raise RuntimeError(f"parity manifest entry {index} has no string id")
    MANIFEST.append(entry)
BY_ID = {entry["id"]: entry for entry in MANIFEST}


def test_manifest_is_complete_and_traceable() -> None:
    assert len(BY_ID) == len(MANIFEST)
    assert set(BY_ID) == set(CASES)
    assert set(BY_ID) == set(CASE_BUILDERS)
    expected_files = set()
    for entry in MANIFEST:
        assert set(entry) == REQUIRED_FIELDS
        assert entry["upstream_commit"] == PINNED_COMMIT
        assert entry["expectation"] in {"parity", "intentional-deviation", "literature"}
        assert entry["risk"] in {"high", "medium", "low"}
        assert isinstance(entry["source"], str) and entry["source"]
        assert isinstance(entry["operation"], str) and entry["operation"]
        assert isinstance(entry["graph_type"], str) and entry["graph_type"]
        assert isinstance(entry["notes"], str) and entry["notes"]
        declared = entry["builder"]
        builder_names = (declared,) if isinstance(declared, str) else tuple(declared)
        assert builder_names == CASE_BUILDERS[entry["id"]]
        assert all(callable(getattr(builders, name, None)) for name in builder_names)
        expected_path = ROOT / entry["expected"]
        assert expected_path.parent == ROOT / "expected"
        assert expected_path.is_file()
        expected_files.add(expected_path.resolve())

    present = {path.resolve() for path in (ROOT / "expected").glob("*.json")}
    assert present == expected_files


@pytest.mark.parametrize("fixture_id", tuple(BY_ID))
def test_parity_fixture(fixture_id: str) -> None:
    entry = BY_ID[fixture_id]
    expected = _load_json(ROOT / entry["expected"])

    assert CASES[fixture_id]() == expected
