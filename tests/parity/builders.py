"""Object-based builders adapted from pinned Dagitty fixtures.

Fixture structures are adapted under GPL-2.0-only from jtextor/dagitty commit
7a657776dc8f5e5ba4e323edb028e2c2aaf29327. No graph-string parser is used.
"""

from __future__ import annotations

from pydagitty import DAG, MAG, PAG, PDAG, Edge, Endpoint, Graph, Node, nodes

BuiltGraph = tuple[Graph, dict[str, Node]]


def _named(text: str) -> tuple[tuple[Node, ...], dict[str, Node]]:
    values = nodes(text)
    return values, {node.identifier: node for node in values}


def sep_admg_bidirected_chain() -> BuiltGraph:
    (x, m, y), named = _named("x m y")
    return DAG(paths=[x @ m, m >> y]), named


def sep_dag_collider_descendant() -> BuiltGraph:
    (x, m, y, p), named = _named("x m y p")
    return DAG(paths=[x >> m, y >> m, m >> p]), named


def path_mag_mixed_star() -> BuiltGraph:
    (a, b, c, d, f, x), named = _named("a b c d f x")
    return MAG(nodes=[f], paths=[a - x, x >> b, c @ x, d >> x]), named


def separator_extended_confounding() -> BuiltGraph:
    (a, b, c, d, e), named = _named("A B C D E")
    graph = DAG(paths=[a >> b, c >> b, c >> a, d >> c, e >> c, d >> a, e >> b])
    graph.exposures = a
    graph.outcomes = b
    return graph, named


def transform_moral_bidirected_district() -> BuiltGraph:
    (a, b, x, z), named = _named("a b x z")
    return DAG(paths=[a >> x, x @ z, b >> z]), named


def transform_canonical_mixed() -> BuiltGraph:
    (a, b, c, d), named = _named("a b c d")
    return MAG(paths=[a @ b, b @ c, c - d]), named


def transform_latent_projection() -> BuiltGraph:
    (v1, z, v2, y, x), named = _named("v1 z v2 y x")
    graph = DAG(paths=[v1 >> z, v1 >> v2 >> y, x >> v1])
    graph.latents = v1
    return graph, named


def transform_structural_measurement() -> BuiltGraph:
    (latent, construct, indicator, outcome), named = _named("L A B C")
    graph = DAG(paths=[latent >> construct, latent >> indicator, construct >> outcome])
    graph.latents = (latent, construct)
    return graph, named


def adjust_m_bias_mandatory() -> BuiltGraph:
    (a, x, m, b, y), named = _named("a x m b y")
    graph = DAG(paths=[a >> x, a >> m, b >> m, b >> y])
    graph.exposures = x
    graph.outcomes = y
    return graph, named


def adjust_joint_exposure_outcome() -> BuiltGraph:
    (c, y1, m, x1, y2, x2, m2), named = _named("C Y1 m X1 Y2 X2 m2")
    graph = DAG(
        paths=[
            c >> y1,
            c >> m,
            x1 >> x2,
            x1 >> y2 >> y1,
            x2 >> y1,
            x1 >> m2 >> m >> x2,
        ]
    )
    graph.exposures = (x1, x2)
    graph.outcomes = (y1, y2)
    return graph, named


def adjust_direct_chain() -> BuiltGraph:
    (z, a, b, c), named = _named("Z a b c")
    graph = DAG(
        paths=[z >> a, z >> b, z >> c, a >> b, a >> c, b >> c]
    )
    graph.exposures = a
    graph.outcomes = c
    return graph, named


def adjust_direct_modes_deviation() -> BuiltGraph:
    return adjust_direct_chain()


def equiv_shielded_triangle() -> BuiltGraph:
    (x, y, z), named = _named("x y z")
    return DAG(paths=[x >> y, z >> y, z >> x]), named


def implication_mediator() -> BuiltGraph:
    (z, x, i, y), named = _named("Z X I Y")
    return DAG(paths=[z >> x, z >> i, x >> i, x >> y, i >> y]), named


def implication_latent_allpairs_deviation() -> BuiltGraph:
    (x, m, y), named = _named("x m y")
    graph = DAG(paths=[x >> m >> y])
    graph.latents = m
    return graph, named


def instrument_conditional_confounded() -> BuiltGraph:
    (w, y, i, x), named = _named("w y i x")
    graph = DAG(paths=[w >> y, w >> i, i >> x, x >> y, x @ y])
    graph.exposures = x
    graph.outcomes = y
    return graph, named


def instrument_adjusted_deviation() -> BuiltGraph:
    (w, y, i, x), named = _named("w y i x")
    graph = DAG(paths=[w >> y, w >> i, i >> x, x >> y, x @ y])
    graph.exposures = x
    graph.outcomes = y
    graph.adjusted_nodes = w
    return graph, named


def tetrad_chokepoint() -> BuiltGraph:
    (a, x, b, y), named = _named("a x b y")
    return DAG(paths=[a >> x, b >> x, x >> y]), named


def tetrad_two_factor_138() -> BuiltGraph:
    (x, y, x1, x2, x3, x4, y1, y2, y3, y4), named = _named(
        "x y x1 x2 x3 x4 y1 y2 y3 y4"
    )
    graph = DAG(
        paths=[
            x @ y,
            x >> x1,
            x >> x2,
            x >> x3,
            x >> x4,
            y >> y1,
            y >> y2,
            y >> y3,
            y >> y4,
        ]
    )
    graph.latents = (x, y)
    return graph, named


def mag_backdoor_dag_invisible() -> BuiltGraph:
    (x, m, y), named = _named("x m y")
    graph = DAG(paths=[x @ m, m @ y, x >> y])
    graph.exposures = x
    graph.outcomes = y
    return graph, named


def mag_backdoor_visible() -> BuiltGraph:
    (x, m, y), named = _named("x m y")
    graph = MAG(paths=[x @ m, m @ y, x >> y])
    graph.exposures = x
    graph.outcomes = y
    return graph, named


def mag_backdoor_witness() -> BuiltGraph:
    (x, m, y, i), named = _named("x m y i")
    graph = MAG(paths=[x @ m, m @ y, x >> y, i >> x])
    graph.exposures = x
    graph.outcomes = y
    return graph, named


def mag_adjust_visibility() -> BuiltGraph:
    (i, x, y), named = _named("I X Y")
    return MAG(paths=[i >> x, x >> y]), named


def mag_ancestry_moralization() -> BuiltGraph:
    (a, b, x, z), named = _named("a b x z")
    return MAG(paths=[a >> x, x @ z, b >> z]), named


def pdag_orient_chain() -> BuiltGraph:
    (x, y, z), named = _named("x y z")
    return PDAG(paths=[x >> y, y - z]), named


def pdag_adjust_confounding() -> BuiltGraph:
    (z, x, y, c), named = _named("z x y c")
    graph = PDAG(paths=[z - x, x >> y, c >> x, c >> y])
    graph.exposures = x
    graph.outcomes = y
    return graph, named


def pdag_transformations() -> BuiltGraph:
    (a, b, c, d), named = _named("a b c d")
    return PDAG(paths=[a >> c, b - c, d >> b]), named


def pag_separation_circle_tail() -> BuiltGraph:
    (a, b, c), named = _named("a b c")
    return PAG(
        edges=[
            Edge(a, b, Endpoint.CIRCLE, Endpoint.ARROW),
            Edge(c, b, Endpoint.CIRCLE, Endpoint.ARROW),
        ]
    ), named


def pag_adjust_circle_chain() -> BuiltGraph:
    (u, x, y), named = _named("u x y")
    graph = PAG(
        edges=[
            Edge(u, x, Endpoint.CIRCLE, Endpoint.CIRCLE),
            Edge(x, y, Endpoint.CIRCLE, Endpoint.CIRCLE),
        ]
    )
    graph.exposures = x
    graph.outcomes = y
    return graph, named


def pag_backdoor_circle_tail() -> BuiltGraph:
    (v1, v2, v3, v4, x, y), named = _named("V1 V2 V3 V4 X Y")
    graph = PAG(
        edges=[
            Edge(v2, x, Endpoint.CIRCLE, Endpoint.ARROW),
            Edge(v1, x, Endpoint.CIRCLE, Endpoint.ARROW),
            Edge(x, v4),
            Edge(x, y),
            Edge(v4, y, Endpoint.CIRCLE, Endpoint.ARROW),
            Edge(v3, y),
            Edge(v3, v4),
            Edge(v3, x, Endpoint.CIRCLE, Endpoint.ARROW),
        ]
    )
    graph.exposures = x
    graph.outcomes = y
    return graph, named
