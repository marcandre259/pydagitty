import pytest

from pydagitty import (
    DAG,
    GRAPH,
    PAG,
    PDAG,
    Edge,
    Endpoint,
    InvalidGraphError,
    Path,
    UnsupportedGraphTypeError,
    connected_components,
    is_path_open,
    minimal_separators,
    nodes,
    reachable_nodes,
)


def _node_sequences(paths) -> list[tuple[str, ...]]:
    return [tuple(node.identifier for node in path.nodes) for path in paths]


def test_chain_fork_and_collider_separation_rules() -> None:
    a, b, c, d = nodes("A B C D")
    chain = DAG(paths=[a >> b, b >> c])
    fork = DAG(paths=[b >> a, b >> c])
    collider = DAG(paths=[a >> b, c >> b, b >> d])

    assert chain.dconnected(a, c)
    assert chain.dseparated(a, c, given=b)
    assert fork.dconnected(a, c)
    assert fork.dseparated(a, c, given=b)
    assert collider.dseparated(a, c)
    assert collider.dconnected(a, c, given=b)
    assert collider.dconnected(a, c, given=d)
    assert not collider.dconnected((), c)
    assert collider.dseparated((), c)


def test_setwise_separation_is_symmetric() -> None:
    a, b, m, n, y, z = nodes("A B M N Y Z")
    graph = DAG(paths=[a >> m >> y, b >> n >> z])

    assert graph.dconnected((a, b), (y, z))
    assert graph.dconnected((y, z), (a, b))
    assert graph.dseparated((a, b), (y, z), given=(m, n))
    assert graph.dseparated((y, z), (a, b), given=(m, n))

    with pytest.raises(InvalidGraphError, match="must be disjoint"):
        graph.dseparated((a, b), (y, z), given=a)


def test_statuses_are_not_implicit_conditioning_for_separation() -> None:
    a, b, c = nodes("A B C")
    graph = DAG(paths=[a >> b, b >> c])
    graph.adjusted_nodes = b
    graph.selected_nodes = b

    assert graph.dconnected(a, c)
    assert graph.dseparated(a, c, given=b)
    assert reachable_nodes(graph, a) == {a, b, c}
    assert reachable_nodes(graph, (), given=b) == set()


def test_pag_separation_uses_documented_circle_as_tail_approximation() -> None:
    a, b, c = nodes("A B C")
    graph = PAG(
        edges=[
            Edge(a, b, Endpoint.CIRCLE, Endpoint.ARROW),
            Edge(c, b, Endpoint.CIRCLE, Endpoint.ARROW),
        ]
    )

    assert graph.dseparated(a, c)
    assert graph.dconnected(a, c, given=b)
    with pytest.raises(UnsupportedGraphTypeError):
        graph.paths(a, c)


def test_pdag_undirected_incidence_does_not_open_closed_collider() -> None:
    x, collider, y, neighbor = nodes("X C Y D")
    graph = PDAG(paths=[x >> collider, y >> collider, collider - neighbor])

    assert graph.dseparated(x, y)
    assert graph.dconnected(x, y, given=collider)


def test_paths_return_blocked_and_open_paths_unless_open_only() -> None:
    x, y, z, collider, descendant = nodes("X Y Z C D")
    graph = DAG(
        paths=[
            x >> y,
            z >> x,
            z >> y,
            x >> collider,
            y >> collider,
            collider >> descendant,
        ]
    )

    all_paths = graph.paths(x, y, given=z, max_results=None)
    by_nodes = {tuple(path.nodes): path for path in all_paths}

    assert _node_sequences(all_paths) == [("X", "Y"), ("X", "Z", "Y"), ("X", "C", "Y")]
    assert is_path_open(graph, by_nodes[(x, y)], given=z)
    assert not is_path_open(graph, by_nodes[(x, z, y)], given=z)
    assert not is_path_open(graph, by_nodes[(x, collider, y)], given=z)
    assert _node_sequences(graph.paths(x, y, given=z, open_only=True, max_results=None)) == [
        ("X", "Y")
    ]
    assert is_path_open(graph, by_nodes[(x, collider, y)], given=collider)
    assert is_path_open(graph, by_nodes[(x, collider, y)], given=descendant)


def test_directed_paths_and_parallel_edges_retain_exact_edge_choices() -> None:
    a, b, c = nodes("A B C")
    directed = Edge(a, b)
    bidirected = Edge(a, b, Endpoint.ARROW, Endpoint.ARROW)
    graph = DAG(edges=[directed, bidirected, Edge(b, c)])

    all_paths = graph.paths(a, c, max_results=None)
    directed_paths = graph.paths(a, c, directed=True, max_results=None)

    assert _node_sequences(all_paths) == [("A", "B", "C"), ("A", "B", "C")]
    assert all_paths[0].edges != all_paths[1].edges
    assert len(directed_paths) == 1
    assert directed_paths[0].edges == (directed, Edge(b, c))
    assert graph.paths(c, a, directed=True, max_results=None).items == ()


def test_path_limits_validation_and_truncation() -> None:
    a, b, c, d = nodes("A B C D")
    graph = DAG(paths=[a >> b, b >> d, a >> c, c >> d])

    zero = graph.paths(a, d, max_results=0)
    one = graph.paths(a, d, max_results=1)
    exact = graph.paths(a, d, max_results=2)

    assert zero.items == ()
    assert not zero.truncated
    assert len(one) == 1
    assert one.truncated
    assert len(exact) == 2
    assert not exact.truncated
    with pytest.raises(TypeError):
        graph.paths(a, d, max_results=True)
    with pytest.raises(ValueError):
        graph.paths(a, d, max_results=-1)


def test_path_iterator_uses_a_snapshot_taken_at_call_time() -> None:
    a, b, c, d = nodes("A B C D")
    graph = DAG(paths=[a >> b, b >> d])

    iterator = graph.iter_paths(a, d, max_results=None)
    graph.append_path(a >> c >> d)

    assert _node_sequences(iterator) == [("A", "B", "D")]
    assert _node_sequences(graph.paths(a, d, max_results=None)) == [
        ("A", "B", "D"),
        ("A", "C", "D"),
    ]


def test_path_value_object_validates_incidence() -> None:
    a, b, c = nodes("A B C")

    assert Path((a,), ()).nodes == (a,)
    with pytest.raises(ValueError):
        Path((a, b), ())
    with pytest.raises(ValueError):
        Path((a, b), (Edge(a, c),))


def test_connected_components_can_avoid_nodes() -> None:
    a, b, c, d, isolated = nodes("A B C D isolated")
    graph = GRAPH(nodes=[isolated], paths=[a - b, b - c, c - d])

    assert connected_components(graph) == ({isolated}, {a, b, c, d})
    assert connected_components(graph, avoiding=b) == ({isolated}, {a}, {c, d})
    with pytest.raises(UnsupportedGraphTypeError):
        connected_components(DAG(nodes=[a]))


def test_minimal_separators_support_mandatory_forbidden_and_limits() -> None:
    a, b, c, d = nodes("A B C D")
    graph = GRAPH(paths=[a - b, b - d, a - c, c - d])

    separators = minimal_separators(graph, a, d)

    assert separators.items == ({b, c},)
    assert not separators.truncated
    assert minimal_separators(graph, a, d, mandatory=b).items == ({b, c},)
    assert minimal_separators(graph, a, d, forbidden=b).items == ()
    assert minimal_separators(graph, a, d, max_results=0).items == ()
    with pytest.raises(TypeError):
        minimal_separators(graph, a, d, max_results=False)
