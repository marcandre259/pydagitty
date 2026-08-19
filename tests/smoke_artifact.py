"""Exercise an installed wheel or source distribution without pytest."""

from __future__ import annotations

import argparse
from importlib.metadata import version as distribution_version
from pathlib import Path

import pydagitty
from pydagitty import DAG, nodes
from pydagitty._version import version as module_version


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--render", action="store_true")
    arguments = parser.parse_args()

    installed_version = distribution_version("pydagitty")
    assert installed_version == arguments.expected_version
    assert module_version == installed_version

    repository = Path.cwd().resolve()
    module_path = Path(pydagitty.__file__).resolve()
    assert repository not in module_path.parents, (
        f"imported checkout instead of artifact: {module_path}"
    )

    exposure, outcome, confounder = nodes("X Y Z")
    graph = DAG(paths=[confounder >> exposure, confounder >> outcome, exposure >> outcome])
    graph.exposures = exposure
    graph.outcomes = outcome

    separation_graph = DAG(paths=[confounder >> exposure, confounder >> outcome])
    assert separation_graph.dseparated(exposure, outcome) is False
    assert separation_graph.dseparated(exposure, outcome, given=confounder) is True
    assert graph.dseparated(exposure, outcome, given=confounder) is False
    assert tuple(graph.adjustment_sets().items[0]) == (confounder,)

    dot = graph.to_graphviz()
    assert "digraph" in dot.source
    assert "X" in dot.source and "Y" in dot.source and "Z" in dot.source
    if arguments.render:
        assert b"<svg" in dot.pipe(format="svg")

    print(f"Smoke-tested pydagitty {installed_version} from {module_path}")


if __name__ == "__main__":
    main()
