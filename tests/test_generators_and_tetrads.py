import random

import pytest

from pydagitty import (
    DAG,
    MAG,
    Edge,
    Endpoint,
    Tetrad,
    UnsupportedGraphTypeError,
    complete_dag,
    nodes,
    random_dag,
)


def _directed_pairs(graph) -> set[tuple[str, str]]:
    result = set()
    for edge in graph.edges:
        parent = edge.node1 if edge.endpoint_at(edge.node1) is Endpoint.TAIL else edge.node2
        child = edge.other(parent)
        result.add((parent.identifier, child.identifier))
    return result


def test_complete_dag_uses_supplied_order_and_default_names() -> None:
    c, a, b = nodes("C A B")
    graph = complete_dag((c, a, b))
    generated = complete_dag(3)

    assert graph.nodes == (c, a, b)
    assert _directed_pairs(graph) == {("C", "A"), ("C", "B"), ("A", "B")}
    assert graph.topological_ordering() == (c, a, b)
    assert tuple(node.identifier for node in generated.nodes) == ("x1", "x2", "x3")
    assert len(generated.edges) == 3
    assert complete_dag(0).nodes == ()


def test_random_dag_probability_extremes_and_seed_reproducibility() -> None:
    empty = random_dag(4, 0, rng=random.Random(1))
    complete = random_dag(4, 1, rng=random.Random(1))
    first = random_dag(6, 0.35, rng=random.Random(42))
    second = random_dag(6, 0.35, rng=random.Random(42))

    assert empty.edges == ()
    assert len(complete.edges) == 6
    assert first.edges == second.edges
    assert first.nodes == second.nodes
    assert first.is_acyclic()
    assert all(
        first.nodes.index(parent) < first.nodes.index(child)
        for parent in first.nodes
        for child in first.children(parent)
    )


def test_generators_validate_inputs() -> None:
    a = nodes("A")[0]

    with pytest.raises(TypeError):
        complete_dag(True)
    with pytest.raises(ValueError):
        complete_dag(-1)
    with pytest.raises(ValueError):
        complete_dag((a, a))
    with pytest.raises(ValueError):
        random_dag(2, -0.1, rng=random.Random())
    with pytest.raises(ValueError):
        random_dag(2, 1.1, rng=random.Random())
    with pytest.raises(TypeError):
        random_dag(2, True, rng=random.Random())
    with pytest.raises(TypeError):
        random_dag(2, 0.5, rng=None)  # type: ignore[arg-type]


def test_tetrad_value_object_validation() -> None:
    a, b, c, d = nodes("A B C D")
    tetrad = Tetrad(a, b, c, d)

    assert tetrad.nodes == (a, b, c, d)
    assert tetrad == Tetrad(a, b, c, d)
    with pytest.raises(ValueError):
        Tetrad(a, a, c, d)


def test_single_factor_model_has_three_within_tetrads() -> None:
    latent, a, b, c, d = nodes("L A B C D")
    graph = DAG(paths=[latent >> a, latent >> b, latent >> c, latent >> d])
    graph.latents = latent

    all_tetrads = graph.vanishing_tetrads()
    within = graph.vanishing_tetrads(kind="within")

    assert len(all_tetrads) == 3
    assert all_tetrads.items == within.items
    assert graph.vanishing_tetrads(kind="between").items == ()
    assert graph.vanishing_tetrads(kind="epistemic").items == ()
    assert all(latent not in tetrad.nodes for tetrad in all_tetrads)
    assert all(len(set(tetrad.nodes)) == 4 for tetrad in all_tetrads)


def test_two_factor_model_has_one_between_tetrad() -> None:
    first_factor, second_factor, a, b, c, d = nodes("L1 L2 A B C D")
    graph = DAG(
        paths=[
            first_factor >> a,
            first_factor >> b,
            second_factor >> c,
            second_factor >> d,
        ]
    )
    graph.latents = (first_factor, second_factor)

    between = graph.vanishing_tetrads(kind="between")

    assert len(between) == 1
    assert set(between[0].nodes) == {a, b, c, d}
    assert graph.vanishing_tetrads(kind="within").items == ()
    assert graph.vanishing_tetrads(kind="epistemic").items == ()


def test_tetrad_limits_and_preconditions() -> None:
    latent, a, b, c, d = nodes("L A B C D")
    graph = DAG(paths=[latent >> a, latent >> b, latent >> c, latent >> d])
    graph.latents = latent

    limited = graph.vanishing_tetrads(max_results=2)

    assert len(limited) == 2
    assert limited.truncated
    assert graph.vanishing_tetrads(max_results=0).items == ()
    assert not graph.vanishing_tetrads(max_results=3).truncated
    with pytest.raises(ValueError):
        graph.vanishing_tetrads(kind="unknown")
    with pytest.raises(TypeError):
        graph.vanishing_tetrads(max_results=True)
    with pytest.raises(UnsupportedGraphTypeError):
        MAG(nodes=[a, b, c, d]).vanishing_tetrads()


def test_bidirected_shorthand_is_canonicalized_for_tetrads() -> None:
    a, b, c, d = nodes("A B C D")
    graph = DAG(
        edges=[
            Edge(a, b, Endpoint.ARROW, Endpoint.ARROW),
            Edge(a, c, Endpoint.ARROW, Endpoint.ARROW),
            Edge(a, d, Endpoint.ARROW, Endpoint.ARROW),
        ]
    )

    result = graph.vanishing_tetrads(max_results=1)

    assert len(result) <= 1
    assert all(set(tetrad.nodes) == {a, b, c, d} for tetrad in result)
