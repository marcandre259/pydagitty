"""Dependency-free graphical constraints for linear structural equation models.

Informed by Dagitty's ``jslib/graph/GraphAnalyzer.js`` at commit ``7a657776``.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import combinations

from .exceptions import UnsupportedGraphTypeError
from .model import Edge, Endpoint, EnumerationResult, Graph, GraphType, Node


@dataclass(frozen=True, slots=True)
class Tetrad:
    """A constraint ``cov(i,j) cov(k,l) - cov(i,k) cov(j,l) = 0``."""

    i: Node
    j: Node
    k: Node
    l: Node  # noqa: E741 - conventional fourth tetrad index

    def __post_init__(self) -> None:
        values = (self.i, self.j, self.k, self.l)
        if any(not isinstance(node, Node) for node in values):
            raise TypeError("tetrad entries must be Node objects")
        if len(set(values)) != 4:
            raise ValueError("tetrad entries must be distinct")

    @property
    def nodes(self) -> tuple[Node, Node, Node, Node]:
        return (self.i, self.j, self.k, self.l)


def _validate_limit(max_results: int | None) -> None:
    if max_results is None:
        return
    if isinstance(max_results, bool) or not isinstance(max_results, int):
        raise TypeError("max_results must be an integer or None")
    if max_results < 0:
        raise ValueError("max_results must be non-negative")


def _directed_endpoints(edge: Edge) -> tuple[Node, Node] | None:
    first_mark = edge.endpoint_at(edge.node1)
    second_mark = edge.endpoint_at(edge.node2)
    if first_mark is Endpoint.TAIL and second_mark is Endpoint.ARROW:
        return edge.node1, edge.node2
    if first_mark is Endpoint.ARROW and second_mark is Endpoint.TAIL:
        return edge.node2, edge.node1
    return None


def _canonical_structure(
    nodes: tuple[Node, ...], edges: tuple[Edge, ...]
) -> tuple[int, tuple[tuple[int, int], ...], tuple[frozenset[int], ...]]:
    """Replace each bidirected edge by a fresh latent common parent."""
    index = {node: position for position, node in enumerate(nodes)}
    directed: list[tuple[int, int]] = []
    parent_sets: list[set[int]] = [set() for _ in nodes]

    for edge in edges:
        endpoints = _directed_endpoints(edge)
        if endpoints is not None:
            parent, child = endpoints
            parent_index = index[parent]
            child_index = index[child]
            directed.append((parent_index, child_index))
            parent_sets[child_index].add(parent_index)
            continue

        # DAG's mixed-edge shorthand permits only arrow-arrow edges here.
        latent_index = len(parent_sets)
        parent_sets.append(set())
        for child in edge.nodes:
            child_index = index[child]
            directed.append((latent_index, child_index))
            parent_sets[child_index].add(latent_index)

    return (
        len(parent_sets),
        tuple(directed),
        tuple(frozenset(parents) for parents in parent_sets),
    )


def _trek_graph(
    node_count: int, directed: tuple[tuple[int, int], ...]
) -> tuple[tuple[int, ...], ...]:
    """Build the directed, two-copy trek graph of a canonical DAG."""
    adjacency: list[list[int]] = [[] for _ in range(2 * node_count)]
    present: list[set[int]] = [set() for _ in adjacency]

    def add_edge(source: int, target: int) -> None:
        if target not in present[source]:
            present[source].add(target)
            adjacency[source].append(target)

    for node_index in range(node_count):
        add_edge(2 * node_index, 2 * node_index + 1)
    for parent, child in directed:
        add_edge(2 * parent + 1, 2 * child + 1)
        add_edge(2 * child, 2 * parent)

    return tuple(tuple(neighbours) for neighbours in adjacency)


def _has_two_disjoint_paths(
    trek_adjacency: tuple[tuple[int, ...], ...],
    starts: tuple[int, int],
    targets: tuple[int, int],
) -> bool:
    """Test for two vertex-disjoint directed paths by unit-capacity max flow."""
    trek_size = len(trek_adjacency)
    source = 2 * trek_size
    sink = source + 1
    residual: dict[tuple[int, int], int] = {}
    adjacency: list[list[int]] = [[] for _ in range(sink + 1)]

    def add_edge(left: int, right: int, capacity: int) -> None:
        if (left, right) not in residual:
            adjacency[left].append(right)
            adjacency[right].append(left)
            residual[left, right] = 0
            residual[right, left] = 0
        residual[left, right] += capacity

    for vertex in range(trek_size):
        add_edge(2 * vertex, 2 * vertex + 1, 1)
    for left, neighbours in enumerate(trek_adjacency):
        for right in neighbours:
            add_edge(2 * left + 1, 2 * right, 2)
    for start in starts:
        add_edge(source, 2 * start, 1)
    for target in targets:
        add_edge(2 * target + 1, sink, 1)

    for _ in range(2):
        previous: dict[int, int] = {source: -1}
        queue = deque((source,))
        while queue and sink not in previous:
            current = queue.popleft()
            for neighbour in adjacency[current]:
                if neighbour not in previous and residual[current, neighbour] > 0:
                    previous[neighbour] = current
                    queue.append(neighbour)
                    if neighbour == sink:
                        break
        if sink not in previous:
            return False

        current = sink
        while current != source:
            prior = previous[current]
            residual[prior, current] -= 1
            residual[current, prior] += 1
            current = prior

    return True


def _matches_typology(
    kind: str,
    quadruple: tuple[int, int, int, int],
    left: tuple[int, int],
    right: tuple[int, int],
    parents: tuple[frozenset[int], ...],
) -> bool:
    if kind == "all":
        return True
    if any(len(parents[node]) != 1 for node in quadruple):
        return False

    if kind == "within":
        return len(set().union(*(parents[node] for node in quadruple))) == 1

    left_parents = parents[left[0]] | parents[left[1]]
    right_parents = parents[right[0]] | parents[right[1]]
    if kind == "between":
        return (
            len(left_parents) == 1
            and len(right_parents) == 1
            and left_parents != right_parents
        )

    # Pinned Dagitty's epistemic class has one same-parent pair opposite a
    # pair whose members have different parents in this determinant layout.
    return sorted((len(left_parents), len(right_parents))) == [1, 2]


def vanishing_tetrads(
    graph: Graph,
    *,
    kind: str = "all",
    max_results: int | None = None,
) -> EnumerationResult[Tetrad]:
    """Enumerate covariance tetrads that vanish generically in a linear SEM.

    The criterion is the trek-separation theorem: a two-by-two covariance
    determinant vanishes exactly when its two endpoint sets have no pair of
    vertex-disjoint paths in the canonical DAG's trek graph. Bidirected edges
    are interpreted as fresh latent common causes, and graph-marked latent
    nodes are excluded from the observed quadruples.

    Typology follows pinned Dagitty deterministically after canonicalization.
    Each endpoint must have exactly one direct parent. ``within`` requires one
    parent shared by all four endpoints; ``between`` requires a distinct shared
    parent for each determinant side; ``epistemic`` requires one shared-parent
    side and two different parents on the other side.
    """
    if not isinstance(graph, Graph):
        raise TypeError("graph must be a Graph")
    if graph.type is not GraphType.DAG:
        raise UnsupportedGraphTypeError("vanishing tetrads are supported only for DAG")
    if kind not in {"all", "within", "between", "epistemic"}:
        raise ValueError("kind must be 'all', 'within', 'between', or 'epistemic'")
    _validate_limit(max_results)
    graph.validate()
    if max_results == 0:
        return EnumerationResult()

    nodes = graph.nodes
    edges = graph.edges
    latent_nodes = set(graph.latents)
    observed_indices = tuple(
        index for index, node in enumerate(nodes) if node not in latent_nodes
    )
    if len(observed_indices) < 4:
        return EnumerationResult()

    node_count, directed, parents = _canonical_structure(nodes, edges)
    trek_adjacency = _trek_graph(node_count, directed)
    results: list[Tetrad] = []

    for quadruple in combinations(observed_indices, 4):
        first, second, third, fourth = quadruple
        layouts = (
            ((first, second), (third, fourth)),
            ((first, third), (second, fourth)),
            ((first, fourth), (second, third)),
        )
        for left, right in layouts:
            if not _matches_typology(kind, quadruple, left, right, parents):
                continue
            starts = (2 * left[0], 2 * left[1])
            targets = (2 * right[0] + 1, 2 * right[1] + 1)
            if _has_two_disjoint_paths(trek_adjacency, starts, targets):
                continue

            tetrad = Tetrad(
                nodes[left[0]],
                nodes[right[0]],
                nodes[right[1]],
                nodes[left[1]],
            )
            if max_results is not None and len(results) == max_results:
                return EnumerationResult(results, truncated=True)
            results.append(tetrad)

    return EnumerationResult(results)
