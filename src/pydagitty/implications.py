"""Generation of graphical conditional-independence implications.

Informed by Dagitty's ``jslib/graph/GraphAnalyzer.js`` at commit ``7a657776``.
"""

from __future__ import annotations

from collections.abc import Iterator
from itertools import combinations

from .exceptions import UnsupportedGraphTypeError
from .model import (
    ConditionalIndependence,
    Endpoint,
    EnumerationResult,
    Graph,
    GraphType,
    Node,
)
from .traversal import minimal_separators

_SUPPORTED_TYPES = {GraphType.DAG, GraphType.MAG, GraphType.PDAG}


def _limit(value: int | None) -> int | None:
    if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
        raise TypeError("max_results must be a non-negative integer or None")
    if value is not None and value < 0:
        raise ValueError("max_results must be non-negative")
    return value


def _bounded(
    items: Iterator[ConditionalIndependence], maximum: int | None
) -> EnumerationResult[ConditionalIndependence]:
    if maximum == 0:
        return EnumerationResult((), truncated=False)
    result: list[ConditionalIndependence] = []
    for item in items:
        if maximum is not None and len(result) == maximum:
            return EnumerationResult(result, truncated=True)
        result.append(item)
    return EnumerationResult(result, truncated=False)


def _conditioning_subsets(nodes: tuple[Node, ...]) -> Iterator[tuple[Node, ...]]:
    for size in range(len(nodes) + 1):
        yield from combinations(nodes, size)


def _pairs(nodes: tuple[Node, ...]) -> Iterator[tuple[Node, Node]]:
    yield from combinations(nodes, 2)


def _all_pairs(graph: Graph, observed: tuple[Node, ...]) -> Iterator[ConditionalIndependence]:
    selected = tuple(graph.selected_nodes)
    selected_set = set(selected)
    for first, second in _pairs(observed):
        candidates = tuple(
            node
            for node in observed
            if node != first and node != second and node not in selected_set
        )
        for chosen in _conditioning_subsets(candidates):
            given_set = set(chosen) | selected_set
            given = tuple(node for node in graph.nodes if node in given_set)
            if graph.dseparated(first, second, given=given):
                yield ConditionalIndependence(first, second, given)


def _missing_edges(
    graph: Graph, observed: tuple[Node, ...], limit: int | None
) -> Iterator[ConditionalIndependence]:
    selected = tuple(graph.selected_nodes)
    selected_set = set(selected)
    emitted = 0
    for first, second in _pairs(observed):
        if limit is not None and emitted >= limit:
            return
        if graph.adjacent(first, second):
            continue
        if graph.type is GraphType.PDAG:
            candidates = tuple(
                node
                for node in observed
                if node != first and node != second and node not in selected_set
            )
            accepted: list[frozenset[Node]] = []
            for chosen in _conditioning_subsets(candidates):
                chosen_set = frozenset(chosen)
                if any(separator < chosen_set for separator in accepted):
                    continue
                given_set = set(chosen) | selected_set
                given = tuple(node for node in graph.nodes if node in given_set)
                if graph.dseparated(first, second, given=given):
                    accepted.append(chosen_set)
                    yield ConditionalIndependence(first, second, given)
                    emitted += 1
                    if limit is not None and emitted >= limit:
                        return
            continue
        relevant = graph.ancestor_graph((first, second) + selected)
        moral = relevant.moralize()
        separators = minimal_separators(
            moral,
            first,
            second,
            mandatory=tuple(node for node in moral.nodes if node in selected_set),
            forbidden=tuple(node for node in moral.nodes if node in graph.latents),
            max_results=None,
        )
        for separator in separators:
            given_set = set(separator) | selected_set
            given = tuple(node for node in graph.nodes if node in given_set)
            if graph.dseparated(first, second, given=given):
                yield ConditionalIndependence(first, second, given)
                emitted += 1
                if limit is not None and emitted >= limit:
                    return


def _is_bidirected_or_undirected(graph: Graph, first: Node, second: Node) -> bool:
    for edge in graph.edges_between(first, second):
        first_mark = edge.endpoint_at(first)
        second_mark = edge.endpoint_at(second)
        if first_mark is second_mark and first_mark in {Endpoint.ARROW, Endpoint.TAIL}:
            return True
    return False


def _ordered_basis(graph: Graph, observed: tuple[Node, ...]) -> Iterator[ConditionalIndependence]:
    if graph.selected_nodes:
        raise ValueError("basis_set does not support selected nodes")

    if graph.type is GraphType.DAG:
        ordering = graph.topological_ordering()
    else:
        # Topologically order only strict directed edges; mixed incidences do
        # not contribute to directed indegree.
        indegree = {node: len(graph.parents(node)) for node in graph.nodes}
        remaining = set(graph.nodes)
        ordered: list[Node] = []
        while remaining:
            next_node = next(
                (node for node in graph.nodes if node in remaining and indegree[node] == 0),
                None,
            )
            if next_node is None:
                raise ValueError("basis_set requires acyclic strict directed edges")
            remaining.remove(next_node)
            ordered.append(next_node)
            for child in graph.children(next_node):
                indegree[child] -= 1
        ordering = tuple(ordered)
    observed_set = set(observed)

    for index, node in enumerate(ordering):
        if node not in observed_set:
            continue
        prefix = set(ordering[: index + 1])
        district = {node}
        queue = [node]
        while queue:
            current = queue.pop()
            for other in graph.adjacent_nodes(current):
                if (
                    other in prefix
                    and other not in district
                    and _is_bidirected_or_undirected(graph, current, other)
                ):
                    district.add(other)
                    queue.append(other)

        blanket = district - {node}
        for member in district:
            blanket.update(parent for parent in graph.parents(member) if parent in prefix)
        blanket.discard(node)
        given = tuple(item for item in graph.nodes if item in blanket and item in observed_set)
        right = tuple(
            item
            for item in ordering[:index]
            if item in observed_set and item not in blanket
        )
        # Removing latent blanket members may invalidate an observed statement.
        right = tuple(
            item for item in right if graph.dseparated(node, item, given=given)
        )
        if right and graph.dseparated(node, right, given=given):
            yield ConditionalIndependence(node, right, given)


def implied_conditional_independencies(
    graph: Graph,
    *,
    mode: str = "missing_edge",
    max_results: int | None = None,
) -> EnumerationResult[ConditionalIndependence]:
    """Return observed-variable conditional independencies implied by ``graph``."""
    if not isinstance(graph, Graph):
        raise TypeError("graph must be a Graph")
    maximum = _limit(max_results)
    if mode not in {"missing_edge", "basis_set", "all_pairs"}:
        raise ValueError("mode must be 'missing_edge', 'basis_set', or 'all_pairs'")
    if graph.type not in _SUPPORTED_TYPES:
        raise UnsupportedGraphTypeError(
            "implied independencies support DAG, MAG, and PDAG"
        )
    graph.validate()
    if mode == "basis_set" and graph.selected_nodes:
        raise ValueError("basis_set does not support selected nodes")

    hidden = set(graph.latents) | set(graph.selected_nodes)
    observed = tuple(node for node in graph.nodes if node not in hidden)
    if mode == "missing_edge":
        search_limit = None if maximum is None else maximum + 1
        items = _missing_edges(graph, observed, search_limit)
    elif mode == "all_pairs":
        items = _all_pairs(graph, observed)
    else:
        items = _ordered_basis(graph, observed)
    return _bounded(items, maximum)
