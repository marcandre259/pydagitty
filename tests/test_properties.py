import random

from hypothesis import given
from hypothesis import strategies as st

from pydagitty import DAG, Edge, Endpoint, Node, random_dag


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


@given(st.integers(min_value=0, max_value=8), st.integers())
def test_random_dag_topological_order_respects_every_edge(count: int, seed: int) -> None:
    graph = random_dag(count, p=0.5, rng=random.Random(seed))
    positions = {node: index for index, node in enumerate(graph.topological_ordering())}

    for edge in graph.edges:
        parent = edge.node1 if edge.left is Endpoint.TAIL else edge.node2
        child = edge.other(parent)
        assert positions[parent] < positions[child]


@given(st.integers(min_value=0, max_value=63), st.integers(min_value=0, max_value=7))
def test_dseparation_is_symmetric_for_small_dags(mask: int, conditioning: int) -> None:
    graph = DAG(nodes=[Node(name) for name in "ABCD"])
    pairs = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
    for bit, (parent, child) in enumerate(pairs):
        if mask & (1 << bit):
            graph.add_edge(Edge(graph.nodes[parent], graph.nodes[child]))

    given = tuple(graph.nodes[index + 1] for index in range(3) if conditioning & (1 << index))
    assert graph.dseparated(graph.nodes[0], graph.nodes[-1], given=given) == graph.dseparated(
        graph.nodes[-1], graph.nodes[0], given=given
    )
