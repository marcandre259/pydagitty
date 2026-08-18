"""Core value objects and primitive graph operations for PyDagitty.

Informed by Dagitty's ``jslib/graph/Graph.js`` at commit ``7a657776``.
"""

from __future__ import annotations

import heapq
from collections.abc import Callable, Iterable, Iterator, Mapping
from collections.abc import Set as AbstractSet
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType, NotImplementedType
from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

from .exceptions import (
    InvalidEdgeError,
    InvalidGraphError,
    UnknownNodeError,
    UnsupportedGraphTypeError,
)

if TYPE_CHECKING:
    from .sem import Tetrad


class Endpoint(str, Enum):
    """An endpoint mark at one incidence of an edge."""

    TAIL = "tail"
    ARROW = "arrow"
    CIRCLE = "circle"


class GraphType(str, Enum):
    """Supported public and internal graph families."""

    DAG = "dag"
    MAG = "mag"
    PDAG = "pdag"
    PAG = "pag"
    GRAPH = "graph"
    DIGRAPH = "digraph"


class NodeStatus(str, Enum):
    """Graph-owned causal roles that may be assigned independently."""

    EXPOSURE = "exposure"
    OUTCOME = "outcome"
    LATENT = "latent"
    ADJUSTED = "adjusted"
    SELECTED = "selected"


@dataclass(frozen=True, slots=True)
class Node:
    """A node whose identity is its exact, case-sensitive identifier."""

    identifier: str

    def __post_init__(self) -> None:
        if not isinstance(self.identifier, str):
            raise TypeError("a node identifier must be a string")
        if not self.identifier:
            raise ValueError("a node identifier must not be empty")

    def __str__(self) -> str:
        return self.identifier

    def __rshift__(self, other: object) -> PathExpression | NotImplementedType:
        return _join_operands(self, other, Endpoint.TAIL, Endpoint.ARROW)

    def __rrshift__(self, other: object) -> PathExpression | NotImplementedType:
        return _join_operands(other, self, Endpoint.TAIL, Endpoint.ARROW)

    def __lshift__(self, other: object) -> PathExpression | NotImplementedType:
        return _join_operands(self, other, Endpoint.ARROW, Endpoint.TAIL)

    def __rlshift__(self, other: object) -> PathExpression | NotImplementedType:
        return _join_operands(other, self, Endpoint.ARROW, Endpoint.TAIL)

    def __matmul__(self, other: object) -> PathExpression | NotImplementedType:
        return _join_operands(self, other, Endpoint.ARROW, Endpoint.ARROW)

    def __rmatmul__(self, other: object) -> PathExpression | NotImplementedType:
        return _join_operands(other, self, Endpoint.ARROW, Endpoint.ARROW)

    def __sub__(self, other: object) -> PathExpression | NotImplementedType:
        return _join_operands(self, other, Endpoint.TAIL, Endpoint.TAIL)

    def __rsub__(self, other: object) -> PathExpression | NotImplementedType:
        return _join_operands(other, self, Endpoint.TAIL, Endpoint.TAIL)


@dataclass(frozen=True, slots=True, init=False)
class Edge:
    """An immutable edge canonicalized by endpoint-node identifier."""

    node1: Node
    node2: Node
    left: Endpoint
    right: Endpoint

    def __init__(
        self,
        node1: Node,
        node2: Node,
        left: Endpoint = Endpoint.TAIL,
        right: Endpoint = Endpoint.ARROW,
    ) -> None:
        if not isinstance(node1, Node) or not isinstance(node2, Node):
            raise TypeError("edge endpoints must be Node objects")
        try:
            left_endpoint = Endpoint(left)
            right_endpoint = Endpoint(right)
        except (TypeError, ValueError) as exc:
            raise TypeError("edge marks must be Endpoint values") from exc
        if node1 == node2:
            raise InvalidEdgeError("self-edges are not supported")
        if node2.identifier < node1.identifier:
            node1, node2 = node2, node1
            left_endpoint, right_endpoint = right_endpoint, left_endpoint
        object.__setattr__(self, "node1", node1)
        object.__setattr__(self, "node2", node2)
        object.__setattr__(self, "left", left_endpoint)
        object.__setattr__(self, "right", right_endpoint)

    @property
    def left_node(self) -> Node:
        return self.node1

    @property
    def right_node(self) -> Node:
        return self.node2

    @property
    def left_endpoint(self) -> Endpoint:
        return self.left

    @property
    def right_endpoint(self) -> Endpoint:
        return self.right

    @property
    def nodes(self) -> tuple[Node, Node]:
        return (self.node1, self.node2)

    def endpoint_at(self, node: Node) -> Endpoint:
        if not isinstance(node, Node):
            raise TypeError("node must be a Node")
        if node == self.node1:
            return self.left
        if node == self.node2:
            return self.right
        raise ValueError(f"node {node!r} is not incident to this edge")

    def other(self, node: Node) -> Node:
        if not isinstance(node, Node):
            raise TypeError("node must be a Node")
        if node == self.node1:
            return self.node2
        if node == self.node2:
            return self.node1
        raise ValueError(f"node {node!r} is not incident to this edge")

    def with_nodes(self, node1: Node, node2: Node) -> Edge:
        """Rebind equal endpoint nodes while preserving endpoint incidences."""
        if node1 == self.node1 and node2 == self.node2:
            return Edge(node1, node2, self.left, self.right)
        if node1 == self.node2 and node2 == self.node1:
            return Edge(node1, node2, self.right, self.left)
        raise InvalidEdgeError("replacement nodes do not match the edge")


EndpointPair = tuple[Endpoint, Endpoint]


@dataclass(frozen=True, slots=True)
class PathExpression:
    """An immutable syntactic path used by the construction DSL."""

    nodes: tuple[Node, ...]
    endpoints: tuple[EndpointPair, ...]

    def __post_init__(self) -> None:
        nodes = tuple(self.nodes)
        endpoint_pairs = tuple((Endpoint(left), Endpoint(right)) for left, right in self.endpoints)
        if not nodes:
            raise ValueError("a path expression must contain at least one node")
        if any(not isinstance(node, Node) for node in nodes):
            raise TypeError("path expression nodes must be Node objects")
        if len(endpoint_pairs) != len(nodes) - 1:
            raise ValueError("a path expression needs one endpoint pair per segment")
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "endpoints", endpoint_pairs)

    @property
    def cursor(self) -> Node:
        return self.nodes[-1]

    @property
    def first(self) -> Node:
        return self.nodes[0]

    @property
    def edges(self) -> tuple[Edge, ...]:
        return tuple(
            Edge(self.nodes[index], self.nodes[index + 1], left, right)
            for index, (left, right) in enumerate(self.endpoints)
        )

    def __rshift__(self, other: object) -> PathExpression | NotImplementedType:
        return _join_operands(self, other, Endpoint.TAIL, Endpoint.ARROW)

    def __rrshift__(self, other: object) -> PathExpression | NotImplementedType:
        return _join_operands(other, self, Endpoint.TAIL, Endpoint.ARROW)

    def __lshift__(self, other: object) -> PathExpression | NotImplementedType:
        return _join_operands(self, other, Endpoint.ARROW, Endpoint.TAIL)

    def __rlshift__(self, other: object) -> PathExpression | NotImplementedType:
        return _join_operands(other, self, Endpoint.ARROW, Endpoint.TAIL)

    def __matmul__(self, other: object) -> PathExpression | NotImplementedType:
        return _join_operands(self, other, Endpoint.ARROW, Endpoint.ARROW)

    def __rmatmul__(self, other: object) -> PathExpression | NotImplementedType:
        return _join_operands(other, self, Endpoint.ARROW, Endpoint.ARROW)

    def __sub__(self, other: object) -> PathExpression | NotImplementedType:
        return _join_operands(self, other, Endpoint.TAIL, Endpoint.TAIL)

    def __rsub__(self, other: object) -> PathExpression | NotImplementedType:
        return _join_operands(other, self, Endpoint.TAIL, Endpoint.TAIL)


def _as_path_expression(value: object) -> PathExpression | None:
    if isinstance(value, PathExpression):
        return value
    if isinstance(value, Node):
        return PathExpression((value,), ())
    return None


def _join_operands(
    left: object,
    right: object,
    left_endpoint: Endpoint,
    right_endpoint: Endpoint,
) -> PathExpression | NotImplementedType:
    left_path = _as_path_expression(left)
    right_path = _as_path_expression(right)
    if left_path is None or right_path is None:
        return NotImplemented  # type: ignore[no-any-return]
    return PathExpression(
        left_path.nodes + right_path.nodes,
        left_path.endpoints + ((left_endpoint, right_endpoint),) + right_path.endpoints,
    )


class NodeSet(AbstractSet[Node]):
    """An immutable set with deterministic, caller-provided iteration order."""

    __slots__ = ("_items", "_set")

    def __init__(self, nodes: Iterable[Node] = ()) -> None:
        items: list[Node] = []
        seen: set[Node] = set()
        for node in nodes:
            if not isinstance(node, Node):
                raise TypeError("NodeSet members must be Node objects")
            if node not in seen:
                seen.add(node)
                items.append(node)
        self._items = tuple(items)
        self._set = frozenset(seen)

    def __contains__(self, value: object) -> bool:
        return value in self._set

    def __iter__(self) -> Iterator[Node]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __hash__(self) -> int:
        return hash(self._set)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, AbstractSet):
            return self._set == frozenset(other)
        return False

    def __repr__(self) -> str:
        return f"NodeSet({self._items!r})"

    def as_frozenset(self) -> frozenset[Node]:
        return self._set


T = TypeVar("T")


@dataclass(frozen=True, slots=True, init=False)
class EnumerationResult(Generic[T]):
    """A bounded deterministic enumeration and its truncation state."""

    items: tuple[T, ...]
    truncated: bool

    def __init__(self, items: Iterable[T] = (), truncated: bool = False) -> None:
        if not isinstance(truncated, bool):
            raise TypeError("truncated must be a bool")
        object.__setattr__(self, "items", tuple(items))
        object.__setattr__(self, "truncated", truncated)

    def __iter__(self) -> Iterator[T]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    @overload
    def __getitem__(self, index: int) -> T: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[T, ...]: ...

    def __getitem__(self, index: int | slice) -> T | tuple[T, ...]:
        return self.items[index]


@dataclass(frozen=True, slots=True)
class Path:
    """A concrete path retaining exact choices among parallel edges."""

    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]

    def __post_init__(self) -> None:
        nodes = tuple(self.nodes)
        edges = tuple(self.edges)
        if not nodes:
            raise ValueError("a path must contain at least one node")
        if any(not isinstance(node, Node) for node in nodes):
            raise TypeError("path nodes must be Node objects")
        if any(not isinstance(edge, Edge) for edge in edges):
            raise TypeError("path edges must be Edge objects")
        if len(edges) != len(nodes) - 1:
            raise ValueError("a path needs one edge per node pair")
        for index, edge in enumerate(edges):
            if {nodes[index], nodes[index + 1]} != {edge.node1, edge.node2}:
                raise ValueError("path edge is not incident to its adjacent nodes")
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)


@dataclass(frozen=True, slots=True, init=False)
class ConditionalIndependence:
    """A setwise conditional-independence statement."""

    left: NodeSet
    right: NodeSet
    given: NodeSet

    def __init__(
        self,
        left: Node | Iterable[Node],
        right: Node | Iterable[Node],
        given: Node | Iterable[Node] = (),
    ) -> None:
        object.__setattr__(self, "left", _coerce_node_set(left))
        object.__setattr__(self, "right", _coerce_node_set(right))
        object.__setattr__(self, "given", _coerce_node_set(given))


@dataclass(frozen=True, slots=True, init=False)
class Instrument:
    """A graphical instrument and its conditioning set."""

    node: Node
    conditioning_set: NodeSet

    def __init__(self, node: Node, conditioning_set: Node | Iterable[Node] = ()) -> None:
        if not isinstance(node, Node):
            raise TypeError("instrument node must be a Node")
        object.__setattr__(self, "node", node)
        object.__setattr__(self, "conditioning_set", _coerce_node_set(conditioning_set))

    @property
    def given(self) -> NodeSet:
        return self.conditioning_set


def _coerce_node_set(value: Node | Iterable[Node]) -> NodeSet:
    if isinstance(value, Node):
        return NodeSet((value,))
    if isinstance(value, str):
        raise TypeError("bare strings are not node collections")
    return NodeSet(value)


def has_arrowhead(edge: Edge, node: Node) -> bool:
    return edge.endpoint_at(node) is Endpoint.ARROW


def has_tail(edge: Edge, node: Node) -> bool:
    return edge.endpoint_at(node) is Endpoint.TAIL


def has_circle(edge: Edge, node: Node) -> bool:
    return edge.endpoint_at(node) is Endpoint.CIRCLE


def is_parent_edge(edge: Edge, parent: Node, child: Node) -> bool:
    return (
        parent != child
        and edge.endpoint_at(parent) is Endpoint.TAIL
        and edge.endpoint_at(child) is Endpoint.ARROW
    )


def is_spouse_edge(edge: Edge, first: Node, second: Node) -> bool:
    return (
        first != second
        and edge.endpoint_at(first) is Endpoint.ARROW
        and edge.endpoint_at(second) is Endpoint.ARROW
    )


def is_neighbour_edge(edge: Edge, first: Node, second: Node) -> bool:
    return (
        first != second
        and edge.endpoint_at(first) is Endpoint.TAIL
        and edge.endpoint_at(second) is Endpoint.TAIL
    )


def is_possible_parent_edge(edge: Edge, parent: Node, child: Node) -> bool:
    """Return whether a partial edge can be oriented parent -> child."""
    parent_mark = edge.endpoint_at(parent)
    child_mark = edge.endpoint_at(child)
    return parent != child and parent_mark is not Endpoint.ARROW and (
        child_mark is not Endpoint.TAIL or parent_mark is Endpoint.TAIL
    )


def is_possible_neighbour_edge(edge: Edge, first: Node, second: Node) -> bool:
    """Return whether an edge can be oriented without an arrowhead at either node."""
    return (
        first != second
        and edge.endpoint_at(first) is not Endpoint.ARROW
        and edge.endpoint_at(second) is not Endpoint.ARROW
    )


_ALLOWED_ENDPOINTS: dict[GraphType, frozenset[tuple[Endpoint, Endpoint]]] = {
    GraphType.DAG: frozenset(
        {
            (Endpoint.TAIL, Endpoint.ARROW),
            (Endpoint.ARROW, Endpoint.TAIL),
            (Endpoint.ARROW, Endpoint.ARROW),
        }
    ),
    GraphType.MAG: frozenset(
        {
            (Endpoint.TAIL, Endpoint.ARROW),
            (Endpoint.ARROW, Endpoint.TAIL),
            (Endpoint.ARROW, Endpoint.ARROW),
            (Endpoint.TAIL, Endpoint.TAIL),
        }
    ),
    GraphType.PDAG: frozenset(
        {
            (Endpoint.TAIL, Endpoint.ARROW),
            (Endpoint.ARROW, Endpoint.TAIL),
            (Endpoint.ARROW, Endpoint.ARROW),
            (Endpoint.TAIL, Endpoint.TAIL),
        }
    ),
    GraphType.PAG: frozenset((left, right) for left in Endpoint for right in Endpoint),
    GraphType.GRAPH: frozenset({(Endpoint.TAIL, Endpoint.TAIL)}),
    GraphType.DIGRAPH: frozenset((left, right) for left in Endpoint for right in Endpoint),
}


class Graph:
    """Mutable, insertion-ordered graph with immutable node and edge identity."""

    GRAPH_TYPE = GraphType.DIGRAPH

    def __init__(
        self,
        graph_type: GraphType | None = None,
        *,
        nodes: Iterable[Node] = (),
        edges: Iterable[Edge] = (),
        paths: Iterable[PathExpression] = (),
    ) -> None:
        declared_type = self.GRAPH_TYPE if graph_type is None else GraphType(graph_type)
        if type(self) is not Graph and declared_type is not self.GRAPH_TYPE:
            raise ValueError("a concrete graph class has a fixed graph type")
        self._type = declared_type
        self._nodes: dict[str, Node] = {}
        self._edges: dict[Edge, Edge] = {}
        self._incident: dict[str, dict[Edge, None]] = {}
        self._node_attributes: dict[Node, dict[str, Any]] = {}
        self._edge_attributes: dict[Edge, dict[str, Any]] = {}
        self._statuses: dict[NodeStatus, dict[Node, None]] = {
            status: {} for status in NodeStatus
        }

        initial_nodes = tuple(nodes)
        initial_edges = tuple(edges)
        initial_paths = tuple(paths)
        for node in initial_nodes:
            self.add_node(node)
        path_edges: list[Edge] = list(initial_edges)
        path_nodes: list[Node] = []
        for path in initial_paths:
            if not isinstance(path, PathExpression):
                raise TypeError("paths must contain PathExpression objects")
            path_nodes.extend(path.nodes)
            path_edges.extend(path.edges)
        self._add_edges_atomic(path_edges, preferred_nodes=path_nodes)

    @property
    def type(self) -> GraphType:
        return self._type

    @property
    def graph_type(self) -> GraphType:
        return self._type

    @property
    def nodes(self) -> tuple[Node, ...]:
        return tuple(self._nodes.values())

    @property
    def edges(self) -> tuple[Edge, ...]:
        return tuple(self._edges.values())

    @property
    def node_attributes(self) -> Mapping[Node, Mapping[str, Any]]:
        return MappingProxyType(
            {
                node: MappingProxyType(attributes)
                for node, attributes in self._node_attributes.items()
            }
        )

    @property
    def edge_attributes(self) -> Mapping[Edge, Mapping[str, Any]]:
        return MappingProxyType(
            {
                edge: MappingProxyType(attributes)
                for edge, attributes in self._edge_attributes.items()
            }
        )

    def __len__(self) -> int:
        return len(self._nodes)

    def __iter__(self) -> Iterator[Node]:
        return iter(self._nodes.values())

    def __contains__(self, node: object) -> bool:
        return isinstance(node, Node) and node.identifier in self._nodes

    def __repr__(self) -> str:
        return f"{type(self).__name__}(nodes={list(self.nodes)!r}, edges={list(self.edges)!r})"

    def node(self, identifier: str) -> Node:
        if not isinstance(identifier, str):
            raise TypeError("identifier must be a string")
        try:
            return self._nodes[identifier]
        except KeyError as exc:
            raise UnknownNodeError(f"unknown node: {identifier!r}") from exc

    def _resolve_node(self, node: Node) -> Node:
        if not isinstance(node, Node):
            raise TypeError("expected a Node")
        try:
            return self._nodes[node.identifier]
        except KeyError as exc:
            raise UnknownNodeError(f"unknown node: {node.identifier!r}") from exc

    def _resolve_nodes(self, value: Node | Iterable[Node]) -> tuple[Node, ...]:
        candidates: tuple[Node, ...]
        if isinstance(value, Node):
            candidates = (value,)
        else:
            if isinstance(value, str):
                raise TypeError("bare strings are not node collections")
            try:
                candidates = tuple(value)
            except TypeError as exc:
                raise TypeError("expected a Node or iterable of Node objects") from exc
        resolved: set[Node] = set()
        for node in candidates:
            resolved.add(self._resolve_node(node))
        return tuple(node for node in self._nodes.values() if node in resolved)

    def _normalize_edge(self, edge: Edge, registry: dict[str, Node]) -> Edge:
        if not isinstance(edge, Edge):
            raise TypeError("edges must be Edge objects")
        first = registry.get(edge.node1.identifier, edge.node1)
        second = registry.get(edge.node2.identifier, edge.node2)
        normalized = Edge(first, second, edge.left, edge.right)
        if (normalized.left, normalized.right) not in _ALLOWED_ENDPOINTS[self._type]:
            raise InvalidEdgeError(
                f"edge endpoints {normalized.left.value}-{normalized.right.value} "
                f"are not allowed in {self._type.value}"
            )
        return normalized

    def _add_edges_atomic(
        self,
        edges: Iterable[Edge],
        *,
        preferred_nodes: Iterable[Node] = (),
    ) -> None:
        candidates = tuple(edges)
        registry = dict(self._nodes)
        for node in preferred_nodes:
            if not isinstance(node, Node):
                raise TypeError("path expression nodes must be Node objects")
            registry.setdefault(node.identifier, node)
        normalized: list[Edge] = []
        for edge in candidates:
            candidate = self._normalize_edge(edge, registry)
            for node in candidate.nodes:
                registry.setdefault(node.identifier, node)
            normalized.append(self._normalize_edge(edge, registry))
        for identifier, node in registry.items():
            if identifier not in self._nodes:
                self.add_node(node)
        for edge in normalized:
            owned = Edge(
                self._nodes[edge.node1.identifier],
                self._nodes[edge.node2.identifier],
                edge.left,
                edge.right,
            )
            if owned in self._edges:
                continue
            self._edges[owned] = owned
            self._incident[owned.node1.identifier][owned] = None
            self._incident[owned.node2.identifier][owned] = None
            self._edge_attributes[owned] = {}

    def add_node(self, node: Node, **attributes: Any) -> Graph:
        if not isinstance(node, Node):
            raise TypeError("node must be a Node")
        owned = self._nodes.get(node.identifier)
        if owned is None:
            owned = node
            self._nodes[node.identifier] = owned
            self._incident[node.identifier] = {}
            self._node_attributes[owned] = {}
        if attributes:
            self._node_attributes[owned].update(attributes)
        return self

    def add_edge(self, edge: Edge, **attributes: Any) -> Graph:
        self._add_edges_atomic((edge,))
        owned = self._find_edge(edge)
        if attributes:
            self._edge_attributes[owned].update(attributes)
        return self

    def append_path(self, *paths: PathExpression) -> Graph:
        edge_batch: list[Edge] = []
        path_nodes: list[Node] = []
        for path in paths:
            if not isinstance(path, PathExpression):
                raise TypeError("append_path accepts only PathExpression objects")
            path_nodes.extend(path.nodes)
            edge_batch.extend(path.edges)
        self._add_edges_atomic(edge_batch, preferred_nodes=path_nodes)
        return self

    def _find_edge(self, edge: Edge) -> Edge:
        if not isinstance(edge, Edge):
            raise TypeError("edge must be an Edge")
        if edge.node1.identifier not in self._nodes or edge.node2.identifier not in self._nodes:
            raise InvalidEdgeError("edge has an endpoint not owned by this graph")
        normalized = Edge(
            self._nodes[edge.node1.identifier],
            self._nodes[edge.node2.identifier],
            edge.left,
            edge.right,
        )
        try:
            return self._edges[normalized]
        except KeyError as exc:
            raise InvalidEdgeError("edge is not present in this graph") from exc

    def has_edge(self, edge: Edge) -> bool:
        try:
            self._find_edge(edge)
        except InvalidEdgeError:
            return False
        return True

    def remove_edge(self, edge: Edge) -> Graph:
        owned = self._find_edge(edge)
        del self._edges[owned]
        del self._incident[owned.node1.identifier][owned]
        del self._incident[owned.node2.identifier][owned]
        self._edge_attributes.pop(owned, None)
        return self

    def remove_node(self, node: Node) -> Graph:
        owned = self._resolve_node(node)
        for edge in tuple(self._incident[owned.identifier]):
            self.remove_edge(edge)
        del self._incident[owned.identifier]
        del self._nodes[owned.identifier]
        self._node_attributes.pop(owned, None)
        for members in self._statuses.values():
            members.pop(owned, None)
        return self

    def reverse_edge(self, edge: Edge) -> Graph:
        owned = self._find_edge(edge)
        if {owned.left, owned.right} != {Endpoint.TAIL, Endpoint.ARROW}:
            raise InvalidEdgeError("only a strict directed edge can be reversed")
        parent = owned.node1 if owned.left is Endpoint.TAIL else owned.node2
        child = owned.other(parent)
        reversed_edge = Edge(child, parent, Endpoint.TAIL, Endpoint.ARROW)
        if reversed_edge in self._edges:
            raise InvalidEdgeError("the reversed edge already exists")
        attributes = self._edge_attributes[owned]
        self.remove_edge(owned)
        self._edges[reversed_edge] = reversed_edge
        self._incident[reversed_edge.node1.identifier][reversed_edge] = None
        self._incident[reversed_edge.node2.identifier][reversed_edge] = None
        self._edge_attributes[reversed_edge] = attributes
        return self

    def set_node_attributes(self, node: Node, **attributes: Any) -> Graph:
        owned = self._resolve_node(node)
        self._node_attributes[owned].update(attributes)
        return self

    def set_edge_attributes(self, edge: Edge, **attributes: Any) -> Graph:
        owned = self._find_edge(edge)
        self._edge_attributes[owned].update(attributes)
        return self

    def set_status(self, status: NodeStatus, nodes: Node | Iterable[Node]) -> Graph:
        if not isinstance(status, NodeStatus):
            raise TypeError("status must be a NodeStatus")
        resolved = self._resolve_nodes(nodes)
        self._statuses[status] = {node: None for node in resolved}
        return self

    def status(self, status: NodeStatus) -> NodeSet:
        if not isinstance(status, NodeStatus):
            raise TypeError("status must be a NodeStatus")
        return NodeSet(self._statuses[status])

    @property
    def exposures(self) -> NodeSet:
        return self.status(NodeStatus.EXPOSURE)

    @exposures.setter
    def exposures(self, nodes: Node | Iterable[Node]) -> None:
        self.set_status(NodeStatus.EXPOSURE, nodes)

    @property
    def outcomes(self) -> NodeSet:
        return self.status(NodeStatus.OUTCOME)

    @outcomes.setter
    def outcomes(self, nodes: Node | Iterable[Node]) -> None:
        self.set_status(NodeStatus.OUTCOME, nodes)

    @property
    def latents(self) -> NodeSet:
        return self.status(NodeStatus.LATENT)

    @latents.setter
    def latents(self, nodes: Node | Iterable[Node]) -> None:
        self.set_status(NodeStatus.LATENT, nodes)

    @property
    def adjusted_nodes(self) -> NodeSet:
        return self.status(NodeStatus.ADJUSTED)

    @adjusted_nodes.setter
    def adjusted_nodes(self, nodes: Node | Iterable[Node]) -> None:
        self.set_status(NodeStatus.ADJUSTED, nodes)

    @property
    def selected_nodes(self) -> NodeSet:
        return self.status(NodeStatus.SELECTED)

    @selected_nodes.setter
    def selected_nodes(self, nodes: Node | Iterable[Node]) -> None:
        self.set_status(NodeStatus.SELECTED, nodes)

    def incident_edges(self, nodes: Node | Iterable[Node]) -> tuple[Edge, ...]:
        resolved = self._resolve_nodes(nodes)
        selected: set[Edge] = set()
        for node in resolved:
            selected.update(self._incident[node.identifier])
        return tuple(edge for edge in self._edges if edge in selected)

    def edges_between(self, first: Node, second: Node) -> tuple[Edge, ...]:
        left = self._resolve_node(first)
        right = self._resolve_node(second)
        if left == right:
            return ()
        return tuple(
            edge for edge in self._incident[left.identifier] if right in edge.nodes
        )

    def _related(
        self,
        nodes: Node | Iterable[Node],
        predicate: Callable[[Edge, Node, Node], bool],
    ) -> NodeSet:
        sources = self._resolve_nodes(nodes)
        found: set[Node] = set()
        for source in sources:
            for edge in self._incident[source.identifier]:
                other = edge.other(source)
                if predicate(edge, source, other):
                    found.add(other)
        return NodeSet(node for node in self._nodes.values() if node in found)

    def parents(self, nodes: Node | Iterable[Node]) -> NodeSet:
        return self._related(nodes, lambda edge, node, other: is_parent_edge(edge, other, node))

    def children(self, nodes: Node | Iterable[Node]) -> NodeSet:
        return self._related(nodes, is_parent_edge)

    def spouses(self, nodes: Node | Iterable[Node]) -> NodeSet:
        return self._related(nodes, is_spouse_edge)

    def neighbours(self, nodes: Node | Iterable[Node]) -> NodeSet:
        return self._related(nodes, is_neighbour_edge)

    def neighbors(self, nodes: Node | Iterable[Node]) -> NodeSet:
        return self.neighbours(nodes)

    def possible_parents(self, nodes: Node | Iterable[Node]) -> NodeSet:
        return self._related(
            nodes,
            lambda edge, node, other: is_possible_parent_edge(edge, other, node),
        )

    def possible_children(self, nodes: Node | Iterable[Node]) -> NodeSet:
        return self._related(nodes, is_possible_parent_edge)

    def possible_neighbours(self, nodes: Node | Iterable[Node]) -> NodeSet:
        return self._related(nodes, is_possible_neighbour_edge)

    def possible_neighbors(self, nodes: Node | Iterable[Node]) -> NodeSet:
        return self.possible_neighbours(nodes)

    def adjacent_nodes(self, nodes: Node | Iterable[Node]) -> NodeSet:
        return self._related(nodes, lambda edge, node, other: True)

    def adjacent(self, first: Node, second: Node) -> bool:
        return bool(self.edges_between(first, second))

    def ancestors(self, nodes: Node | Iterable[Node], *, proper: bool = False) -> NodeSet:
        seeds = self._resolve_nodes(nodes)
        found = self._traverse(seeds, self.parents)
        if proper:
            found.difference_update(seeds)
        return NodeSet(node for node in self._nodes.values() if node in found)

    def descendants(self, nodes: Node | Iterable[Node], *, proper: bool = False) -> NodeSet:
        seeds = self._resolve_nodes(nodes)
        found = self._traverse(seeds, self.children)
        if proper:
            found.difference_update(seeds)
        return NodeSet(node for node in self._nodes.values() if node in found)

    def possible_ancestors(
        self, nodes: Node | Iterable[Node], *, proper: bool = False
    ) -> NodeSet:
        seeds = self._resolve_nodes(nodes)
        found = self._traverse(seeds, self.possible_parents)
        if proper:
            found.difference_update(seeds)
        return NodeSet(node for node in self._nodes.values() if node in found)

    def possible_descendants(
        self, nodes: Node | Iterable[Node], *, proper: bool = False
    ) -> NodeSet:
        seeds = self._resolve_nodes(nodes)
        found = self._traverse(seeds, self.possible_children)
        if proper:
            found.difference_update(seeds)
        return NodeSet(node for node in self._nodes.values() if node in found)

    def anteriors(self, nodes: Node | Iterable[Node], *, proper: bool = False) -> NodeSet:
        return self.possible_ancestors(nodes, proper=proper)

    def posteriors(self, nodes: Node | Iterable[Node], *, proper: bool = False) -> NodeSet:
        return self.possible_descendants(nodes, proper=proper)

    @staticmethod
    def _traverse(
        seeds: Iterable[Node], relationship: Callable[[Node], NodeSet]
    ) -> set[Node]:
        found = set(seeds)
        queue = list(seeds)
        index = 0
        while index < len(queue):
            current = queue[index]
            index += 1
            for related in relationship(current):
                if related not in found:
                    found.add(related)
                    queue.append(related)
        return found

    def exogenous_variables(self) -> NodeSet:
        return NodeSet(node for node in self._nodes.values() if not self.parents(node))

    def find_cycle(self) -> tuple[Node, ...] | None:
        state: dict[Node, int] = {}
        for root in self._nodes.values():
            if state.get(root, 0) != 0:
                continue
            active = [root]
            positions = {root: 0}
            state[root] = 1
            stack: list[tuple[Node, Iterator[Node]]] = [(root, iter(self.children(root)))]
            while stack:
                node, children = stack[-1]
                try:
                    child = next(children)
                except StopIteration:
                    stack.pop()
                    active.pop()
                    positions.pop(node, None)
                    state[node] = 2
                    continue
                child_state = state.get(child, 0)
                if child_state == 0:
                    state[child] = 1
                    positions[child] = len(active)
                    active.append(child)
                    stack.append((child, iter(self.children(child))))
                elif child_state == 1:
                    start = positions[child]
                    return tuple(active[start:] + [child])
        return None

    def is_acyclic(self) -> bool:
        return self.find_cycle() is None

    @staticmethod
    def _semidirected_step(edge: Edge, source: Node, target: Node) -> bool:
        source_mark = edge.endpoint_at(source)
        target_mark = edge.endpoint_at(target)
        return (source_mark is Endpoint.TAIL and target_mark is Endpoint.TAIL) or (
            source_mark is not Endpoint.ARROW and target_mark is not Endpoint.TAIL
        )

    def _find_semidirected_cycle(self) -> tuple[Node, ...] | None:
        for start in self._nodes.values():
            stack: list[tuple[Node, tuple[Node, ...], bool, Edge | None]] = [
                (start, (start,), False, None)
            ]
            while stack:
                current, path, has_oriented_edge, previous_edge = stack.pop()
                choices: list[tuple[Node, bool, Edge]] = []
                for edge in self._incident[current.identifier]:
                    if edge == previous_edge:
                        continue
                    other = edge.other(current)
                    if not self._semidirected_step(edge, current, other):
                        continue
                    oriented = not (
                        edge.endpoint_at(current) is Endpoint.TAIL
                        and edge.endpoint_at(other) is Endpoint.TAIL
                    )
                    choices.append((other, oriented, edge))
                for other, oriented, edge in reversed(choices):
                    used_oriented = has_oriented_edge or oriented
                    if other == start and len(path) > 1 and used_oriented:
                        return path + (start,)
                    if other not in path:
                        stack.append((other, path + (other,), used_oriented, edge))
        return None

    def validate(self, *, strict: bool = False) -> bool:
        if strict:
            raise NotImplementedError("strict theorem-level validation is not implemented")
        for edge in self._edges:
            if edge.node1 == edge.node2:
                raise InvalidGraphError("self-edge found")
            if (edge.left, edge.right) not in _ALLOWED_ENDPOINTS[self._type]:
                raise InvalidGraphError(f"edge incompatible with {self._type.value}")
        if self._type is GraphType.DAG:
            cycle = self.find_cycle()
            if cycle is not None:
                raise InvalidGraphError(f"directed cycle found: {cycle!r}")
        elif self._type in {GraphType.MAG, GraphType.PDAG, GraphType.PAG}:
            cycle = self._find_semidirected_cycle()
            if cycle is not None:
                raise InvalidGraphError(f"semi-directed cycle found: {cycle!r}")
        return True

    def topological_ordering(self) -> tuple[Node, ...]:
        if self._type is not GraphType.DAG:
            raise UnsupportedGraphTypeError("topological ordering is supported only for DAG")
        indegree = {node: len(self.parents(node)) for node in self._nodes.values()}
        rank = {node: index for index, node in enumerate(self._nodes.values())}
        ready = [(rank[node], node) for node in self._nodes.values() if indegree[node] == 0]
        heapq.heapify(ready)
        result: list[Node] = []
        while ready:
            _, node = heapq.heappop(ready)
            result.append(node)
            for child in self.children(node):
                indegree[child] -= 1
                if indegree[child] == 0:
                    heapq.heappush(ready, (rank[child], child))
        if len(result) != len(self._nodes):
            raise InvalidGraphError("topological ordering requires an acyclic graph")
        return tuple(result)

    def is_collider(self, first: Node, middle: Node, last: Node) -> bool:
        left = self._resolve_node(first)
        center = self._resolve_node(middle)
        right = self._resolve_node(last)
        if self._type is not GraphType.DAG:
            raise UnsupportedGraphTypeError("strict collider testing is supported only for DAG")
        if len({left, center, right}) != 3:
            return False
        return left in self.parents(center) and right in self.parents(center)

    def markov_blanket(self, nodes: Node | Iterable[Node]) -> NodeSet:
        if self._type is not GraphType.DAG:
            raise UnsupportedGraphTypeError("Markov blankets are supported only for DAG")
        sources = self._resolve_nodes(nodes)
        blanket: set[Node] = set()
        for source in sources:
            parents = set(self.parents(source))
            children = set(self.children(source))
            blanket.update(parents)
            blanket.update(children)
            for child in children:
                blanket.update(self.parents(child))
        blanket.difference_update(sources)
        return NodeSet(node for node in self._nodes.values() if node in blanket)

    def _empty_same_type(self) -> Graph:
        if type(self) is Graph:
            return Graph(self._type)
        return type(self)()

    def clone(self) -> Graph:
        result = self._empty_same_type()
        for node in self._nodes.values():
            result.add_node(node, **deepcopy(self._node_attributes[node]))
        for edge in self._edges:
            result.add_edge(edge, **deepcopy(self._edge_attributes[edge]))
        for status, members in self._statuses.items():
            result.set_status(status, members)
        return result

    copy = clone

    def merge(self, *others: Graph) -> Graph:
        result = self.clone()
        for other in others:
            if not isinstance(other, Graph):
                raise TypeError("merge accepts Graph objects")
            if other.type is not self._type:
                raise InvalidGraphError("only graphs of the same type can be merged")
            for node in other.nodes:
                result.add_node(node)
                result._node_attributes[result._resolve_node(node)].update(
                    deepcopy(other._node_attributes[node])
                )
            for edge in other.edges:
                result.add_edge(edge)
                result._edge_attributes[result._find_edge(edge)].update(
                    deepcopy(other._edge_attributes[edge])
                )
            for status in NodeStatus:
                combined = set(result.status(status)) | set(other.status(status))
                result.set_status(status, combined)
        return result

    def induced_subgraph(self, nodes: Node | Iterable[Node]) -> Graph:
        retained = self._resolve_nodes(nodes)
        retained_set = set(retained)
        result = self._empty_same_type()
        for node in retained:
            result.add_node(node, **deepcopy(self._node_attributes[node]))
        for edge in self._edges:
            if edge.node1 in retained_set and edge.node2 in retained_set:
                result.add_edge(edge, **deepcopy(self._edge_attributes[edge]))
        for status, members in self._statuses.items():
            result.set_status(status, (node for node in retained if node in members))
        return result

    induced = induced_subgraph

    def edge_induced_subgraph(self, edges: Iterable[Edge]) -> Graph:
        selected: set[Edge] = set()
        for edge in edges:
            selected.add(self._find_edge(edge))
        retained_nodes = {
            node for edge in selected for node in (edge.node1, edge.node2)
        }
        result = self._empty_same_type()
        for node in self._nodes.values():
            if node in retained_nodes:
                result.add_node(node, **deepcopy(self._node_attributes[node]))
        for edge in self._edges:
            if edge in selected:
                result.add_edge(edge, **deepcopy(self._edge_attributes[edge]))
        for status, members in self._statuses.items():
            result.set_status(status, (node for node in result.nodes if node in members))
        return result

    edge_induced = edge_induced_subgraph

    def skeleton(self) -> GRAPH:
        result = GRAPH()
        for node in self._nodes.values():
            result.add_node(node, **deepcopy(self._node_attributes[node]))
        for edge in self._edges:
            result.add_edge(Edge(edge.node1, edge.node2, Endpoint.TAIL, Endpoint.TAIL))
        for status, members in self._statuses.items():
            result.set_status(status, members)
        return result

    # Algorithm modules are imported lazily to keep the core model dependency-free.
    def dconnected(
        self,
        first: Node | Iterable[Node],
        second: Node | Iterable[Node],
        given: Node | Iterable[Node] = (),
    ) -> bool:
        from .traversal import dconnected

        return dconnected(self, first, second, given=given)

    def dseparated(
        self,
        first: Node | Iterable[Node],
        second: Node | Iterable[Node],
        given: Node | Iterable[Node] = (),
    ) -> bool:
        from .traversal import dseparated

        return dseparated(self, first, second, given=given)

    def iter_paths(
        self,
        first: Node | Iterable[Node],
        second: Node | Iterable[Node],
        *,
        directed: bool = False,
        given: Node | Iterable[Node] = (),
        open_only: bool = False,
        max_results: int | None = 100,
    ) -> Iterator[Path]:
        from .traversal import iter_paths

        return iter_paths(
            self,
            first,
            second,
            directed=directed,
            given=given,
            open_only=open_only,
            max_results=max_results,
        )

    def paths(
        self,
        first: Node | Iterable[Node],
        second: Node | Iterable[Node],
        *,
        directed: bool = False,
        given: Node | Iterable[Node] = (),
        open_only: bool = False,
        max_results: int | None = 100,
    ) -> EnumerationResult[Path]:
        from .traversal import paths

        return paths(
            self,
            first,
            second,
            directed=directed,
            given=given,
            open_only=open_only,
            max_results=max_results,
        )

    def ancestor_graph(self, nodes: Node | Iterable[Node] | None = None) -> Graph:
        from .transformations import ancestor_graph

        return ancestor_graph(self, nodes=nodes)

    def canonicalize(self) -> Canonicalization:
        from .transformations import canonicalize

        return canonicalize(self)

    def moralize(self) -> GRAPH:
        from .transformations import moralize

        return moralize(self)

    def backdoor_graph(
        self,
        exposure: Node | Iterable[Node] | None = None,
        outcome: Node | Iterable[Node] | None = None,
    ) -> Graph:
        from .transformations import backdoor_graph

        return backdoor_graph(self, exposure=exposure, outcome=outcome)

    def indirect_graph(self, exposure: Node | Iterable[Node] | None = None) -> Graph:
        from .transformations import indirect_graph

        return indirect_graph(self, exposure=exposure)

    def structural_part(self) -> Graph:
        from .transformations import structural_part

        return structural_part(self)

    def measurement_part(self) -> Graph:
        from .transformations import measurement_part

        return measurement_part(self)

    def to_mag(self) -> MAG:
        from .transformations import to_mag

        return to_mag(self)

    def orient_pdag(self) -> DAG:
        from .transformations import orient_pdag

        return orient_pdag(self)

    def equivalence_class(self) -> PDAG:
        from .transformations import equivalence_class

        return equivalence_class(self)

    def equivalent_dags(self, *, max_results: int | None = 100) -> EnumerationResult[DAG]:
        from .transformations import equivalent_dags

        return equivalent_dags(self, max_results=max_results)

    def is_adjustment_set(
        self,
        nodes: Node | Iterable[Node],
        *,
        exposure: Node | Iterable[Node] | None = None,
        outcome: Node | Iterable[Node] | None = None,
        effect: str = "total",
    ) -> bool:
        from .adjustment import is_adjustment_set

        return is_adjustment_set(
            self, nodes, exposure=exposure, outcome=outcome, effect=effect
        )

    def adjustment_sets(
        self,
        *,
        exposure: Node | Iterable[Node] | None = None,
        outcome: Node | Iterable[Node] | None = None,
        effect: str = "total",
        mode: str = "minimal",
        max_results: int | None = None,
    ) -> EnumerationResult[NodeSet]:
        from .adjustment import adjustment_sets

        return adjustment_sets(
            self,
            exposure=exposure,
            outcome=outcome,
            effect=effect,
            mode=mode,
            max_results=max_results,
        )

    def implied_conditional_independencies(
        self,
        *,
        mode: str = "missing_edge",
        max_results: int | None = None,
    ) -> EnumerationResult[ConditionalIndependence]:
        from .implications import implied_conditional_independencies

        return implied_conditional_independencies(
            self, mode=mode, max_results=max_results
        )

    def instrumental_variables(
        self,
        *,
        exposure: Node | None = None,
        outcome: Node | None = None,
    ) -> list[Instrument]:
        from .instruments import instrumental_variables

        return instrumental_variables(self, exposure=exposure, outcome=outcome)

    def vanishing_tetrads(
        self,
        *,
        kind: str = "all",
        max_results: int | None = None,
    ) -> EnumerationResult[Tetrad]:
        from .sem import vanishing_tetrads

        return vanishing_tetrads(self, kind=kind, max_results=max_results)


class DAG(Graph):
    GRAPH_TYPE = GraphType.DAG


class MAG(Graph):
    GRAPH_TYPE = GraphType.MAG


class PDAG(Graph):
    GRAPH_TYPE = GraphType.PDAG


class PAG(Graph):
    GRAPH_TYPE = GraphType.PAG


class GRAPH(Graph):
    """Internal undirected graph representation."""

    GRAPH_TYPE = GraphType.GRAPH


class DIGRAPH(Graph):
    """Internal permissive directed/mixed graph representation."""

    GRAPH_TYPE = GraphType.DIGRAPH


@dataclass(frozen=True, slots=True, init=False)
class Canonicalization:
    """A canonical graph and nodes generated for latent/selection structure."""

    graph: Graph
    latent_nodes: NodeSet
    selection_nodes: NodeSet

    def __init__(
        self,
        graph: Graph,
        latent_nodes: Node | Iterable[Node] = (),
        selection_nodes: Node | Iterable[Node] = (),
    ) -> None:
        if not isinstance(graph, Graph):
            raise TypeError("canonical graph must be a Graph")
        object.__setattr__(self, "graph", graph)
        object.__setattr__(self, "latent_nodes", _coerce_node_set(latent_nodes))
        object.__setattr__(self, "selection_nodes", _coerce_node_set(selection_nodes))


def nodes(specification: str | Iterable[str]) -> tuple[Node, ...]:
    """Create nodes from whitespace-separated or explicitly iterable identifiers."""
    if isinstance(specification, str):
        identifiers = tuple(specification.split())
    else:
        identifiers = tuple(specification)
    return tuple(Node(identifier) for identifier in identifiers)
