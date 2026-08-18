"""Deterministic-order graph generators.

Informed by Dagitty's ``jslib/graph/GraphGenerator.js`` at commit ``7a657776``.
"""

from __future__ import annotations

import random
from collections.abc import Iterable

from .model import DAG, Edge, Endpoint, Node


def _generator_nodes(value: int | Iterable[Node]) -> tuple[Node, ...]:
    if isinstance(value, bool):
        raise TypeError("node count must be an integer, not bool")
    if isinstance(value, int):
        if value < 0:
            raise ValueError("node count must be non-negative")
        return tuple(Node(f"x{index}") for index in range(1, value + 1))
    if isinstance(value, str):
        raise TypeError("bare strings are not node collections")
    result = tuple(value)
    if any(not isinstance(node, Node) for node in result):
        raise TypeError("generator nodes must be Node objects")
    if len({node.identifier for node in result}) != len(result):
        raise ValueError("generator node identifiers must be unique")
    return result


def complete_dag(nodes: int | Iterable[Node]) -> DAG:
    """Create the complete DAG for the supplied fixed topological order."""
    ordered = _generator_nodes(nodes)
    edges = (
        Edge(ordered[first], ordered[second], Endpoint.TAIL, Endpoint.ARROW)
        for first in range(len(ordered))
        for second in range(first + 1, len(ordered))
    )
    return DAG(nodes=ordered, edges=edges)


def random_dag(
    nodes: int | Iterable[Node],
    p: float = 0.5,
    *,
    rng: random.Random,
) -> DAG:
    """Create a DAG by independently sampling edges in lexical position order."""
    if isinstance(p, bool) or not isinstance(p, (int, float)):
        raise TypeError("p must be a real number")
    probability = float(p)
    if not 0.0 <= probability <= 1.0:
        raise ValueError("p must be between zero and one")
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")

    ordered = _generator_nodes(nodes)
    edges: list[Edge] = []
    for first in range(len(ordered)):
        for second in range(first + 1, len(ordered)):
            if rng.random() < probability:
                edges.append(
                    Edge(ordered[first], ordered[second], Endpoint.TAIL, Endpoint.ARROW)
                )
    return DAG(nodes=ordered, edges=edges)
