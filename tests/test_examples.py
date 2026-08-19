"""Keep the complete analyst examples executable in the normal test suite."""

from __future__ import annotations

import runpy
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).parents[1] / "examples"


@pytest.mark.parametrize(
    "script",
    sorted(EXAMPLES.glob("*.py")),
    ids=lambda path: path.stem,
)
def test_documented_example(script: Path) -> None:
    runpy.run_path(str(script), run_name="__main__")
