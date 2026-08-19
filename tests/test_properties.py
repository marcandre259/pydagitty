import random
from itertools import combinations

from hypothesis import given, settings
from hypothesis import strategies as st

from pydagitty import (
    DAG,
    GRAPH,
    MAG,
    Edge,
    Endpoint,
    Graph,
    GraphType,
    Node,
    minimal_separators,
    random_dag,
)


def _ordered_dag(count: int, mask: int, ordering: tuple[int, ...] | None = None) -> DAG:
    graph_nodes = tuple(Node(f"N{index}") for index in range(count))
    order = tuple(range(count)) if ordering is None else tuple(
        index for index in ordering if index < count
    )
    edges = (
        Edge(graph_nodes[parent], graph_nodes[child])
        for bit, (parent, child) in enumerate(combinations(order, 2))
        if mask & (1 << bit)
    )
    return DAG(nodes=graph_nodes, edges=edges)


def _assert_bounded(unlimited, bounded, limit: int) -> None:
    assert len(bounded) <= limit
    assert tuple(_enumeration_item_key(item) for item in bounded) == tuple(
        _enumeration_item_key(item) for item in unlimited[:limit]
    )
    if limit > 0:
        assert bounded.truncated is (len(unlimited) > limit)


def _enumeration_item_key(item):
    if isinstance(item, Graph):
        return tuple(node.identifier for node in item.nodes), item.edges
    return item


@settings(max_examples=20, derandomize=True)
@given(
    st.sampled_from(tuple(Endpoint)),
    st.sampled_from(tuple(Endpoint)),
)
def test_edge_identity_is_invariant_under_incidence_preserving_reversal(
    left: Endpoint,
    right: Endpoint,
) -> None:
    first = Node("A")
    second = Node("B")

    edge = Edge(first, second, left, right)
    reversed_edge = Edge(second, first, right, left)

    assert edge == reversed_edge
    assert hash(edge) == hash(reversed_edge)


@settings(max_examples=30, derandomize=True)
@given(st.integers(min_value=0, max_value=8), st.integers())
def test_random_dag_topological_order_respects_every_edge(count: int, seed: int) -> None:
    graph = random_dag(count, p=0.5, rng=random.Random(seed))
    positions = {node: index for index, node in enumerate(graph.topological_ordering())}

    for edge in graph.edges:
        parent = edge.node1 if edge.left is Endpoint.TAIL else edge.node2
        child = edge.other(parent)
        assert positions[parent] < positions[child]


@settings(max_examples=40, derandomize=True)
@given(st.integers(min_value=0, max_value=63), st.integers(min_value=0, max_value=3))
def test_dseparation_is_symmetric_for_small_dags(mask: int, conditioning: int) -> None:
    graph = DAG(nodes=[Node(name) for name in "ABCD"])
    pairs = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
    for bit, (parent, child) in enumerate(pairs):
        if mask & (1 << bit):
            graph.add_edge(Edge(graph.nodes[parent], graph.nodes[child]))

    given = tuple(graph.nodes[index + 1] for index in range(2) if conditioning & (1 << index))
    assert graph.dseparated(graph.nodes[0], graph.nodes[-1], given=given) == graph.dseparated(
        graph.nodes[-1], graph.nodes[0], given=given
    )


@settings(max_examples=30, derandomize=True)
@given(
    st.integers(min_value=1, max_value=5),
    st.integers(min_value=0, max_value=1023),
    st.integers(min_value=1, max_value=31),
    st.integers(),
)
def test_graph_copies_and_transformations_do_not_share_mutable_metadata(
    count: int,
    edge_mask: int,
    retained_mask: int,
    value: int,
) -> None:
    graph = _ordered_dag(count, edge_mask)
    for index, node in enumerate(graph.nodes):
        graph.set_node_attributes(node, payload={"values": [value, index]})
    for index, edge in enumerate(graph.edges):
        graph.set_edge_attributes(edge, payload={"values": [value, index]})

    retained = tuple(
        node for index, node in enumerate(graph.nodes) if retained_mask & (1 << index)
    )
    if not retained:
        retained = graph.nodes[:1]
    copies = [
        graph.clone(),
        graph.induced_subgraph(retained),
        graph.induced_subgraph(graph.nodes),
        graph.moralize(),
        graph.canonicalize().graph,
        graph.to_mag(),
    ]
    target = retained[0]

    for index, copied in enumerate(copies):
        marker = ("node mutation", index)
        copied.node_attributes[target]["payload"]["values"].append(marker)
        assert marker not in graph.node_attributes[target]["payload"]["values"]
        assert all(
            marker not in other.node_attributes[target]["payload"]["values"]
            for other in copies
            if other is not copied and target in other
        )

    if graph.edges:
        edge = graph.edges[0]
        edge_copies = [copies[0], copies[2], copies[4], copies[5]]
        for index, copied in enumerate(edge_copies):
            marker = ("edge mutation", index)
            copied.edge_attributes[edge]["payload"]["values"].append(marker)
            assert marker not in graph.edge_attributes[edge]["payload"]["values"]
            assert all(
                marker not in other.edge_attributes[edge]["payload"]["values"]
                for other in edge_copies
                if other is not copied
            )


@settings(max_examples=40, derandomize=True)
@given(
    st.integers(min_value=0, max_value=5),
    st.integers(min_value=0, max_value=1023),
)
def test_moralization_has_the_dag_moral_shape_and_is_idempotent(
    count: int,
    edge_mask: int,
) -> None:
    graph = _ordered_dag(count, edge_mask)
    expected_pairs = {frozenset(edge.nodes) for edge in graph.edges}
    for child in graph.nodes:
        expected_pairs.update(frozenset(pair) for pair in combinations(graph.parents(child), 2))

    moral = graph.moralize()
    repeated = moral.moralize()

    assert moral.type is GraphType.GRAPH
    assert moral.nodes == graph.nodes
    assert all(edge.left is edge.right is Endpoint.TAIL for edge in moral.edges)
    assert {frozenset(edge.nodes) for edge in moral.edges} == expected_pairs
    assert repeated.nodes == moral.nodes
    assert repeated.edges == moral.edges


@settings(max_examples=40, derandomize=True)
@given(
    st.integers(min_value=0, max_value=5),
    st.integers(min_value=0, max_value=4**10 - 1),
    st.integers(min_value=0, max_value=31),
    st.integers(min_value=0, max_value=31),
)
def test_canonicalization_restricts_endpoints_and_assigns_generated_roles(
    count: int,
    edge_encoding: int,
    latent_status_mask: int,
    selected_status_mask: int,
) -> None:
    graph_nodes = tuple(Node(f"N{index}") for index in range(count))
    edges = []
    bidirected = []
    undirected = []
    encoding = edge_encoding
    for first, second in combinations(range(count), 2):
        kind = encoding % 4
        encoding //= 4
        if kind == 0:
            continue
        if kind == 1:
            edge = Edge(graph_nodes[first], graph_nodes[second])
        elif kind == 2:
            edge = Edge(
                graph_nodes[first],
                graph_nodes[second],
                Endpoint.ARROW,
                Endpoint.ARROW,
            )
            bidirected.append(edge)
        else:
            edge = Edge(
                graph_nodes[first],
                graph_nodes[second],
                Endpoint.TAIL,
                Endpoint.TAIL,
            )
            undirected.append(edge)
        edges.append(edge)

    graph = MAG(nodes=graph_nodes, edges=edges)
    graph.latents = tuple(
        node for index, node in enumerate(graph.nodes) if latent_status_mask & (1 << index)
    )
    graph.selected_nodes = tuple(
        node for index, node in enumerate(graph.nodes) if selected_status_mask & (1 << index)
    )

    result = graph.canonicalize()
    canonical = result.graph

    assert canonical.type is GraphType.DAG
    assert all(
        {edge.left, edge.right} == {Endpoint.TAIL, Endpoint.ARROW}
        for edge in canonical.edges
    )
    assert len(result.latent_nodes) == len(bidirected)
    assert len(result.selection_nodes) == len(undirected)
    assert len(canonical.edges) == len(edges) + len(bidirected) + len(undirected)
    assert set(canonical.latents) == set(graph.latents) | set(result.latent_nodes)
    assert set(canonical.selected_nodes) == set(graph.selected_nodes) | set(
        result.selection_nodes
    )
    assert set(result.latent_nodes).isdisjoint(result.selection_nodes)
    assert set(result.latent_nodes) | set(result.selection_nodes) <= set(canonical.nodes) - set(
        graph.nodes
    )

    for source_edge, latent in zip(bidirected, result.latent_nodes):
        assert canonical.parents(latent) == set()
        assert canonical.children(latent) == set(source_edge.nodes)
        assert latent not in canonical.selected_nodes
    for source_edge, selected in zip(undirected, result.selection_nodes):
        assert canonical.parents(selected) == set(source_edge.nodes)
        assert canonical.children(selected) == set()
        assert selected not in canonical.latents


@settings(max_examples=35, derandomize=True)
@given(
    st.integers(min_value=2, max_value=5),
    st.integers(min_value=0, max_value=1023),
    st.permutations(tuple(range(5))),
    st.integers(min_value=0, max_value=31),
)
def test_enumerated_adjustment_sets_are_valid_and_minimal_sets_are_minimal(
    count: int,
    edge_mask: int,
    ordering: tuple[int, ...],
    mandatory_mask: int,
) -> None:
    graph = _ordered_dag(count, edge_mask, ordering)
    exposure, outcome = graph.nodes[:2]
    graph.exposures = exposure
    graph.outcomes = outcome
    graph.adjusted_nodes = tuple(
        node
        for index, node in enumerate(graph.nodes)
        if index >= 2 and mandatory_mask & (1 << index)
    )

    results = {
        mode: graph.adjustment_sets(mode=mode, max_results=None)
        for mode in ("minimal", "canonical", "all")
    }
    for result in results.values():
        assert all(graph.is_adjustment_set(candidate) for candidate in result)

    mandatory = set(graph.adjusted_nodes)
    for candidate in results["minimal"]:
        chosen = set(candidate)
        assert mandatory <= chosen
        for member in candidate:
            assert not graph.is_adjustment_set(chosen - {member})


@settings(max_examples=30, derandomize=True)
@given(
    st.integers(min_value=0, max_value=4),
    st.integers(min_value=0, max_value=63),
)
def test_equivalent_dags_are_acyclic_and_map_to_the_same_cpdag(
    count: int,
    edge_mask: int,
) -> None:
    graph = _ordered_dag(count, edge_mask)
    cpdag = graph.equivalence_class()
    equivalent = graph.equivalent_dags(max_results=None)

    assert len(equivalent) >= 1
    assert not equivalent.truncated
    for candidate in equivalent:
        assert candidate.is_acyclic()
        assert candidate.nodes == graph.nodes
        assert set(candidate.equivalence_class().edges) == set(cpdag.edges)


@settings(max_examples=35, derandomize=True)
@given(
    st.integers(min_value=1, max_value=5),
    st.integers(min_value=0, max_value=1023),
    st.permutations(tuple(range(5))),
    st.integers(min_value=0, max_value=31),
)
def test_latent_projection_excludes_explicitly_latent_source_nodes(
    count: int,
    edge_mask: int,
    ordering: tuple[int, ...],
    latent_mask: int,
) -> None:
    graph = _ordered_dag(count, edge_mask, ordering)
    graph.latents = tuple(
        node for index, node in enumerate(graph.nodes) if latent_mask & (1 << index)
    )

    projected = graph.to_mag()
    observed = set(graph.nodes) - set(graph.latents)

    assert projected.type is GraphType.MAG
    assert set(projected.nodes) == observed
    assert not set(projected.nodes) & set(graph.latents)
    assert all(set(edge.nodes) <= observed for edge in projected.edges)
    assert projected.latents == set()


@settings(max_examples=8, derandomize=True)
@given(st.integers(min_value=0, max_value=5))
def test_supported_enumerations_respect_result_limits(limit: int) -> None:
    start, first, second, third, finish = (Node(name) for name in "ABCDE")
    path_graph = DAG(
        edges=[
            Edge(start, first),
            Edge(first, finish),
            Edge(start, second),
            Edge(second, finish),
            Edge(start, third),
            Edge(third, finish),
        ]
    )
    _assert_bounded(
        path_graph.paths(start, finish, max_results=None),
        path_graph.paths(start, finish, max_results=limit),
        limit,
    )

    separator_graph = GRAPH(paths=[start - first - second - finish])
    _assert_bounded(
        minimal_separators(separator_graph, start, finish, max_results=None),
        minimal_separators(separator_graph, start, finish, max_results=limit),
        limit,
    )

    exposure, outcome, confounder, *irrelevant = (Node(name) for name in "XYZQRW")
    adjustment_graph = DAG(
        nodes=irrelevant,
        edges=[
            Edge(confounder, exposure),
            Edge(confounder, outcome),
            Edge(exposure, outcome),
        ],
    )
    adjustment_graph.exposures = exposure
    adjustment_graph.outcomes = outcome
    _assert_bounded(
        adjustment_graph.adjustment_sets(mode="all", max_results=None),
        adjustment_graph.adjustment_sets(mode="all", max_results=limit),
        limit,
    )

    chain = DAG(paths=[start >> first >> second >> finish])
    _assert_bounded(
        chain.equivalent_dags(max_results=None),
        chain.equivalent_dags(max_results=limit),
        limit,
    )

    implication_graph = DAG(nodes=[start, first, second, third])
    _assert_bounded(
        implication_graph.implied_conditional_independencies(
            mode="all_pairs", max_results=None
        ),
        implication_graph.implied_conditional_independencies(
            mode="all_pairs", max_results=limit
        ),
        limit,
    )

    latent = Node("L")
    indicators = tuple(Node(f"I{index}") for index in range(5))
    tetrad_graph = DAG(edges=[Edge(latent, indicator) for indicator in indicators])
    tetrad_graph.latents = latent
    _assert_bounded(
        tetrad_graph.vanishing_tetrads(max_results=None),
        tetrad_graph.vanishing_tetrads(max_results=limit),
        limit,
    )
