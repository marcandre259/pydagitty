import pytest

from pydagitty import (
    DAG,
    GRAPH,
    MAG,
    PDAG,
    Edge,
    Endpoint,
    GraphType,
    InvalidGraphError,
    NodeStatus,
    complete_dag,
    nodes,
)


def _directed_pairs(graph) -> set[tuple[str, str]]:
    pairs = set()
    for edge in graph.edges:
        if edge.endpoint_at(edge.node1) is Endpoint.TAIL:
            pairs.add((edge.node1.identifier, edge.node2.identifier))
        elif edge.endpoint_at(edge.node2) is Endpoint.TAIL:
            pairs.add((edge.node2.identifier, edge.node1.identifier))
    return pairs


def test_ancestor_graph_default_status_seeds_and_explicit_override() -> None:
    a, b, c, d, unrelated = nodes("A B C D U")
    graph = DAG(nodes=[unrelated], paths=[a >> b >> c >> d])
    graph.exposures = b
    graph.outcomes = d
    graph.adjusted_nodes = c

    default = graph.ancestor_graph()
    explicit = graph.ancestor_graph(c)

    assert default.nodes == (a, b, c, d)
    assert explicit.nodes == (a, b, c)
    assert graph.nodes == (unrelated, a, b, c, d)
    assert default.exposures == {b}
    assert default.outcomes == {d}


def test_canonicalization_replaces_bidirected_and_undirected_edges() -> None:
    a, b, c = nodes("A B C")
    directed = Edge(a, c)
    graph = MAG(
        nodes=[a, b, c],
        edges=[
            directed,
            Edge(a, b, Endpoint.ARROW, Endpoint.ARROW),
            Edge(b, c, Endpoint.TAIL, Endpoint.TAIL),
        ],
    )
    graph.set_edge_attributes(directed, beta=4)
    graph.exposures = a
    before_edges = graph.edges

    result = graph.canonicalize()
    canonical = result.graph

    assert canonical.type is GraphType.DAG
    assert tuple(node.identifier for node in result.latent_nodes) == ("L1",)
    assert tuple(node.identifier for node in result.selection_nodes) == ("S1",)
    assert canonical.latents == set(result.latent_nodes)
    assert canonical.selected_nodes == set(result.selection_nodes)
    assert canonical.parents(a) == set(result.latent_nodes)
    assert canonical.parents(b) == set(result.latent_nodes)
    assert canonical.children(b) == set(result.selection_nodes)
    assert canonical.children(c) == set(result.selection_nodes)
    assert canonical.edge_attributes[directed]["beta"] == 4
    assert canonical.exposures == {a}
    assert graph.edges == before_edges
    assert graph.latents == set()


def test_moralization_marries_coparents_and_is_idempotent_for_graph() -> None:
    a, b, c = nodes("A B C")
    dag = DAG(paths=[a >> c, b >> c])
    dag.outcomes = c

    moral = dag.moralize()
    twice = moral.moralize()

    assert moral.type is GraphType.GRAPH
    assert moral.adjacent(a, b)
    assert moral.adjacent(a, c)
    assert moral.adjacent(b, c)
    assert all(edge.left is edge.right is Endpoint.TAIL for edge in moral.edges)
    assert set(twice.edges) == set(moral.edges)
    assert twice.outcomes == {c}


def test_backdoor_and_indirect_graph_remove_only_target_edges() -> None:
    x, mediator, y, confounder = nodes("X M Y Z")
    direct = Edge(x, y)
    graph = DAG(paths=[x >> mediator >> y, confounder >> x, confounder >> y])
    graph.add_edge(direct, beta=7)
    graph.exposures = x
    graph.outcomes = y

    backdoor = graph.backdoor_graph()
    indirect = graph.indirect_graph()

    assert not backdoor.has_edge(Edge(x, mediator))
    assert not backdoor.has_edge(direct)
    assert backdoor.has_edge(Edge(confounder, x))
    assert indirect.has_edge(Edge(x, mediator))
    assert not indirect.has_edge(direct)
    assert graph.has_edge(Edge(x, mediator))
    assert graph.edge_attributes[direct]["beta"] == 7


def test_structural_and_measurement_parts_follow_latent_status() -> None:
    latent, construct, indicator, outcome = nodes("L A B C")
    graph = DAG(paths=[latent >> construct, latent >> indicator, construct >> outcome])
    graph.latents = (latent, construct)

    structural = graph.structural_part()
    measurement = graph.measurement_part()

    assert structural.nodes == (latent, construct)
    assert structural.edges == (Edge(latent, construct),)
    assert measurement.nodes == (latent, construct, indicator, outcome)
    assert set(measurement.edges) == {Edge(latent, indicator), Edge(construct, outcome)}
    assert measurement.latents == {latent, construct}


def test_latent_projection_creates_directed_and_bidirected_mag_edges() -> None:
    latent, a, b, c = nodes("L A B C")
    graph = DAG(paths=[latent >> a, latent >> b, a >> c])
    graph.latents = latent
    graph.outcomes = c

    projected = graph.to_mag()

    assert projected.type is GraphType.MAG
    assert projected.nodes == (a, b, c)
    assert projected.has_edge(Edge(a, b, Endpoint.ARROW, Endpoint.ARROW))
    assert projected.has_edge(Edge(a, c))
    assert projected.outcomes == {c}
    assert projected.latents == set()
    assert latent in graph.nodes


def test_to_mag_rejects_selection_projection() -> None:
    a, b = nodes("A B")
    graph = DAG(paths=[a >> b])
    graph.selected_nodes = a

    with pytest.raises(InvalidGraphError):
        graph.to_mag()


def test_orient_pdag_returns_acyclic_extension_and_preserves_metadata() -> None:
    a, b, c = nodes("A B C")
    undirected = Edge(a, b, Endpoint.TAIL, Endpoint.TAIL)
    graph = PDAG(edges=[undirected, Edge(b, c)])
    graph.set_edge_attributes(undirected, note={"source": "uncertain"})
    graph.set_status(NodeStatus.EXPOSURE, a)

    oriented = graph.orient_pdag()

    assert oriented.type is GraphType.DAG
    assert oriented.is_acyclic()
    assert len(oriented.edges) == 2
    assert oriented.exposures == {a}
    assert any(
        attrs == {"note": {"source": "uncertain"}}
        for attrs in oriented.edge_attributes.values()
    )
    assert graph.has_edge(undirected)


def test_equivalence_class_distinguishes_chain_and_unshielded_collider() -> None:
    a, b, c = nodes("A B C")
    chain = DAG(paths=[a >> b, b >> c])
    collider = DAG(paths=[a >> b, c >> b])

    chain_class = chain.equivalence_class()
    collider_class = collider.equivalence_class()

    assert all(edge.left is edge.right is Endpoint.TAIL for edge in chain_class.edges)
    assert set(collider_class.edges) == {Edge(a, b), Edge(c, b)}
    assert len(chain.equivalent_dags()) == 3
    assert len(collider.equivalent_dags()) == 1
    assert all(candidate.is_acyclic() for candidate in chain.equivalent_dags())
    assert all(
        set(candidate.equivalence_class().edges) == set(chain_class.edges)
        for candidate in chain.equivalent_dags()
    )


def test_equivalent_dag_limit_and_completed_pdag_validation() -> None:
    a, b, c = nodes("A B C")
    chain = DAG(paths=[a >> b, b >> c])

    limited = chain.equivalent_dags(max_results=2)

    assert len(limited) == 2
    assert limited.truncated
    assert chain.equivalent_dags(max_results=0).items == ()
    assert not chain.equivalent_dags(max_results=0).truncated
    assert len(chain.equivalence_class().equivalent_dags()) == 3
    incomplete = PDAG(paths=[a >> b, b - c])
    with pytest.raises(InvalidGraphError):
        incomplete.equivalent_dags()
    with pytest.raises(TypeError):
        chain.equivalent_dags(max_results=True)


def test_endpoint_changing_edges_drop_semantic_metadata() -> None:
    a, b = nodes("A B")
    directed = Edge(a, b)
    dag = DAG(edges=[directed])
    dag.set_edge_attributes(directed, beta=2, style="solid", note="kept")

    cpdag = dag.equivalence_class()

    assert cpdag.edge_attributes[cpdag.edges[0]] == {"note": "kept"}


def test_complete_dag_equivalence_class_is_fully_undirected() -> None:
    cpdag = complete_dag(6).equivalence_class()

    assert len(cpdag.edges) == 15
    assert all(edge.left is edge.right is Endpoint.TAIL for edge in cpdag.edges)


def test_skeleton_collapses_parallel_edges_without_source_mutation() -> None:
    a, b = nodes("A B")
    graph = DAG(edges=[Edge(a, b), Edge(a, b, Endpoint.ARROW, Endpoint.ARROW)])
    graph.latents = b

    skeleton = graph.skeleton()

    assert isinstance(skeleton, GRAPH)
    assert skeleton.edges == (Edge(a, b, Endpoint.TAIL, Endpoint.TAIL),)
    assert skeleton.latents == {b}
    assert len(graph.edges) == 2
