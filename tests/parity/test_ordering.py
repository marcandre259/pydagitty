"""Protect deterministic PyDagitty ordering separately from parity set equality."""

from __future__ import annotations

from pydagitty import minimal_separators

from . import builders
from .normalize import edge_text


def test_separator_and_equivalent_dag_order_is_stable() -> None:
    graph, n = builders.separator_extended_confounding()
    analysis = graph.backdoor_graph().ancestor_graph().moralize()
    separators = minimal_separators(analysis, n["A"], n["B"])
    assert [[node.identifier for node in item] for item in separators] == [
        ["C", "E"],
        ["C", "D"],
    ]

    triangle, _ = builders.equiv_shielded_triangle()
    dags = triangle.equivalent_dags(max_results=None)
    assert [[edge_text(edge) for edge in dag.edges] for dag in dags] == [
        ["x->y", "z->y", "z->x"],
        ["x->y", "z->y", "x->z"],
        ["x->y", "y->z", "x->z"],
        ["y->x", "z->y", "z->x"],
        ["y->x", "y->z", "z->x"],
        ["y->x", "y->z", "x->z"],
    ]


def test_analysis_record_order_is_stable() -> None:
    implication_graph, _ = builders.implication_mediator()
    statements = implication_graph.implied_conditional_independencies(
        mode="missing_edge", max_results=None
    )
    assert [
        (
            [node.identifier for node in item.left],
            [node.identifier for node in item.right],
            [node.identifier for node in item.given],
        )
        for item in statements
    ] == [(["Z"], ["Y"], ["X", "I"])]

    instrument_graph, _ = builders.instrument_conditional_confounded()
    assert [
        (item.node.identifier, [node.identifier for node in item.given])
        for item in instrument_graph.instrumental_variables()
    ] == [("i", ["w"])]

    tetrad_graph, _ = builders.tetrad_chokepoint()
    assert [
        [node.identifier for node in item.nodes]
        for item in tetrad_graph.vanishing_tetrads(max_results=None)
    ] == [["a", "x", "y", "b"]]
