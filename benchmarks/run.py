#!/usr/bin/env python3
"""Run reproducible, dependency-free PyDagitty benchmarks and emit JSON."""

from __future__ import annotations

import argparse
import json
import platform
import random
from collections.abc import Callable
from time import perf_counter
from typing import Any

from pydagitty import (
    DAG,
    GRAPH,
    Edge,
    Endpoint,
    Graph,
    Node,
    complete_dag,
    minimal_separators,
    random_dag,
)

SEED = 2026
DEFAULT_MAX_RESULTS = 100


def _positive_int(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if result < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return result


def _result_limit(value: str) -> int | None:
    if value.lower() == "none":
        return None
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a non-negative integer or 'none'") from exc
    if result < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer or 'none'")
    return result


def _measure(operation: Callable[[], Any]) -> tuple[Any, float]:
    started = perf_counter()
    result = operation()
    return result, perf_counter() - started


def _record(
    name: str,
    graph: Graph,
    *,
    arguments: dict[str, Any],
    elapsed: float,
    result_count: int,
    result_kind: str,
    truncated: bool | None,
    dimensions: dict[str, int] | None = None,
) -> dict[str, Any]:
    graph_dimensions = {"nodes": len(graph.nodes), "edges": len(graph.edges)}
    if dimensions is not None:
        graph_dimensions.update(dimensions)
    return {
        "name": name,
        "dimensions": graph_dimensions,
        "arguments": arguments,
        "elapsed_seconds": elapsed,
        "result_count": result_count,
        "result_kind": result_kind,
        "truncated": truncated,
    }


def _sparse_separation(scale: int, max_results: int | None) -> list[dict[str, Any]]:
    del max_results
    node_count = 100 * scale
    probability = min(6 / max(node_count - 1, 1), 1.0)
    graph = random_dag(node_count, probability, rng=random.Random(SEED))
    query_count = 25 * scale
    conditioned_count = min(3 * scale, node_count - 2)
    query_rng = random.Random(SEED + 1)
    queries: list[tuple[Node, Node, tuple[Node, ...]]] = []
    for _ in range(query_count):
        selected = query_rng.sample(graph.nodes, 2 + conditioned_count)
        queries.append((selected[0], selected[1], tuple(selected[2:])))

    separated, elapsed = _measure(
        lambda: sum(graph.dseparated(first, second, given) for first, second, given in queries)
    )
    return [
        _record(
            "sparse_separation",
            graph,
            dimensions={"queries": query_count},
            arguments={
                "conditioned_nodes_per_query": conditioned_count,
                "edge_probability": probability,
                "seed": SEED,
            },
            elapsed=elapsed,
            result_count=separated,
            result_kind="separated_queries",
            truncated=None,
        )
    ]


def _layered_dag(layer_count: int) -> tuple[DAG, Node, Node]:
    source = Node("source")
    target = Node("target")
    layers = tuple(
        (Node(f"layer_{index}_a"), Node(f"layer_{index}_b"))
        for index in range(layer_count)
    )
    graph_nodes = (source,) + tuple(node for layer in layers for node in layer) + (target,)
    edges = [Edge(source, node) for node in layers[0]]
    for left, right in zip(layers, layers[1:]):
        edges.extend(Edge(parent, child) for parent in left for child in right)
    edges.extend(Edge(node, target) for node in layers[-1])
    return DAG(nodes=graph_nodes, edges=edges), source, target


def _paths(scale: int, max_results: int | None) -> list[dict[str, Any]]:
    layer_count = 6 + scale
    graph, source, target = _layered_dag(layer_count)
    result, elapsed = _measure(
        lambda: graph.paths(source, target, directed=True, max_results=max_results)
    )
    return [
        _record(
            "paths",
            graph,
            dimensions={"layers": layer_count},
            arguments={"directed": True, "max_results": max_results, "open_only": False},
            elapsed=elapsed,
            result_count=len(result),
            result_kind="paths",
            truncated=result.truncated,
        )
    ]


def _parallel_path_graph(width: int) -> tuple[GRAPH, Node, Node]:
    source = Node("source")
    target = Node("target")
    internal = tuple(
        (Node(f"path_{index}_a"), Node(f"path_{index}_b")) for index in range(width)
    )
    graph_nodes = (source,) + tuple(node for pair in internal for node in pair) + (target,)
    edges: list[Edge] = []
    for first, second in internal:
        edges.extend(
            (
                Edge(source, first, Endpoint.TAIL, Endpoint.TAIL),
                Edge(first, second, Endpoint.TAIL, Endpoint.TAIL),
                Edge(second, target, Endpoint.TAIL, Endpoint.TAIL),
            )
        )
    return GRAPH(nodes=graph_nodes, edges=edges), source, target


def _minimal_separators(scale: int, max_results: int | None) -> list[dict[str, Any]]:
    width = 6 + scale
    graph, source, target = _parallel_path_graph(width)
    result, elapsed = _measure(
        lambda: minimal_separators(graph, source, target, max_results=max_results)
    )
    return [
        _record(
            "minimal_separators",
            graph,
            dimensions={"parallel_paths": width},
            arguments={"max_results": max_results},
            elapsed=elapsed,
            result_count=len(result),
            result_kind="minimal_separators",
            truncated=result.truncated,
        )
    ]


def _adjustment_graph(width: int) -> DAG:
    exposure = Node("X")
    outcome = Node("Y")
    pairs = tuple((Node(f"A{index}"), Node(f"B{index}")) for index in range(width))
    graph_nodes = (exposure, outcome) + tuple(node for pair in pairs for node in pair)
    edges = [Edge(exposure, outcome)]
    for first, second in pairs:
        edges.extend((Edge(first, exposure), Edge(first, second), Edge(second, outcome)))
    graph = DAG(nodes=graph_nodes, edges=edges)
    graph.exposures = exposure
    graph.outcomes = outcome
    return graph


def _adjustment(scale: int, max_results: int | None) -> list[dict[str, Any]]:
    width = 4 + scale
    graph = _adjustment_graph(width)
    records = []
    for mode in ("minimal", "all"):
        result, elapsed = _measure(
            lambda: graph.adjustment_sets(mode=mode, max_results=max_results)
        )
        records.append(
            _record(
                f"adjustment_{mode}",
                graph,
                dimensions={"confounding_paths": width, "candidate_nodes": 2 * width},
                arguments={"effect": "total", "max_results": max_results, "mode": mode},
                elapsed=elapsed,
                result_count=len(result),
                result_kind="adjustment_sets",
                truncated=result.truncated,
            )
        )
    return records


def _equivalent_dags(scale: int, max_results: int | None) -> list[dict[str, Any]]:
    node_count = 4 + scale
    graph = complete_dag(node_count)
    result, elapsed = _measure(lambda: graph.equivalent_dags(max_results=max_results))
    return [
        _record(
            "equivalent_dags",
            graph,
            dimensions={"reversible_edges": len(graph.edges)},
            arguments={"max_results": max_results},
            elapsed=elapsed,
            result_count=len(result),
            result_kind="dags",
            truncated=result.truncated,
        )
    ]


def _instrument_graph(confounder_count: int) -> DAG:
    instrument = Node("Z")
    exposure = Node("X")
    outcome = Node("Y")
    confounders = tuple(Node(f"U{index}") for index in range(confounder_count))
    graph = DAG(nodes=(instrument, exposure, outcome) + confounders)
    graph.add_edge(Edge(instrument, exposure))
    graph.add_edge(Edge(exposure, outcome))
    for confounder in confounders:
        graph.add_edge(Edge(confounder, instrument))
        graph.add_edge(Edge(confounder, outcome))
    graph.exposures = exposure
    graph.outcomes = outcome
    return graph


def _instruments(scale: int, max_results: int | None) -> list[dict[str, Any]]:
    del max_results
    confounder_count = 4 + scale
    graph = _instrument_graph(confounder_count)
    result, elapsed = _measure(graph.instrumental_variables)
    return [
        _record(
            "instruments",
            graph,
            dimensions={
                "candidate_nodes": len(graph.nodes) - 2,
                "conditioning_candidates": confounder_count,
            },
            arguments={"max_results": None},
            elapsed=elapsed,
            result_count=len(result),
            result_kind="instruments",
            truncated=None,
        )
    ]


def _tetrad_graph(observed_count: int) -> DAG:
    latent = Node("L")
    observed = tuple(Node(f"O{index}") for index in range(observed_count))
    graph = DAG(nodes=(latent,) + observed, edges=(Edge(latent, node) for node in observed))
    graph.latents = latent
    return graph


def _tetrads(scale: int, max_results: int | None) -> list[dict[str, Any]]:
    observed_count = 6 + 2 * scale
    graph = _tetrad_graph(observed_count)
    result, elapsed = _measure(
        lambda: graph.vanishing_tetrads(kind="all", max_results=max_results)
    )
    return [
        _record(
            "tetrads",
            graph,
            dimensions={"observed_nodes": observed_count},
            arguments={"kind": "all", "max_results": max_results},
            elapsed=elapsed,
            result_count=len(result),
            result_kind="tetrads",
            truncated=result.truncated,
        )
    ]


SCENARIOS: dict[str, Callable[[int, int | None], list[dict[str, Any]]]] = {
    "sparse-separation": _sparse_separation,
    "paths": _paths,
    "minimal-separators": _minimal_separators,
    "adjustment": _adjustment,
    "equivalent-dags": _equivalent_dags,
    "instruments": _instruments,
    "tetrads": _tetrads,
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run reproducible PyDagitty benchmarks and emit one JSON document."
    )
    parser.add_argument(
        "--scenario",
        action="append",
        choices=("all", *SCENARIOS),
        help="scenario to run; repeat this option to select multiple (default: all)",
    )
    parser.add_argument(
        "--scale",
        type=_positive_int,
        default=1,
        help="positive fixture scale (default: 1)",
    )
    parser.add_argument(
        "--max-results",
        type=_result_limit,
        default=DEFAULT_MAX_RESULTS,
        metavar="N|none",
        help="enumeration result limit; use 'none' only for small fixtures (default: 100)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    requested = args.scenario or ["all"]
    selected = list(SCENARIOS) if "all" in requested else list(dict.fromkeys(requested))
    records = []
    for name in selected:
        records.extend(SCENARIOS[name](args.scale, args.max_results))

    document = {
        "schema_version": 1,
        "environment": {
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "configuration": {
            "scenarios": selected,
            "scale": args.scale,
            "max_results": args.max_results,
            "seed": SEED,
        },
        "benchmarks": records,
    }
    print(json.dumps(document, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
