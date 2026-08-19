"""Endpoint-aware traversal, path, and separator algorithms.

Informed by Dagitty's ``jslib/graph/GraphAnalyzer.js`` at commit ``7a657776``.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Iterator

from .exceptions import InvalidGraphError, UnsupportedGraphTypeError
from .model import (
    Edge,
    Endpoint,
    EnumerationResult,
    Graph,
    GraphType,
    Node,
    NodeSet,
    Path,
    is_parent_edge,
)

__all__ = [
    "connected_components",
    "dconnected",
    "dseparated",
    "is_path_open",
    "iter_paths",
    "minimal_separators",
    "paths",
    "reachable_nodes",
]


_SEPARATION_TYPES = frozenset(
    {GraphType.DAG, GraphType.MAG, GraphType.PDAG, GraphType.PAG}
)
_PATH_TYPES = frozenset({GraphType.DAG, GraphType.MAG, GraphType.PDAG})


def _require_graph(graph: Graph) -> None:
    if not isinstance(graph, Graph):
        raise TypeError("graph must be a Graph")


def _require_type(graph: Graph, supported: frozenset[GraphType], operation: str) -> None:
    if graph.type not in supported:
        names = ", ".join(item.value.upper() for item in sorted(supported, key=str))
        raise UnsupportedGraphTypeError(f"{operation} is supported only for {names}")


def _validate_max_results(max_results: int | None) -> None:
    if max_results is None:
        return
    if isinstance(max_results, bool) or not isinstance(max_results, int):
        raise TypeError("max_results must be an int or None")
    if max_results < 0:
        raise ValueError("max_results must be non-negative")


def _endpoint(edge: Edge, node: Node, pag_approximation: bool) -> Endpoint:
    endpoint = edge.endpoint_at(node)
    if pag_approximation and endpoint is Endpoint.CIRCLE:
        return Endpoint.TAIL
    return endpoint


def _ancestors_of(
    graph: Graph,
    nodes: Iterable[Node],
    *,
    pag_approximation: bool = False,
) -> set[Node]:
    """Return strict ancestors, optionally after replacing PAG circles by tails."""
    found = set(nodes)
    queue = deque(found)
    while queue:
        child = queue.popleft()
        for edge in graph.incident_edges(child):
            parent = edge.other(child)
            if (
                _endpoint(edge, parent, pag_approximation) is Endpoint.TAIL
                and _endpoint(edge, child, pag_approximation) is Endpoint.ARROW
                and parent not in found
            ):
                found.add(parent)
                queue.append(parent)
    return found


def reachable_nodes(
    graph: Graph,
    first: Node | Iterable[Node],
    given: Node | Iterable[Node] = (),
) -> NodeSet:
    """Return nodes m-connected to ``first`` given ``given``.

    For PAGs this deliberately implements Dagitty's pinned approximation: every
    circle endpoint is treated as a tail before traversal.
    """
    _require_graph(graph)
    _require_type(graph, _SEPARATION_TYPES, "reachability")
    sources = graph._resolve_nodes(first)
    conditioned = set(graph._resolve_nodes(given))
    if not sources:
        return NodeSet()

    pag_approximation = graph.type is GraphType.PAG
    ancestors_of_conditioned = _ancestors_of(
        graph, conditioned, pag_approximation=pag_approximation
    )
    # ``forward`` means arrival at an arrowhead; ``backward`` means arrival at
    # a tail-like endpoint. Keeping these states separate prevents an
    # undirected edge from being traversed out and immediately back to turn a
    # closed collider into an open route.
    forward_queue: deque[Node] = deque()
    backward_queue: deque[Node] = deque(sources)
    forward_visited: set[Node] = set()
    backward_visited: set[Node] = set()

    def relatives(
        node: Node, source_marks: set[Endpoint], target_marks: set[Endpoint]
    ) -> Iterator[Node]:
        for edge in graph.incident_edges(node):
            other = edge.other(node)
            if (
                _endpoint(edge, node, pag_approximation) in source_marks
                and _endpoint(edge, other, pag_approximation) in target_marks
            ):
                yield other

    def enqueue(queue: deque[Node], visited: set[Node], values: Iterable[Node]) -> None:
        for node in values:
            if node not in visited and node not in queue:
                queue.append(node)

    while forward_queue or backward_queue:
        if forward_queue:
            current = forward_queue.pop()
            if current in forward_visited:
                continue
            forward_visited.add(current)
            if current in ancestors_of_conditioned:
                enqueue(
                    backward_queue,
                    backward_visited,
                    relatives(current, {Endpoint.ARROW}, {Endpoint.TAIL}),
                )
                enqueue(
                    forward_queue,
                    forward_visited,
                    relatives(current, {Endpoint.ARROW}, {Endpoint.ARROW}),
                )
            if current not in conditioned:
                enqueue(
                    forward_queue,
                    forward_visited,
                    relatives(current, {Endpoint.TAIL}, {Endpoint.ARROW, Endpoint.TAIL}),
                )

        if backward_queue:
            current = backward_queue.pop()
            if current in backward_visited:
                continue
            backward_visited.add(current)
            if current in conditioned:
                continue
            enqueue(
                forward_queue,
                forward_visited,
                relatives(
                    current,
                    {Endpoint.TAIL, Endpoint.ARROW},
                    {Endpoint.ARROW},
                ),
            )
            enqueue(
                backward_queue,
                backward_visited,
                relatives(current, {Endpoint.ARROW, Endpoint.TAIL}, {Endpoint.TAIL}),
            )

    reached = forward_visited | backward_visited
    return NodeSet(node for node in graph.nodes if node in reached)


def dconnected(
    graph: Graph,
    first: Node | Iterable[Node],
    second: Node | Iterable[Node],
    given: Node | Iterable[Node] = (),
) -> bool:
    """Return whether any node in ``first`` is m-connected to ``second``."""
    _require_graph(graph)
    _require_type(graph, _SEPARATION_TYPES, "d-connection")
    sources = graph._resolve_nodes(first)
    targets = graph._resolve_nodes(second)
    conditioned = graph._resolve_nodes(given)
    conditioned_set = set(conditioned)
    if conditioned_set & (set(sources) | set(targets)):
        raise InvalidGraphError("separation endpoints and given nodes must be disjoint")
    if not targets:
        return False
    reachable = reachable_nodes(graph, sources, conditioned)
    return any(node in reachable for node in targets)


def dseparated(
    graph: Graph,
    first: Node | Iterable[Node],
    second: Node | Iterable[Node],
    given: Node | Iterable[Node] = (),
) -> bool:
    """Return the Boolean complement of :func:`dconnected`."""
    return not dconnected(graph, first, second, given=given)


def _owned_path(graph: Graph, path: Path) -> Path:
    if not isinstance(path, Path):
        raise TypeError("path must be a Path")
    owned_nodes = tuple(graph._resolve_node(node) for node in path.nodes)
    owned_edges = tuple(graph._find_edge(edge) for edge in path.edges)
    return Path(owned_nodes, owned_edges)


def _path_is_open(
    path: Path,
    conditioned: set[Node],
    ancestors_of_conditioned: set[Node],
) -> bool:
    for index in range(1, len(path.nodes) - 1):
        node = path.nodes[index]
        collider = (
            path.edges[index - 1].endpoint_at(node) is Endpoint.ARROW
            and path.edges[index].endpoint_at(node) is Endpoint.ARROW
        )
        if collider:
            if node not in ancestors_of_conditioned:
                return False
        elif node in conditioned:
            return False
    return True


def is_path_open(
    graph: Graph,
    path: Path,
    *,
    given: Node | Iterable[Node] = (),
) -> bool:
    """Classify one exact path using its endpoint incidences.

    Only internal path nodes are classified. A collider is open when it or a
    strict directed descendant is in ``given``; a conditioned non-collider is
    closed.
    """
    _require_graph(graph)
    _require_type(graph, _PATH_TYPES, "path classification")
    owned = _owned_path(graph, path)
    conditioned = set(graph._resolve_nodes(given))
    ancestors_of_conditioned = _ancestors_of(graph, conditioned)
    return _path_is_open(owned, conditioned, ancestors_of_conditioned)


def _path_choices(
    graph: Graph, node: Node, directed: bool
) -> tuple[tuple[Node, Edge], ...]:
    choices: list[tuple[Node, Edge]] = []
    for edge in graph.incident_edges(node):
        other = edge.other(node)
        if not directed or is_parent_edge(edge, node, other):
            choices.append((other, edge))
    return tuple(choices)


def iter_paths(
    graph: Graph,
    first: Node | Iterable[Node],
    second: Node | Iterable[Node],
    *,
    directed: bool = False,
    given: Node | Iterable[Node] = (),
    open_only: bool = False,
    max_results: int | None = 100,
) -> Iterator[Path]:
    """Iterate simple paths in deterministic depth-first order.

    Different endpoint-defined edges between the same node pair yield distinct
    paths. Set ``open_only`` to filter by ``given`` without conflating path
    enumeration with openness classification. The graph snapshot is captured by
    this call, before iteration begins.
    """
    _require_graph(graph)
    _require_type(graph, _PATH_TYPES, "path enumeration")
    if not isinstance(directed, bool):
        raise TypeError("directed must be a bool")
    if not isinstance(open_only, bool):
        raise TypeError("open_only must be a bool")
    _validate_max_results(max_results)

    sources = graph._resolve_nodes(first)
    targets = graph._resolve_nodes(second)
    conditioned_source = graph._resolve_nodes(given)
    snapshot = graph.clone()
    snapshot_sources = tuple(snapshot.node(node.identifier) for node in sources)
    snapshot_targets = tuple(snapshot.node(node.identifier) for node in targets)
    conditioned = {
        snapshot.node(node.identifier) for node in conditioned_source
    }
    ancestors_of_conditioned = _ancestors_of(snapshot, conditioned)

    def generate() -> Iterator[Path]:
        if max_results == 0 or not snapshot_sources or not snapshot_targets:
            return
        emitted = 0
        for source in snapshot_sources:
            for target in snapshot_targets:
                if source == target:
                    candidate = Path((source,), ())
                    if not open_only or _path_is_open(
                        candidate, conditioned, ancestors_of_conditioned
                    ):
                        yield candidate
                        emitted += 1
                        if max_results is not None and emitted >= max_results:
                            return
                    continue

                path_nodes = [source]
                path_edges: list[Edge] = []
                visited = {source}
                stack: list[tuple[Node, Iterator[tuple[Node, Edge]]]] = [
                    (source, iter(_path_choices(snapshot, source, directed)))
                ]
                while stack:
                    _, choices = stack[-1]
                    try:
                        other, edge = next(choices)
                    except StopIteration:
                        stack.pop()
                        if stack:
                            removed = path_nodes.pop()
                            visited.remove(removed)
                            path_edges.pop()
                        continue
                    if other in visited:
                        continue

                    path_nodes.append(other)
                    path_edges.append(edge)
                    visited.add(other)
                    if other == target:
                        candidate = Path(tuple(path_nodes), tuple(path_edges))
                        visited.remove(path_nodes.pop())
                        path_edges.pop()
                        if not open_only or _path_is_open(
                            candidate, conditioned, ancestors_of_conditioned
                        ):
                            yield candidate
                            emitted += 1
                            if max_results is not None and emitted >= max_results:
                                return
                    else:
                        stack.append(
                            (other, iter(_path_choices(snapshot, other, directed)))
                        )

    return generate()


def paths(
    graph: Graph,
    first: Node | Iterable[Node],
    second: Node | Iterable[Node],
    *,
    directed: bool = False,
    given: Node | Iterable[Node] = (),
    open_only: bool = False,
    max_results: int | None = 100,
) -> EnumerationResult[Path]:
    """Return a bounded collection of simple paths and truncation state."""
    _validate_max_results(max_results)
    if max_results == 0:
        # Zero is an explicit no-search request.
        iterator = iter_paths(
            graph,
            first,
            second,
            directed=directed,
            given=given,
            open_only=open_only,
            max_results=0,
        )
        return EnumerationResult(iterator, truncated=False)
    if max_results is None:
        return EnumerationResult(
            iter_paths(
                graph,
                first,
                second,
                directed=directed,
                given=given,
                open_only=open_only,
                max_results=None,
            ),
            truncated=False,
        )

    iterator = iter_paths(
        graph,
        first,
        second,
        directed=directed,
        given=given,
        open_only=open_only,
        max_results=max_results + 1,
    )
    items: list[Path] = []
    for item in iterator:
        if len(items) == max_results:
            return EnumerationResult(items, truncated=True)
        items.append(item)
    return EnumerationResult(items, truncated=False)


def _require_undirected(graph: Graph, operation: str) -> None:
    _require_graph(graph)
    if graph.type is not GraphType.GRAPH:
        raise UnsupportedGraphTypeError(f"{operation} requires an undirected GRAPH")


def _adjacent_avoiding(
    graph: Graph, node: Node, avoided: set[Node]
) -> Iterator[Node]:
    for edge in graph.incident_edges(node):
        other = edge.other(node)
        if other not in avoided:
            yield other


def connected_components(
    graph: Graph,
    *,
    avoiding: Node | Iterable[Node] = (),
) -> tuple[NodeSet, ...]:
    """Return components of an undirected graph after removing ``avoiding``."""
    _require_undirected(graph, "connected components")
    avoided = set(graph._resolve_nodes(avoiding))
    visited = set(avoided)
    result: list[NodeSet] = []
    for root in graph.nodes:
        if root in visited:
            continue
        members: set[Node] = {root}
        visited.add(root)
        queue = deque((root,))
        while queue:
            current = queue.popleft()
            for other in _adjacent_avoiding(graph, current, avoided):
                if other not in visited:
                    visited.add(other)
                    members.add(other)
                    queue.append(other)
        result.append(NodeSet(node for node in graph.nodes if node in members))
    return tuple(result)


def _separator_iterator(
    graph: Graph,
    sources: tuple[Node, ...],
    targets: tuple[Node, ...],
    mandatory: tuple[Node, ...],
    forbidden: tuple[Node, ...],
) -> Iterator[NodeSet]:
    order = {node: index for index, node in enumerate(graph.nodes)}
    mandatory_set = set(mandatory)
    forbidden_set = set(forbidden)
    source_set = set(sources)
    target_set = set(targets)
    seen: set[frozenset[Node]] = set()

    if not sources or not targets or source_set & target_set:
        return
    if mandatory_set & (source_set | target_set | forbidden_set):
        return

    def ordered(nodes: Iterable[Node]) -> list[Node]:
        return sorted(set(nodes), key=order.__getitem__)

    def neighbors_through_forbidden(nodes: Iterable[Node]) -> list[Node]:
        visited = set(nodes) | mandatory_set
        queue = deque(ordered(nodes))
        boundary: set[Node] = set()
        while queue:
            current = queue.popleft()
            for edge in graph.incident_edges(current):
                other = edge.other(current)
                if other in visited:
                    continue
                visited.add(other)
                if other in forbidden_set:
                    queue.append(other)
                else:
                    boundary.add(other)
        return ordered(boundary)

    def component_avoiding(
        starts: Iterable[Node], avoided_nodes: Iterable[Node]
    ) -> list[Node]:
        avoided = set(avoided_nodes)
        starts_ordered = ordered(starts)
        visited = set(avoided)
        result: set[Node] = set()
        queue: deque[Node] = deque()
        for node in starts_ordered:
            visited.add(node)
            result.add(node)
            queue.append(node)
        while queue:
            current = queue.popleft()
            for edge in graph.incident_edges(current):
                other = edge.other(current)
                if other not in visited:
                    visited.add(other)
                    result.add(other)
                    queue.append(other)
        return ordered(result)

    def near_separator(a_side: Iterable[Node]) -> list[Node]:
        neighborhood = neighbors_through_forbidden(a_side)
        target_component = component_avoiding(
            targets, list(neighborhood) + list(mandatory)
        )
        return neighbors_through_forbidden(target_component)

    initial_u = ordered(list(targets) + neighbors_through_forbidden(targets))

    def enumerate_from(a_side: list[Node], excluded: list[Node]) -> Iterator[NodeSet]:
        separator = near_separator(a_side)
        source_component = component_avoiding(
            sources, list(separator) + list(mandatory)
        )
        if set(source_component) & set(excluded):
            return
        candidates = [
            node
            for node in neighbors_through_forbidden(source_component)
            if node not in excluded
        ]
        if candidates:
            choice = candidates[0]
            yield from enumerate_from(ordered(source_component + [choice]), excluded)
            yield from enumerate_from(source_component, ordered(excluded + [choice]))
            return

        result_set = frozenset(separator) | frozenset(mandatory)
        if result_set in seen:
            return
        seen.add(result_set)
        yield NodeSet(node for node in graph.nodes if node in result_set)

    yield from enumerate_from(list(sources), initial_u)


def minimal_separators(
    graph: Graph,
    first: Node | Iterable[Node],
    second: Node | Iterable[Node],
    *,
    mandatory: Node | Iterable[Node] = (),
    forbidden: Node | Iterable[Node] = (),
    max_results: int | None = None,
) -> EnumerationResult[NodeSet]:
    """Enumerate minimal vertex separators of an undirected graph.

    Mandatory vertices are fixed members, so minimality applies only to the
    remaining members. Forbidden vertices may be traversed but never returned.
    """
    _require_undirected(graph, "minimal separators")
    _validate_max_results(max_results)
    sources = graph._resolve_nodes(first)
    targets = graph._resolve_nodes(second)
    required = graph._resolve_nodes(mandatory)
    excluded = graph._resolve_nodes(forbidden)
    if max_results == 0:
        return EnumerationResult((), truncated=False)

    iterator = _separator_iterator(graph, sources, targets, required, excluded)
    if max_results is None:
        return EnumerationResult(iterator, truncated=False)

    items: list[NodeSet] = []
    for item in iterator:
        if len(items) == max_results:
            return EnumerationResult(items, truncated=True)
        items.append(item)
    return EnumerationResult(items, truncated=False)
