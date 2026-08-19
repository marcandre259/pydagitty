"""Stable normalization helpers for parity expectations."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pydagitty import ConditionalIndependence, Edge, Endpoint, Graph, Instrument, Node, Tetrad


def node_ids(values: Iterable[Node]) -> list[str]:
    return sorted(node.identifier for node in values)


def node_sets(values: Iterable[Iterable[Node]]) -> list[list[str]]:
    return sorted(node_ids(value) for value in values)


def edge_text(edge: Edge) -> str:
    first, second = sorted(edge.nodes, key=lambda node: node.identifier)
    left = edge.endpoint_at(first)
    right = edge.endpoint_at(second)
    if left is Endpoint.TAIL and right is Endpoint.ARROW:
        return f"{first}->{second}"
    if left is Endpoint.ARROW and right is Endpoint.TAIL:
        return f"{second}->{first}"
    if left is right is Endpoint.ARROW:
        return f"{first}<->{second}"
    if left is right is Endpoint.TAIL:
        return f"{first}--{second}"
    marks = {
        Endpoint.TAIL: "-",
        Endpoint.ARROW: ">",
        Endpoint.CIRCLE: "@",
    }
    return f"{first}{marks[left]}-{marks[right]}{second}"


def graph_data(graph: Graph) -> dict[str, Any]:
    return {
        "type": graph.type.value,
        "nodes": node_ids(graph.nodes),
        "edges": sorted(edge_text(edge) for edge in graph.edges),
    }


def conditional_independencies(
    values: Iterable[ConditionalIndependence],
) -> list[dict[str, list[str]]]:
    result = []
    for value in values:
        endpoints = sorted((node_ids(value.left), node_ids(value.right)))
        result.append(
            {
                "left": endpoints[0],
                "right": endpoints[1],
                "given": node_ids(value.given),
            }
        )
    return sorted(result, key=lambda item: (item["left"], item["right"], item["given"]))


def instruments(values: Iterable[Instrument]) -> list[dict[str, Any]]:
    return sorted(
        (
            {
                "instrument": value.node.identifier,
                "given": node_ids(value.conditioning_set),
            }
            for value in values
        ),
        key=lambda item: (item["instrument"], item["given"]),
    )


def tetrads(values: Iterable[Tetrad]) -> list[list[list[list[str]]]]:
    result = []
    for value in values:
        positive = sorted(
            (
                sorted((value.i.identifier, value.j.identifier)),
                sorted((value.k.identifier, value.l.identifier)),
            )
        )
        negative = sorted(
            (
                sorted((value.i.identifier, value.k.identifier)),
                sorted((value.j.identifier, value.l.identifier)),
            )
        )
        result.append(sorted((positive, negative)))
    return sorted(result)
