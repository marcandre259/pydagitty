"""Optional Graphviz rendering for PyDagitty graphs."""

from __future__ import annotations

from collections.abc import Mapping
from importlib import import_module
from typing import TYPE_CHECKING

from .model import Edge, Endpoint, Graph, Node, NodeStatus

if TYPE_CHECKING:
    import graphviz


_ENDPOINT_SHAPES = {
    Endpoint.TAIL: "none",
    Endpoint.ARROW: "normal",
    Endpoint.CIRCLE: "odot",
}
_ENDPOINT_ORDER = {
    Endpoint.TAIL: 0,
    Endpoint.CIRCLE: 1,
    Endpoint.ARROW: 2,
}
_GRAPH_ATTRIBUTES = {
    "bgcolor": "transparent",
    "outputorder": "edgesfirst",
    "rankdir": "TB",
}
_NODE_ATTRIBUTES = {
    "color": "#4a4a4a",
    "fillcolor": "#f3f3f3",
    "fontname": "Helvetica",
    "fontsize": "11",
    "margin": "0.10,0.06",
    "shape": "ellipse",
    "style": "filled",
}
_EDGE_ATTRIBUTES = {
    "arrowsize": "0.8",
    "color": "#333333",
    "penwidth": "1.2",
}


def _load_graphviz() -> object:
    try:
        return import_module("graphviz")
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Graphviz support requires the optional dependency; "
            "install it with `pip install 'pydagitty[viz]'`"
        ) from exc


def _ordered_edge(edge: Edge) -> tuple[Node, Node]:
    """Order incidences from less to more directed for useful dot ranks."""
    if _ENDPOINT_ORDER[edge.left] <= _ENDPOINT_ORDER[edge.right]:
        return edge.node1, edge.node2
    return edge.node2, edge.node1


def _status_attributes(graph: Graph, node: Node) -> dict[str, str]:
    exposure = node in graph.status(NodeStatus.EXPOSURE)
    outcome = node in graph.status(NodeStatus.OUTCOME)
    attributes: dict[str, str] = {}

    if exposure and outcome:
        attributes.update(fillcolor="#bed403:#00a2e0", gradientangle="90")
    elif exposure:
        attributes["fillcolor"] = "#bed403"
    elif outcome:
        attributes["fillcolor"] = "#00a2e0"
    if node in graph.status(NodeStatus.LATENT):
        attributes["style"] = "filled,dashed"
    if node in graph.status(NodeStatus.ADJUSTED):
        attributes["peripheries"] = "2"
    if node in graph.status(NodeStatus.SELECTED):
        attributes["shape"] = "box"
    return attributes


def to_graphviz(
    graph: Graph,
    *,
    name: str | None = None,
    engine: str = "dot",
    format: str = "svg",
    graph_attr: Mapping[str, str] | None = None,
    node_attr: Mapping[str, str] | None = None,
    edge_attr: Mapping[str, str] | None = None,
    show_statuses: bool = True,
) -> graphviz.Digraph:
    """Return a Graphviz graph preserving nodes, edges, and endpoint marks."""
    if not isinstance(graph, Graph):
        raise TypeError("graph must be a Graph")
    if not isinstance(show_statuses, bool):
        raise TypeError("show_statuses must be a bool")

    graphviz_module = _load_graphviz()
    dot = graphviz_module.Digraph(  # type: ignore[attr-defined]
        name=name or graph.type.value,
        engine=engine,
        format=format,
        strict=False,
        graph_attr={**_GRAPH_ATTRIBUTES, **dict(graph_attr or {})},
        node_attr={**_NODE_ATTRIBUTES, **dict(node_attr or {})},
        edge_attr={**_EDGE_ATTRIBUTES, **dict(edge_attr or {})},
    )
    identifiers = {node: f"n{index}" for index, node in enumerate(graph.nodes)}
    for node in graph.nodes:
        attributes = _status_attributes(graph, node) if show_statuses else {}
        label = graphviz_module.nohtml(  # type: ignore[attr-defined]
            graphviz_module.escape(node.identifier)  # type: ignore[attr-defined]
        )
        dot.node(identifiers[node], label=label, **attributes)

    for edge in graph.edges:
        tail, head = _ordered_edge(edge)
        tail_endpoint = edge.endpoint_at(tail)
        head_endpoint = edge.endpoint_at(head)
        attributes = {
            "arrowhead": _ENDPOINT_SHAPES[head_endpoint],
            "arrowtail": _ENDPOINT_SHAPES[tail_endpoint],
            "dir": "both",
        }
        if tail_endpoint is head_endpoint:
            attributes["constraint"] = "false"
        dot.edge(identifiers[tail], identifiers[head], **attributes)
    return dot
