"""Conditional graphical instrumental-variable discovery.

Informed by Dagitty's ``jslib/graph/GraphAnalyzer.js`` at commit ``7a657776``.
"""

from __future__ import annotations

from collections.abc import Iterable
from itertools import combinations

from .exceptions import InvalidGraphError, UnsupportedGraphTypeError
from .model import Graph, GraphType, Instrument, Node, NodeSet


def _resolve_single(
    graph: Graph, value: Node | None, status: Iterable[Node], label: str
) -> Node:
    resolved = tuple(status) if value is None else graph._resolve_nodes(value)
    if len(resolved) != 1:
        raise InvalidGraphError(f"exactly one {label} is required")
    return resolved[0]


def instrumental_variables(
    graph: Graph,
    *,
    exposure: Node | None = None,
    outcome: Node | None = None,
) -> list[Instrument]:
    """Discover conditional instruments for a linear total causal effect.

    The graphical criterion establishes exclusion and relevance; use as an IV
    additionally assumes a linear structural model with a homogeneous effect.
    """
    if not isinstance(graph, Graph):
        raise TypeError("graph must be a Graph")
    if graph.type is not GraphType.DAG:
        raise UnsupportedGraphTypeError("instrument discovery is supported only for DAG")
    graph.validate()

    source = _resolve_single(graph, exposure, graph.exposures, "exposure")
    target = _resolve_single(graph, outcome, graph.outcomes, "outcome")
    if source == target:
        raise InvalidGraphError("exposure and outcome must be distinct")
    unavailable = set(graph.latents) | set(graph.selected_nodes) | set(graph.adjusted_nodes)
    if source in unavailable or target in unavailable:
        raise InvalidGraphError("exposure and outcome cannot be latent, adjusted, or selected")

    canonicalization = graph.canonicalize()
    canonical = canonicalization.graph
    backdoor = canonical.backdoor_graph(exposure=source, outcome=target)
    fixed = set(canonical.selected_nodes)

    mediators = (
        set(canonical.descendants(source, proper=True))
        & set(canonical.ancestors(target, proper=True))
    ) - {target}
    forbidden_conditioning = (
        {source, target}
        | set(canonical.latents)
        | set(canonical.descendants(target, proper=True))
        | mediators
    )
    if fixed & forbidden_conditioning:
        return []

    original_nodes = set(graph.nodes)
    candidates = tuple(
        node
        for node in graph.nodes
        if node not in {source, target}
        and node not in unavailable
    )
    results: list[Instrument] = []

    for instrument in candidates:
        ancestral = set(canonical.ancestors((instrument, source, target)))
        eligible = tuple(
            node
            for node in canonical.nodes
            if node in original_nodes
            and node in ancestral
            and node != instrument
            and node not in forbidden_conditioning
            and node not in fixed
            and node not in unavailable
        )
        found: tuple[Node, ...] | None = None
        for size in range(len(eligible) + 1):
            for chosen in combinations(eligible, size):
                given_set = set(chosen) | fixed
                given = tuple(node for node in canonical.nodes if node in given_set)
                if not backdoor.dseparated(instrument, target, given=given):
                    continue
                if not canonical.dconnected(instrument, source, given=given):
                    continue
                found = tuple(node for node in graph.nodes if node in set(chosen) | fixed)
                break
            if found is not None:
                break
        if found is not None:
            results.append(Instrument(instrument, NodeSet(found)))
    return results
