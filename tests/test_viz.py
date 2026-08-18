import shutil

import pytest

from pydagitty import DAG, PAG, Edge, Endpoint, Node, nodes
from pydagitty.viz import to_graphviz


def test_all_endpoint_combinations_and_layout_order_are_preserved() -> None:
    endpoint_shapes = {
        Endpoint.TAIL: "none",
        Endpoint.CIRCLE: "odot",
        Endpoint.ARROW: "normal",
    }
    endpoint_order = {
        Endpoint.TAIL: 0,
        Endpoint.CIRCLE: 1,
        Endpoint.ARROW: 2,
    }
    a, b = nodes("A B")

    for left in Endpoint:
        for right in Endpoint:
            dot = PAG(edges=[Edge(a, b, left, right)]).to_graphviz()
            line = dot.body[-1]
            if endpoint_order[left] <= endpoint_order[right]:
                tail_id, head_id = "n0", "n1"
                tail_endpoint, head_endpoint = left, right
            else:
                tail_id, head_id = "n1", "n0"
                tail_endpoint, head_endpoint = right, left

            assert f"{tail_id} -> {head_id}" in line
            assert f"arrowtail={endpoint_shapes[tail_endpoint]}" in line
            assert f"arrowhead={endpoint_shapes[head_endpoint]}" in line
            assert ("constraint=false" in line) is (left is right)


def test_parallel_edges_and_isolated_nodes_are_retained() -> None:
    a, b, isolated = nodes("A B isolated")
    graph = DAG(
        nodes=[isolated],
        edges=[
            Edge(a, b),
            Edge(a, b, Endpoint.ARROW, Endpoint.ARROW),
        ],
    )

    dot = graph.to_graphviz()

    assert sum(" -> " in line for line in dot.body) == 2
    assert sum("label=" in line for line in dot.body) == 3
    assert "arrowtail=none" in dot.body[-2]
    assert "arrowtail=normal" in dot.body[-1]


def test_identifiers_are_safe_labels_on_opaque_node_ids() -> None:
    identifier = r'<A:B\N "quoted">'
    graph = DAG(nodes=[Node(identifier)])

    dot = graph.to_graphviz()

    assert dot.body[0].lstrip().startswith("n0 [")
    assert "A:B" in dot.body[0]
    assert "\\\\N" in dot.body[0]
    assert "n0:" not in dot.source
    assert "label=<" not in dot.source


def test_statuses_have_composable_styles_and_can_be_hidden() -> None:
    node = Node("A")
    graph = DAG(nodes=[node])
    graph.exposures = node
    graph.outcomes = node
    graph.latents = node
    graph.adjusted_nodes = node
    graph.selected_nodes = node

    styled = graph.to_graphviz().body[0]
    plain = graph.to_graphviz(show_statuses=False).body[0]

    assert 'fillcolor="#bed403:#00a2e0"' in styled
    assert "gradientangle=90" in styled
    assert "peripheries=2" in styled
    assert "shape=box" in styled
    assert 'style="filled,dashed"' in styled
    assert plain == "\tn0 [label=A]\n"


def test_configuration_and_module_function_do_not_mutate_source_graph() -> None:
    a, b = nodes("A B")
    graph = DAG(paths=[a >> b])
    before = repr(graph)

    dot = to_graphviz(
        graph,
        name="causal model",
        engine="neato",
        format="png",
        graph_attr={"rankdir": "LR"},
        node_attr={"fontname": "serif"},
        edge_attr={"color": "red"},
    )

    assert dot.name == "causal model"
    assert dot.engine == "neato"
    assert dot.format == "png"
    assert dot.graph_attr["rankdir"] == "LR"
    assert dot.node_attr["fontname"] == "serif"
    assert dot.edge_attr["color"] == "red"
    assert repr(graph) == before


@pytest.mark.skipif(shutil.which("dot") is None, reason="Graphviz executable is unavailable")
def test_graphviz_renders_svg() -> None:
    a, b = nodes("A B")

    svg = DAG(paths=[a >> b]).to_graphviz().pipe(format="svg")

    assert b"<svg" in svg
    assert b">A<" in svg
    assert b">B<" in svg


def test_visualization_input_validation_and_missing_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    graph = DAG()

    with pytest.raises(TypeError, match="graph must be a Graph"):
        to_graphviz(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="show_statuses must be a bool"):
        graph.to_graphviz(show_statuses=1)  # type: ignore[arg-type]

    def missing_graphviz(name: str) -> object:
        raise ModuleNotFoundError(name)

    monkeypatch.setattr("pydagitty.viz.import_module", missing_graphviz)
    with pytest.raises(ModuleNotFoundError, match=r"pydagitty\[viz\]"):
        graph.to_graphviz()
