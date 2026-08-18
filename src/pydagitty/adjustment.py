"""Adjustment-set validation and deterministic enumeration.

Informed by Dagitty's ``jslib/graph/GraphAnalyzer.js`` at commit ``7a657776``.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from itertools import combinations

from .exceptions import InvalidGraphError, UnsupportedGraphTypeError
from .model import Endpoint, EnumerationResult, Graph, GraphType, Node, NodeSet
from .traversal import minimal_separators

_TOTAL_TYPES = {GraphType.DAG, GraphType.MAG, GraphType.PDAG, GraphType.PAG}


def _limit(value: int | None) -> int | None:
    if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
        raise TypeError("max_results must be a non-negative integer or None")
    if value is not None and value < 0:
        raise ValueError("max_results must be non-negative")
    return value


def _bounded(items: Iterator[NodeSet], maximum: int | None) -> EnumerationResult[NodeSet]:
    if maximum == 0:
        return EnumerationResult((), truncated=False)
    result: list[NodeSet] = []
    for item in items:
        if maximum is not None and len(result) == maximum:
            return EnumerationResult(result, truncated=True)
        result.append(item)
    return EnumerationResult(result, truncated=False)


def _resolve_effect_nodes(
    graph: Graph,
    exposure: Node | Iterable[Node] | None,
    outcome: Node | Iterable[Node] | None,
) -> tuple[tuple[Node, ...], tuple[Node, ...]]:
    exposures = tuple(graph.exposures) if exposure is None else graph._resolve_nodes(exposure)
    outcomes = tuple(graph.outcomes) if outcome is None else graph._resolve_nodes(outcome)
    if not exposures or not outcomes:
        raise InvalidGraphError("exposure and outcome sets must be non-empty")

    exposure_set = set(exposures)
    outcome_set = set(outcomes)
    if exposure_set & outcome_set:
        raise InvalidGraphError("exposure and outcome sets must be disjoint")

    latent = set(graph.latents)
    adjusted = set(graph.adjusted_nodes)
    selected = set(graph.selected_nodes)
    if (exposure_set | outcome_set) & (latent | adjusted | selected):
        raise InvalidGraphError(
            "exposure and outcome nodes cannot be latent, adjusted, or selected"
        )
    if latent & (adjusted | selected):
        raise InvalidGraphError("adjusted and selected nodes cannot be latent")
    return exposures, outcomes


def _has_undirected_edge(graph: Graph) -> bool:
    return any(
        edge.endpoint_at(edge.node1) is Endpoint.TAIL
        and edge.endpoint_at(edge.node2) is Endpoint.TAIL
        for edge in graph.edges
    )


def _analysis_graph(graph: Graph, effect: str) -> Graph:
    if effect not in {"total", "direct"}:
        raise ValueError("effect must be 'total' or 'direct'")
    if effect == "direct":
        if graph.type is not GraphType.DAG:
            raise UnsupportedGraphTypeError(
                "direct-effect adjustment is supported only for DAG"
            )
        if graph.selected_nodes:
            raise InvalidGraphError("direct-effect adjustment does not support selected nodes")
        graph.validate()
        return graph

    if graph.type not in _TOTAL_TYPES:
        raise UnsupportedGraphTypeError(
            "total-effect adjustment supports DAG, MAG, PDAG, and PAG"
        )
    graph.validate()
    if graph.type in {GraphType.MAG, GraphType.PAG} and _has_undirected_edge(graph):
        raise InvalidGraphError(
            "adjustment for MAG and PAG requires a graph without undirected edges"
        )
    if graph.type is GraphType.PDAG:
        graph.orient_pdag()
    return graph


def _ordered(graph: Graph, members: Iterable[Node]) -> tuple[Node, ...]:
    selected = set(members)
    return tuple(node for node in graph.nodes if node in selected)


def _forbidden_total(
    graph: Graph, exposures: tuple[Node, ...], outcomes: tuple[Node, ...]
) -> set[Node]:
    exposure_set = set(exposures)
    backward = set(outcomes)
    queue = list(outcomes)
    while queue:
        current = queue.pop()
        if current in exposure_set:
            continue
        for previous in graph.possible_parents(current):
            if previous not in backward:
                backward.add(previous)
                queue.append(previous)
    possible_causal = (backward & set(graph.possible_descendants(exposures))) - exposure_set
    if not possible_causal:
        return set()
    return set(graph.possible_descendants(possible_causal))


def _criterion(
    graph: Graph,
    candidate: set[Node],
    exposures: tuple[Node, ...],
    outcomes: tuple[Node, ...],
    effect: str,
    separation_graph: Graph | None = None,
) -> bool:
    exposure_set = set(exposures)
    outcome_set = set(outcomes)
    latent = set(graph.latents)
    adjusted = set(graph.adjusted_nodes)
    selected = set(graph.selected_nodes)

    if not adjusted <= candidate:
        return False
    if candidate & (exposure_set | outcome_set | latent | selected):
        return False

    if effect == "total":
        if candidate & _forbidden_total(graph, exposures, outcomes):
            return False
        backdoor = separation_graph
        if backdoor is None:
            backdoor = graph.backdoor_graph(exposure=exposures, outcome=outcomes)
        given = _ordered(graph, candidate | selected)
        if not backdoor.dseparated(exposures, outcomes, given=given):
            return False
        if selected and not backdoor.dseparated(
            outcomes, tuple(selected)
        ):
            return False
        return True

    if candidate & set(graph.descendants(outcomes, proper=True)):
        return False
    if separation_graph is None:
        indirect_source = graph.clone()
        indirect_source.exposures = exposures
        indirect_source.outcomes = outcomes
        indirect = indirect_source.indirect_graph(exposure=exposures)
    else:
        indirect = separation_graph
    return indirect.dseparated(exposures, outcomes, given=_ordered(graph, candidate))


def is_adjustment_set(
    graph: Graph,
    nodes: Node | Iterable[Node],
    *,
    exposure: Node | Iterable[Node] | None = None,
    outcome: Node | Iterable[Node] | None = None,
    effect: str = "total",
) -> bool:
    """Return whether ``nodes`` satisfies the requested adjustment criterion."""
    if not isinstance(graph, Graph):
        raise TypeError("graph must be a Graph")
    analysis = _analysis_graph(graph, effect)
    exposures, outcomes = _resolve_effect_nodes(graph, exposure, outcome)
    candidate = set(graph._resolve_nodes(nodes))
    return _criterion(analysis, candidate, exposures, outcomes, effect)


def _candidate_nodes(
    graph: Graph,
    exposures: tuple[Node, ...],
    outcomes: tuple[Node, ...],
    effect: str,
) -> tuple[Node, ...]:
    unavailable = (
        set(exposures)
        | set(outcomes)
        | set(graph.latents)
        | set(graph.selected_nodes)
    )
    if effect == "total":
        unavailable |= _forbidden_total(graph, exposures, outcomes)
    else:
        unavailable |= set(graph.descendants(outcomes, proper=True))
    return tuple(node for node in graph.nodes if node not in unavailable)


def _subsets(
    candidates: tuple[Node, ...], mandatory: set[Node]
) -> Iterator[tuple[Node, ...]]:
    optional = tuple(node for node in candidates if node not in mandatory)
    ordered_mandatory = tuple(node for node in candidates if node in mandatory)
    for size in range(len(optional) + 1):
        for chosen in combinations(optional, size):
            members = set(ordered_mandatory) | set(chosen)
            yield tuple(node for node in candidates if node in members)


def _valid_sets(
    graph: Graph,
    separation_graph: Graph,
    candidates: tuple[Node, ...],
    mandatory: set[Node],
    exposures: tuple[Node, ...],
    outcomes: tuple[Node, ...],
    effect: str,
    minimal: bool,
) -> Iterator[NodeSet]:
    valid: list[frozenset[Node]] = []
    for chosen in _subsets(candidates, mandatory):
        member_set = set(chosen)
        if not _criterion(
            graph,
            member_set,
            exposures,
            outcomes,
            effect,
            separation_graph,
        ):
            continue
        frozen = frozenset(member_set)
        if minimal and any(previous < frozen for previous in valid):
            continue
        valid.append(frozen)
        yield NodeSet(chosen)


def _minimal_sets(
    graph: Graph,
    separation_graph: Graph,
    candidates: tuple[Node, ...],
    mandatory: set[Node],
    exposures: tuple[Node, ...],
    outcomes: tuple[Node, ...],
    effect: str,
    max_results: int | None,
) -> EnumerationResult[NodeSet]:
    selected = set(graph.selected_nodes) if effect == "total" else set()
    seeds = exposures + outcomes + tuple(mandatory | selected)
    relevant = separation_graph.ancestor_graph(seeds)
    moral = relevant.moralize()
    required = tuple(node for node in moral.nodes if node in mandatory | selected)
    allowed = set(candidates) | selected
    forbidden = tuple(
        node
        for node in moral.nodes
        if node not in allowed and node not in set(exposures) | set(outcomes)
    )
    separators = minimal_separators(
        moral,
        exposures,
        outcomes,
        mandatory=required,
        forbidden=forbidden,
        max_results=None,
    )

    def valid() -> Iterator[NodeSet]:
        for separator in separators:
            chosen = set(separator) - selected
            if _criterion(
                graph,
                chosen,
                exposures,
                outcomes,
                effect,
                separation_graph,
            ):
                yield NodeSet(node for node in graph.nodes if node in chosen)

    return _bounded(valid(), max_results)


def adjustment_sets(
    graph: Graph,
    *,
    exposure: Node | Iterable[Node] | None = None,
    outcome: Node | Iterable[Node] | None = None,
    effect: str = "total",
    mode: str = "minimal",
    max_results: int | None = None,
) -> EnumerationResult[NodeSet]:
    """Enumerate adjustment sets in cardinality and graph insertion order."""
    if not isinstance(graph, Graph):
        raise TypeError("graph must be a Graph")
    maximum = _limit(max_results)
    if mode not in {"minimal", "canonical", "all"}:
        raise ValueError("mode must be 'minimal', 'canonical', or 'all'")

    analysis = _analysis_graph(graph, effect)
    exposures, outcomes = _resolve_effect_nodes(graph, exposure, outcome)
    candidates = _candidate_nodes(analysis, exposures, outcomes, effect)
    mandatory = set(analysis.adjusted_nodes)
    if not mandatory <= set(candidates):
        return EnumerationResult((), truncated=False)
    if maximum == 0:
        return EnumerationResult((), truncated=False)
    if effect == "total":
        separation_graph = analysis.backdoor_graph(
            exposure=exposures, outcome=outcomes
        )
    else:
        indirect_source = analysis.clone()
        indirect_source.exposures = exposures
        indirect_source.outcomes = outcomes
        separation_graph = indirect_source.indirect_graph(exposure=exposures)

    if mode == "canonical":
        allowed = set(candidates)
        ancestral = set(analysis.possible_ancestors(exposures + outcomes))
        chosen = allowed & ancestral
        chosen |= mandatory

        def canonical() -> Iterator[NodeSet]:
            if _criterion(
                analysis,
                chosen,
                exposures,
                outcomes,
                effect,
                separation_graph,
            ):
                yield NodeSet(node for node in analysis.nodes if node in chosen)

        return _bounded(canonical(), maximum)

    if mode == "minimal":
        if analysis.type is GraphType.PAG:
            return _bounded(
                _valid_sets(
                    analysis,
                    separation_graph,
                    candidates,
                    mandatory,
                    exposures,
                    outcomes,
                    effect,
                    minimal=True,
                ),
                maximum,
            )
        return _minimal_sets(
            analysis,
            separation_graph,
            candidates,
            mandatory,
            exposures,
            outcomes,
            effect,
            maximum,
        )

    return _bounded(
        _valid_sets(
            analysis,
            separation_graph,
            candidates,
            mandatory,
            exposures,
            outcomes,
            effect,
            minimal=False,
        ),
        maximum,
    )
