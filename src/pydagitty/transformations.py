"""Pure causal-graph transformations.

The algorithms in this module are informed by Dagitty's
``jslib/graph/GraphTransformer.js`` at commit ``7a657776``. Traversal state is
kept locally and every public function returns a new graph.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from copy import deepcopy
from itertools import combinations

from .exceptions import InvalidGraphError, UnsupportedGraphTypeError
from .model import (
    DAG,
    DIGRAPH,
    GRAPH,
    MAG,
    PDAG,
    Canonicalization,
    Edge,
    Endpoint,
    EnumerationResult,
    Graph,
    GraphType,
    Node,
    NodeStatus,
    is_parent_edge,
    is_spouse_edge,
)

_Pair = tuple[Node, Node]
_Direction = tuple[Node, Node]
_Collider = tuple[frozenset[Node], Node]


def _require_type(graph: Graph, allowed: set[GraphType], operation: str) -> None:
    if not isinstance(graph, Graph):
        raise TypeError("graph must be a Graph")
    if graph.type not in allowed:
        names = ", ".join(sorted(item.value for item in allowed))
        raise UnsupportedGraphTypeError(f"{operation} is supported only for {names}")


def _copy_nodes(source: Graph, target: Graph, nodes: Iterable[Node]) -> None:
    for node in nodes:
        target.add_node(node, **deepcopy(dict(source.node_attributes[node])))


def _copy_statuses(source: Graph, target: Graph) -> None:
    retained = set(target.nodes)
    for status in NodeStatus:
        target.set_status(
            status,
            (node for node in source.nodes if node in retained and node in source.status(status)),
        )


def _add_mapped_edge(source: Graph, target: Graph, old: Edge, new: Edge) -> None:
    target.add_edge(new, **deepcopy(dict(source.edge_attributes[old])))


def _add_generated_edge(source: Graph, target: Graph, old: Edge, new: Edge) -> None:
    attributes = {
        key: value
        for key, value in source.edge_attributes[old].items()
        if key not in {"beta", "control_points", "style"}
    }
    target.add_edge(new, **deepcopy(attributes))


def _strict_direction(edge: Edge) -> _Direction | None:
    if {edge.left, edge.right} != {Endpoint.TAIL, Endpoint.ARROW}:
        return None
    parent = edge.node1 if edge.left is Endpoint.TAIL else edge.node2
    return parent, edge.other(parent)


def _new_generated_node(graph: Graph, prefix: str, start: int) -> tuple[Node, int]:
    identifiers = {node.identifier for node in graph.nodes}
    index = start
    while f"{prefix}{index}" in identifiers:
        index += 1
    return Node(f"{prefix}{index}"), index + 1


def ancestor_graph(
    graph: Graph, nodes: Node | Iterable[Node] | None = None
) -> Graph:
    """Return the subgraph induced by the anteriors of the requested nodes."""
    _require_type(
        graph,
        {GraphType.DAG, GraphType.MAG, GraphType.PDAG},
        "ancestor_graph",
    )
    if nodes is None:
        seeds_set = set(graph.exposures) | set(graph.outcomes) | set(graph.adjusted_nodes)
        seeds = tuple(node for node in graph.nodes if node in seeds_set)
    else:
        seeds = graph._resolve_nodes(nodes)
    if graph.type is GraphType.DAG:
        retained = graph.ancestors(seeds)
    else:
        retained = graph.anteriors(seeds)
    return graph.induced_subgraph(retained)


def canonicalize(graph: Graph) -> Canonicalization:
    """Replace bidirected and undirected edges by latent and selected nodes."""
    _require_type(graph, {GraphType.DAG, GraphType.MAG}, "canonicalize")
    result = DAG()
    _copy_nodes(graph, result, graph.nodes)
    latent_nodes: list[Node] = []
    selection_nodes: list[Node] = []
    latent_index = 1
    selection_index = 1

    for edge in graph.edges:
        direction = _strict_direction(edge)
        if direction is not None:
            parent, child = direction
            _add_mapped_edge(
                graph,
                result,
                edge,
                Edge(parent, child, Endpoint.TAIL, Endpoint.ARROW),
            )
        elif is_spouse_edge(edge, edge.node1, edge.node2):
            latent, latent_index = _new_generated_node(result, "L", latent_index)
            result.add_node(latent)
            result.add_edge(Edge(latent, edge.node1))
            result.add_edge(Edge(latent, edge.node2))
            latent_nodes.append(latent)
        elif edge.left is Endpoint.TAIL and edge.right is Endpoint.TAIL:
            selected, selection_index = _new_generated_node(result, "S", selection_index)
            result.add_node(selected)
            result.add_edge(Edge(edge.node1, selected))
            result.add_edge(Edge(edge.node2, selected))
            selection_nodes.append(selected)
        else:
            raise InvalidGraphError(
                "canonicalization requires directed, bidirected, or undirected edges"
            )

    _copy_statuses(graph, result)
    result.set_status(
        NodeStatus.LATENT,
        tuple(node for node in result.nodes if node in graph.latents) + tuple(latent_nodes),
    )
    result.set_status(
        NodeStatus.SELECTED,
        tuple(node for node in result.nodes if node in graph.selected_nodes)
        + tuple(selection_nodes),
    )
    return Canonicalization(result, latent_nodes, selection_nodes)


def moralize(graph: Graph) -> GRAPH:
    """Return the moral graph, completing each district and its parents."""
    _require_type(
        graph,
        {GraphType.DAG, GraphType.MAG, GraphType.PDAG, GraphType.GRAPH},
        "moralize",
    )
    if graph.type is GraphType.GRAPH:
        result = GRAPH()
        _copy_nodes(graph, result, graph.nodes)
        for edge in graph.edges:
            _add_mapped_edge(graph, result, edge, edge)
        _copy_statuses(graph, result)
        return result

    result = GRAPH()
    _copy_nodes(graph, result, graph.nodes)

    # Existing undirected edges are the only unchanged edges in this mapping.
    for edge in graph.edges:
        if edge.left is Endpoint.TAIL and edge.right is Endpoint.TAIL:
            _add_mapped_edge(graph, result, edge, edge)

    unseen = set(graph.nodes)
    while unseen:
        root = next(node for node in graph.nodes if node in unseen)
        district = {root}
        queue = [root]
        unseen.remove(root)
        while queue:
            current = queue.pop()
            for spouse in graph.spouses(current):
                if spouse not in district:
                    district.add(spouse)
                    unseen.discard(spouse)
                    queue.append(spouse)
        family = district | set(graph.parents(district))
        ordered = [node for node in graph.nodes if node in family]
        for first, second in combinations(ordered, 2):
            result.add_edge(Edge(first, second, Endpoint.TAIL, Endpoint.TAIL))

    _copy_statuses(graph, result)
    return result


def _pag_approximation(graph: Graph) -> Graph:
    if graph.type is not GraphType.PAG:
        return graph
    edges = tuple(
        Edge(
            edge.node1,
            edge.node2,
            Endpoint.TAIL if edge.left is Endpoint.CIRCLE else edge.left,
            Endpoint.TAIL if edge.right is Endpoint.CIRCLE else edge.right,
        )
        for edge in graph.edges
    )
    return DIGRAPH(nodes=graph.nodes, edges=edges)


def _proper_possible_causal_nodes(
    graph: Graph, exposures: tuple[Node, ...], outcomes: tuple[Node, ...]
) -> set[Node]:
    exposure_set = set(exposures)
    backward = set(outcomes)
    queue = list(outcomes)
    while queue:
        current = queue.pop()
        if current in exposure_set:
            continue
        for previous in tuple(graph.parents(current)) + tuple(graph.neighbours(current)):
            if previous not in backward:
                backward.add(previous)
                queue.append(previous)
    return backward & set(graph.possible_descendants(exposures))


def _edge_visible(graph: Graph, parent: Node, child: Node) -> bool:
    if graph.type not in {GraphType.MAG, GraphType.PAG}:
        return True

    # Search backwards along a collider path into parent.  Internal nodes on
    # such a path must be parents of child; its remote endpoint must not be
    # adjacent to child.
    child_parents = set(graph.parents(child))
    stack = [parent]
    visited = {parent}
    while stack:
        current = stack.pop()
        for edge in graph.incident_edges(current):
            if edge.endpoint_at(current) is not Endpoint.ARROW:
                continue
            other = edge.other(current)
            if not graph.adjacent(other, child):
                return True
            if (
                other not in visited
                and other in child_parents
                and edge.endpoint_at(other) is Endpoint.ARROW
            ):
                visited.add(other)
                stack.append(other)
    return False


def backdoor_graph(
    graph: Graph,
    exposure: Node | Iterable[Node] | None = None,
    outcome: Node | Iterable[Node] | None = None,
) -> Graph:
    """Remove visible first edges of proper possibly causal paths."""
    _require_type(
        graph,
        {GraphType.DAG, GraphType.MAG, GraphType.PDAG, GraphType.PAG},
        "backdoor_graph",
    )
    exposures = tuple(graph.exposures) if exposure is None else graph._resolve_nodes(exposure)
    outcomes = tuple(graph.outcomes) if outcome is None else graph._resolve_nodes(outcome)
    result = graph.clone()
    if not exposures or not outcomes:
        return result

    working = _pag_approximation(graph)
    working_exposures = tuple(working.node(node.identifier) for node in exposures)
    working_outcomes = tuple(working.node(node.identifier) for node in outcomes)
    causal_nodes = _proper_possible_causal_nodes(
        working, working_exposures, working_outcomes
    )

    for source in exposures:
        work_source = working.node(source.identifier)
        for edge in graph.incident_edges(source):
            direction = _strict_direction(edge)
            if direction is None or direction[0] != source:
                continue
            child = direction[1]
            work_child = working.node(child.identifier)
            if work_child not in causal_nodes:
                continue
            work_edges = working.edges_between(work_source, work_child)
            work_edge = next(
                (
                    item
                    for item in work_edges
                    if is_parent_edge(item, work_source, work_child)
                ),
                None,
            )
            if work_edge is not None and _edge_visible(graph, source, child):
                result.remove_edge(edge)
    return result


def indirect_graph(
    graph: Graph, exposure: Node | Iterable[Node] | None = None
) -> Graph:
    """Remove direct exposure-to-outcome edges for direct-effect analysis."""
    _require_type(
        graph,
        {GraphType.DAG, GraphType.MAG, GraphType.PDAG, GraphType.PAG},
        "indirect_graph",
    )
    exposures = tuple(graph.exposures) if exposure is None else graph._resolve_nodes(exposure)
    outcomes = set(graph.outcomes)
    result = graph.clone()
    for edge in graph.edges:
        direction = _strict_direction(edge)
        if direction is not None and direction[0] in exposures and direction[1] in outcomes:
            result.remove_edge(edge)
    return result


def structural_part(graph: Graph) -> Graph:
    """Return the subgraph induced by latent variables."""
    _require_type(
        graph,
        {GraphType.DAG, GraphType.DIGRAPH},
        "structural_part",
    )
    return graph.induced_subgraph(graph.latents)


def measurement_part(graph: Graph) -> Graph:
    """Return edges whose directed child, or both bidirected ends, are observed."""
    _require_type(
        graph,
        {GraphType.DAG, GraphType.DIGRAPH},
        "measurement_part",
    )
    latent = set(graph.latents)
    result = graph._empty_same_type()
    _copy_nodes(graph, result, graph.nodes)
    for edge in graph.edges:
        direction = _strict_direction(edge)
        if direction is not None and direction[1] not in latent:
            _add_mapped_edge(graph, result, edge, edge)
        elif (
            is_spouse_edge(edge, edge.node1, edge.node2)
            and edge.node1 not in latent
            and edge.node2 not in latent
        ):
            _add_mapped_edge(graph, result, edge, edge)

    for node in tuple(result.nodes):
        if node in latent and not result.incident_edges(node):
            result.remove_node(node)
    _copy_statuses(graph, result)
    return result


def _has_inducing_path(
    graph: Graph,
    first: Node,
    second: Node,
    latent: set[Node],
    endpoint_ancestors: set[Node],
) -> bool:
    def visit(
        current: Node,
        previous_edge: Edge | None,
        visited: set[Node],
    ) -> bool:
        if current == second:
            return True
        for edge in graph.incident_edges(current):
            other = edge.other(current)
            if other in visited:
                continue
            if previous_edge is not None:
                collider = (
                    previous_edge.endpoint_at(current) is Endpoint.ARROW
                    and edge.endpoint_at(current) is Endpoint.ARROW
                )
                if collider:
                    if current not in endpoint_ancestors:
                        continue
                elif current not in latent:
                    continue
            visited.add(other)
            if visit(other, edge, visited):
                return True
            visited.remove(other)
        return False

    return visit(first, None, {first})


def to_mag(graph: Graph) -> MAG:
    """Project latent nodes out of a DAG, returning its latent-projection MAG."""
    _require_type(graph, {GraphType.DAG}, "to_mag")
    if graph.selected_nodes:
        raise InvalidGraphError("to_mag does not project selected nodes")
    if graph.find_cycle() is not None:
        raise InvalidGraphError("latent projection requires an acyclic DAG")

    latent = set(graph.latents)
    observed = tuple(node for node in graph.nodes if node not in latent)
    ancestors = {node: set(graph.ancestors(node)) for node in observed}
    result = MAG()
    _copy_nodes(graph, result, observed)

    for first, second in combinations(observed, 2):
        if not _has_inducing_path(
            graph,
            first,
            second,
            latent,
            ancestors[first] | ancestors[second],
        ):
            continue
        if first in ancestors[second]:
            projected = Edge(first, second, Endpoint.TAIL, Endpoint.ARROW)
        elif second in ancestors[first]:
            projected = Edge(second, first, Endpoint.TAIL, Endpoint.ARROW)
        else:
            projected = Edge(first, second, Endpoint.ARROW, Endpoint.ARROW)
        if graph.has_edge(projected):
            old = graph._find_edge(projected)
            _add_mapped_edge(graph, result, old, projected)
        else:
            result.add_edge(projected)

    _copy_statuses(graph, result)
    return result


def _ordinary_edges(graph: Graph, operation: str) -> tuple[Edge, ...]:
    seen: set[frozenset[Node]] = set()
    for edge in graph.edges:
        pair = frozenset(edge.nodes)
        if pair in seen:
            raise InvalidGraphError(f"{operation} requires a simple graph")
        seen.add(pair)
        if _strict_direction(edge) is None and not (
            edge.left is Endpoint.TAIL and edge.right is Endpoint.TAIL
        ):
            raise InvalidGraphError(
                f"{operation} requires only directed and undirected edges"
            )
    return graph.edges


def _adjacency(edges: Iterable[Edge]) -> set[frozenset[Node]]:
    return {frozenset(edge.nodes) for edge in edges}


def _colliders(
    nodes: tuple[Node, ...],
    adjacency: set[frozenset[Node]],
    directions: Iterable[_Direction],
) -> set[_Collider]:
    parents: dict[Node, set[Node]] = {node: set() for node in nodes}
    for parent, child in directions:
        parents[child].add(parent)
    result: set[_Collider] = set()
    for center in nodes:
        for first, second in combinations(parents[center], 2):
            if frozenset((first, second)) not in adjacency:
                result.add((frozenset((first, second)), center))
    return result


def _reaches(children: dict[Node, set[Node]], start: Node, target: Node) -> bool:
    queue = [start]
    visited = {start}
    while queue:
        current = queue.pop()
        if current == target:
            return True
        for child in children[current]:
            if child not in visited:
                visited.add(child)
                queue.append(child)
    return False


def _orientation_assignments(
    graph: Graph,
    *,
    preferred: dict[_Pair, _Direction] | None = None,
    fix_directed: bool = True,
    required_colliders: set[_Collider] | None = None,
) -> Iterator[dict[_Pair, _Direction]]:
    edges = _ordinary_edges(graph, "orientation")
    pairs = tuple(edge.nodes for edge in edges)
    adjacency = _adjacency(edges)
    fixed: dict[_Pair, _Direction] = {}
    for edge in edges:
        direction = _strict_direction(edge)
        if direction is not None:
            fixed[edge.nodes] = direction
    required = (
        _colliders(graph.nodes, adjacency, fixed.values())
        if required_colliders is None
        else required_colliders
    )
    if not fix_directed:
        fixed = {}
    children: dict[Node, set[Node]] = {node: set() for node in graph.nodes}
    parents: dict[Node, set[Node]] = {node: set() for node in graph.nodes}
    assignment: dict[_Pair, _Direction] = {}

    def add(direction: _Direction) -> bool:
        parent, child = direction
        if _reaches(children, child, parent):
            return False
        for other_parent in parents[child]:
            if frozenset((parent, other_parent)) not in adjacency and (
                frozenset((parent, other_parent)), child
            ) not in required:
                return False
        children[parent].add(child)
        parents[child].add(parent)
        return True

    for pair in pairs:
        if pair in fixed:
            direction = fixed[pair]
            if not add(direction):
                return
            assignment[pair] = direction

    undecided = tuple(pair for pair in pairs if pair not in fixed)

    def enumerate_from(index: int) -> Iterator[dict[_Pair, _Direction]]:
        if index == len(undecided):
            if _colliders(graph.nodes, adjacency, assignment.values()) == required:
                yield dict(assignment)
            return
        pair = undecided[index]
        first, second = pair
        choices = [(first, second), (second, first)]
        if preferred is not None and pair in preferred:
            wanted = preferred[pair]
            choices = [wanted, (wanted[1], wanted[0])]
        for direction in choices:
            if not add(direction):
                continue
            assignment[pair] = direction
            yield from enumerate_from(index + 1)
            del assignment[pair]
            parent, child = direction
            children[parent].remove(child)
            parents[child].remove(parent)

    yield from enumerate_from(0)


def _build_dag(source: Graph, assignment: dict[_Pair, _Direction]) -> DAG:
    result = DAG()
    _copy_nodes(source, result, source.nodes)
    for old in source.edges:
        parent, child = assignment[old.nodes]
        new = Edge(parent, child, Endpoint.TAIL, Endpoint.ARROW)
        if _strict_direction(old) is None:
            _add_generated_edge(source, result, old, new)
        else:
            _add_mapped_edge(source, result, old, new)
    _copy_statuses(source, result)
    return result


def orient_pdag(graph: Graph) -> DAG:
    """Return the first deterministic consistent DAG extension of a PDAG."""
    _require_type(graph, {GraphType.PDAG}, "orient_pdag")
    _ordinary_edges(graph, "orient_pdag")
    assignment = next(_orientation_assignments(graph), None)
    if assignment is None:
        raise InvalidGraphError("PDAG has no compatible acyclic orientation")
    return _build_dag(graph, assignment)


def _directed_dag_edges(graph: Graph, operation: str) -> tuple[Edge, ...]:
    edges = _ordinary_edges(graph, operation)
    if any(_strict_direction(edge) is None for edge in edges):
        raise InvalidGraphError(f"{operation} requires a fully directed DAG")
    if graph.find_cycle() is not None:
        raise InvalidGraphError(f"{operation} requires an acyclic DAG")
    return edges


def _equivalence_class_from_dag(graph: Graph) -> PDAG:
    edges = _directed_dag_edges(graph, "equivalence_class")
    result = PDAG()
    _copy_nodes(graph, result, graph.nodes)
    for old in edges:
        _add_mapped_edge(graph, result, old, old)

    def undirected(first: Node, second: Node) -> bool:
        return any(
            edge.left is Endpoint.TAIL and edge.right is Endpoint.TAIL
            for edge in result.edges_between(first, second)
        )

    def strongly_protected(edge: Edge) -> bool:
        direction = _strict_direction(edge)
        if direction is None:
            return False
        parent, child = direction
        if any(
            ancestor != child and not result.adjacent(ancestor, child)
            for ancestor in result.parents(parent)
        ):
            return True
        other_parents = tuple(node for node in result.parents(child) if node != parent)
        if any(
            not result.adjacent(other, parent) or parent in result.parents(other)
            for other in other_parents
        ):
            return True
        for first, second in combinations(other_parents, 2):
            if (
                not result.adjacent(first, second)
                and undirected(parent, first)
                and undirected(parent, second)
            ):
                return True
        return False

    changed = True
    while changed:
        changed = False
        for edge in tuple(result.edges):
            direction = _strict_direction(edge)
            if direction is None or strongly_protected(edge):
                continue
            replacement = Edge(edge.node1, edge.node2, Endpoint.TAIL, Endpoint.TAIL)
            attributes = graph.edge_attributes[graph._find_edge(edge)]
            result.remove_edge(edge)
            result.add_edge(
                replacement,
                **deepcopy(
                    {
                        key: value
                        for key, value in attributes.items()
                        if key not in {"beta", "control_points", "style"}
                    }
                ),
            )
            changed = True
    _copy_statuses(graph, result)
    return result


def equivalence_class(graph: Graph) -> PDAG:
    """Return the completed PDAG (CPDAG) of a directed DAG."""
    _require_type(graph, {GraphType.DAG}, "equivalence_class")
    return _equivalence_class_from_dag(graph)


def _same_structure(first: Graph, second: Graph) -> bool:
    return (
        tuple(node.identifier for node in first.nodes)
        == tuple(node.identifier for node in second.nodes)
        and set(first.edges) == set(second.edges)
    )


def equivalent_dags(
    graph: Graph, *, max_results: int | None = 100
) -> EnumerationResult[DAG]:
    """Enumerate DAGs in a Markov-equivalence class deterministically."""
    _require_type(graph, {GraphType.DAG, GraphType.PDAG}, "equivalent_dags")
    if isinstance(max_results, bool) or (
        max_results is not None and not isinstance(max_results, int)
    ):
        raise TypeError("max_results must be None or an integer")
    if max_results is not None and max_results < 0:
        raise ValueError("max_results must be non-negative")
    if max_results == 0:
        return EnumerationResult((), truncated=False)

    if graph.type is GraphType.DAG:
        edges = _directed_dag_edges(graph, "equivalent_dags")
        directions = {
            edge.nodes: direction
            for edge in edges
            if (direction := _strict_direction(edge)) is not None
        }
        required = _colliders(graph.nodes, _adjacency(edges), directions.values())
        assignments = _orientation_assignments(
            graph,
            preferred=directions,
            fix_directed=False,
            required_colliders=required,
        )
    else:
        _ordinary_edges(graph, "equivalent_dags")
        first_assignment = next(_orientation_assignments(graph), None)
        if first_assignment is None:
            raise InvalidGraphError("PDAG has no compatible acyclic orientation")
        extension = _build_dag(graph, first_assignment)
        completed_extension = _equivalence_class_from_dag(extension)
        if not _same_structure(graph, completed_extension):
            raise InvalidGraphError("PDAG is not a completed PDAG")
        assignments = _orientation_assignments(graph)

    limit = max_results
    items: list[DAG] = []
    truncated = False
    for assignment in assignments:
        if limit is not None and len(items) >= limit:
            truncated = True
            break
        items.append(_build_dag(graph, assignment))
    return EnumerationResult(items, truncated)
