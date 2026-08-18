import pytest

from pydagitty import (
    DAG,
    DIGRAPH,
    GRAPH,
    MAG,
    PAG,
    PDAG,
    Edge,
    Endpoint,
    Graph,
    GraphType,
    InvalidEdgeError,
    InvalidGraphError,
    Node,
    NodeSet,
    NodeStatus,
    PathExpression,
    UnknownNodeError,
    UnsupportedGraphTypeError,
    has_arrowhead,
    has_circle,
    has_tail,
    nodes,
)


def test_node_identity_validation_and_factory() -> None:
    alpha, beta = nodes("alpha beta")
    unicode_node = Node("café")

    assert alpha == Node("alpha")
    assert alpha != Node("Alpha")
    assert len({alpha, Node("alpha"), beta}) == 2
    assert str(unicode_node) == "café"
    assert nodes(["x", "y"]) == (Node("x"), Node("y"))
    with pytest.raises(ValueError):
        Node("")
    with pytest.raises(TypeError):
        Node(1)  # type: ignore[arg-type]


def test_edge_canonicalization_endpoint_helpers_and_self_edge_policy() -> None:
    a, b, c = nodes("A B C")
    forward = Edge(a, b, Endpoint.TAIL, Endpoint.ARROW)
    reversed_representation = Edge(b, a, Endpoint.ARROW, Endpoint.TAIL)

    assert forward == reversed_representation
    assert hash(forward) == hash(reversed_representation)
    assert forward.endpoint_at(a) is Endpoint.TAIL
    assert forward.other(a) == b
    assert has_tail(forward, a)
    assert has_arrowhead(forward, b)
    assert not has_circle(forward, a)
    with pytest.raises(ValueError):
        forward.endpoint_at(c)
    with pytest.raises(InvalidEdgeError):
        Edge(a, a)


@pytest.mark.parametrize(
    ("expression", "expected_nodes", "expected_endpoints"),
    [
        (
            lambda a, b, c, d: a >> b << c >> d,
            ("A", "B", "C", "D"),
            ((Endpoint.TAIL, Endpoint.ARROW), (Endpoint.ARROW, Endpoint.TAIL),
             (Endpoint.TAIL, Endpoint.ARROW)),
        ),
        (
            lambda a, b, c, d: a >> b @ c,
            ("A", "B", "C"),
            ((Endpoint.TAIL, Endpoint.ARROW), (Endpoint.ARROW, Endpoint.ARROW)),
        ),
        (
            lambda a, b, c, d: a @ b >> c,
            ("A", "B", "C"),
            ((Endpoint.ARROW, Endpoint.ARROW), (Endpoint.TAIL, Endpoint.ARROW)),
        ),
        (
            lambda a, b, c, d: a >> b - c,
            ("A", "B", "C"),
            ((Endpoint.TAIL, Endpoint.ARROW), (Endpoint.TAIL, Endpoint.TAIL)),
        ),
        (
            lambda a, b, c, d: a - b >> c,
            ("A", "B", "C"),
            ((Endpoint.TAIL, Endpoint.TAIL), (Endpoint.TAIL, Endpoint.ARROW)),
        ),
    ],
)
def test_operator_dsl_precedence_cases(expression, expected_nodes, expected_endpoints) -> None:
    a, b, c, d = nodes("A B C D")
    path = expression(a, b, c, d)

    assert isinstance(path, PathExpression)
    assert tuple(node.identifier for node in path.nodes) == expected_nodes
    assert path.endpoints == expected_endpoints
    assert path.first == a
    assert path.cursor == path.nodes[-1]


def test_path_joins_are_immutable_and_parenthesized_forms_normalize() -> None:
    a, b, c, d = nodes("A B C D")
    base = b @ c
    prepended = a >> base
    appended = base >> d

    assert base.nodes == (b, c)
    assert prepended == a >> (b @ c)
    assert prepended == (a >> b) @ c
    assert appended == (b @ c) >> d
    assert tuple(base.edges[0].endpoint_at(node) for node in (b, c)) == (
        Endpoint.ARROW,
        Endpoint.ARROW,
    )


def test_nodeset_has_set_equality_hashing_and_stable_iteration() -> None:
    a, b, c = nodes("A B C")
    ordered = NodeSet((b, a, b))

    assert tuple(ordered) == (b, a)
    assert ordered == {a, b}
    assert ordered != {a, c}
    assert hash(ordered) == hash(NodeSet((a, b)))


@pytest.mark.parametrize("left", tuple(Endpoint))
@pytest.mark.parametrize("right", tuple(Endpoint))
def test_pag_accepts_every_endpoint_combination(left: Endpoint, right: Endpoint) -> None:
    a, b = nodes("A B")
    graph = PAG(edges=[Edge(a, b, left, right)])

    assert graph.validate()
    assert graph.edges[0].endpoint_at(a) is left
    assert graph.edges[0].endpoint_at(b) is right


def test_declared_graph_types_enforce_endpoint_compatibility() -> None:
    a, b = nodes("A B")
    directed = Edge(a, b)
    bidirected = Edge(a, b, Endpoint.ARROW, Endpoint.ARROW)
    undirected = Edge(a, b, Endpoint.TAIL, Endpoint.TAIL)
    partial = Edge(a, b, Endpoint.CIRCLE, Endpoint.ARROW)

    assert len(DAG(edges=[directed, bidirected]).edges) == 2
    assert len(MAG(edges=[directed, bidirected, undirected]).edges) == 3
    assert len(PDAG(edges=[directed, bidirected, undirected]).edges) == 3
    assert GRAPH(edges=[undirected]).type is GraphType.GRAPH
    assert len(DIGRAPH(edges=[directed, bidirected, undirected, partial]).edges) == 4
    with pytest.raises(InvalidEdgeError):
        DAG(edges=[undirected])
    with pytest.raises(InvalidEdgeError):
        MAG(edges=[partial])
    with pytest.raises(InvalidEdgeError):
        GRAPH(edges=[directed])


def test_pag_relationship_queries_cover_six_public_edge_forms() -> None:
    x, child, spouse, neighbour, circles, circle_arrow, circle_tail = nodes(
        "X child spouse neighbour circles circle_arrow circle_tail"
    )
    graph = PAG(
        edges=[
            Edge(x, child, Endpoint.TAIL, Endpoint.ARROW),
            Edge(x, spouse, Endpoint.ARROW, Endpoint.ARROW),
            Edge(x, neighbour, Endpoint.TAIL, Endpoint.TAIL),
            Edge(x, circles, Endpoint.CIRCLE, Endpoint.CIRCLE),
            Edge(x, circle_arrow, Endpoint.CIRCLE, Endpoint.ARROW),
            Edge(x, circle_tail, Endpoint.CIRCLE, Endpoint.TAIL),
        ]
    )

    assert graph.children(x) == {child}
    assert graph.parents(child) == {x}
    assert graph.spouses(x) == {spouse}
    assert graph.neighbours(x) == {neighbour}
    assert graph.possible_children(x) == {child, neighbour, circles, circle_arrow}
    assert graph.possible_parents(x) == {neighbour, circles, circle_tail}
    assert graph.possible_neighbours(x) == {neighbour, circles, circle_tail}
    assert graph.adjacent_nodes(x) == {
        child,
        spouse,
        neighbour,
        circles,
        circle_arrow,
        circle_tail,
    }


def test_mutation_is_fluent_idempotent_and_allows_parallel_edge_types() -> None:
    a, b, c = nodes("A B C")
    directed = Edge(a, b)
    bidirected = Edge(a, b, Endpoint.ARROW, Endpoint.ARROW)
    graph = DAG()

    assert graph.add_edge(directed) is graph
    assert graph.add_edge(directed) is graph
    assert graph.add_edge(bidirected) is graph
    assert graph.append_path(b >> c) is graph
    assert graph.nodes == (a, b, c)
    assert len(graph.edges_between(a, b)) == 2
    assert graph.remove_edge(bidirected) is graph
    assert graph.edges_between(a, b) == (directed,)
    graph.remove_node(b)
    assert graph.nodes == (a, c)
    assert graph.edges == ()


def test_append_path_failure_is_atomic() -> None:
    a, b, c = nodes("A B C")
    graph = DAG()

    with pytest.raises(InvalidEdgeError):
        graph.append_path(a >> b - c)
    assert graph.nodes == ()
    assert graph.edges == ()
    with pytest.raises(TypeError):
        DAG(edges=[a >> b])  # type: ignore[list-item]


def test_reverse_edge_is_atomic_and_migrates_metadata() -> None:
    a, b = nodes("A B")
    edge = Edge(a, b)
    graph = DAG(edges=[edge])
    graph.set_edge_attributes(edge, beta=2.5, style={"width": 2})

    assert graph.reverse_edge(edge) is graph
    reversed_edge = Edge(b, a)
    assert graph.has_edge(reversed_edge)
    assert not graph.has_edge(edge)
    assert graph.edge_attributes[reversed_edge] == {"beta": 2.5, "style": {"width": 2}}
    with pytest.raises(InvalidEdgeError):
        graph.reverse_edge(edge)

    collision = DAG(edges=[edge, reversed_edge])
    before = collision.edges
    with pytest.raises(InvalidEdgeError):
        collision.reverse_edge(edge)
    assert collision.edges == before


def test_status_replacement_resolution_and_independence() -> None:
    a, b, c = nodes("A B C")
    graph = DAG(nodes=[a, b, c])

    assert graph.set_status(NodeStatus.EXPOSURE, (a, b)) is graph
    graph.exposures = Node("C")
    graph.outcomes = a
    graph.latents = b
    graph.adjusted_nodes = (a, c)
    graph.selected_nodes = c

    assert graph.exposures == {c}
    assert graph.outcomes == {a}
    assert graph.latents == {b}
    assert graph.adjusted_nodes == {a, c}
    assert graph.selected_nodes == {c}
    with pytest.raises(UnknownNodeError):
        graph.exposures = Node("missing")
    with pytest.raises(TypeError):
        graph.outcomes = "A"  # type: ignore[assignment]


def test_graph_owned_metadata_clone_and_induced_subgraph_are_independent() -> None:
    a, b, c = nodes("A B C")
    edge = Edge(a, b)
    graph = DAG(nodes=[c], edges=[edge])
    graph.add_node(Node("A"), eps=0.5, nested={"values": [1]})
    graph.set_edge_attributes(edge, beta=3, nested={"values": [2]})
    graph.exposures = a

    clone = graph.clone()
    clone.node_attributes[a]["nested"]["values"].append(9)
    clone.edge_attributes[edge]["nested"]["values"].append(9)
    clone.outcomes = b

    assert graph.node_attributes[a]["nested"] == {"values": [1]}
    assert graph.edge_attributes[edge]["nested"] == {"values": [2]}
    assert graph.outcomes == set()
    assert clone.exposures == {a}
    subgraph = graph.induced_subgraph((a, b))
    assert subgraph.nodes == (a, b)
    assert subgraph.edge_attributes[edge]["beta"] == 3


def test_public_metadata_views_cannot_corrupt_internal_storage() -> None:
    a, b = nodes("A B")
    edge = Edge(a, b)
    graph = DAG(edges=[edge])

    with pytest.raises(TypeError):
        graph.node_attributes[a]["eps"] = 1  # type: ignore[index]
    with pytest.raises(TypeError):
        graph.edge_attributes[edge]["beta"] = 1  # type: ignore[index]

    assert graph.clone().edges == (edge,)


def test_ancestry_cycles_topology_blanket_and_collider() -> None:
    a, b, c, d = nodes("A B C D")
    graph = DAG(paths=[a >> c, b >> c, c >> d])

    assert graph.parents(c) == {a, b}
    assert graph.ancestors(d) == {a, b, c, d}
    assert graph.ancestors(d, proper=True) == {a, b, c}
    assert graph.descendants(a) == {a, c, d}
    assert graph.exogenous_variables() == {a, b}
    assert graph.is_collider(a, c, b)
    assert graph.markov_blanket(c) == {a, b, d}
    assert graph.topological_ordering() == (a, b, c, d)
    assert graph.find_cycle() is None
    graph.append_path(d >> a)
    assert graph.find_cycle() == (a, c, d, a)
    assert not graph.is_acyclic()
    with pytest.raises(InvalidGraphError):
        graph.validate()
    with pytest.raises(InvalidGraphError):
        graph.topological_ordering()
    with pytest.raises(UnsupportedGraphTypeError):
        MAG(nodes=[a]).topological_ordering()


def test_generic_graph_constructor_and_fixed_concrete_type() -> None:
    generic = Graph(GraphType.PAG)

    assert generic.type is GraphType.PAG
    assert generic.graph_type is GraphType.PAG
    assert len(generic) == 0
    with pytest.raises(ValueError):
        DAG(GraphType.MAG)
