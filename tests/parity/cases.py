"""Executable parity cases keyed by stable fixture identifier."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydagitty import Edge, is_path_open, minimal_separators, reachable_nodes

from . import builders
from .normalize import (
    conditional_independencies,
    edge_text,
    graph_data,
    instruments,
    node_ids,
    node_sets,
    tetrads,
)

Case = Callable[[], Any]


def sep_admg_bidirected_chain() -> dict[str, bool]:
    graph, n = builders.sep_admg_bidirected_chain()
    return {
        "unconditioned": graph.dconnected(n["x"], n["y"]),
        "given_m": graph.dconnected(n["x"], n["y"], given=n["m"]),
    }


def sep_dag_collider_descendant() -> dict[str, bool]:
    graph, n = builders.sep_dag_collider_descendant()
    return {
        "unconditioned": graph.dconnected(n["x"], n["y"]),
        "given_m": graph.dconnected(n["x"], n["y"], given=n["m"]),
        "given_p": graph.dconnected(n["x"], n["y"], given=n["p"]),
    }


def path_mag_mixed_star() -> dict[str, Any]:
    graph, n = builders.path_mag_mixed_star()
    ab = graph.paths(n["a"], n["b"], max_results=None).items
    cd = graph.paths(n["c"], n["d"], max_results=None).items
    return {
        "a_to_b": [
            {
                "nodes": [node.identifier for node in path.nodes],
                "edges": [edge_text(edge) for edge in path.edges],
                "open": is_path_open(graph, path),
            }
            for path in ab
        ],
        "c_to_d": [
            {
                "nodes": [node.identifier for node in path.nodes],
                "edges": [edge_text(edge) for edge in path.edges],
                "open": is_path_open(graph, path),
                "open_given_x": is_path_open(graph, path, given=n["x"]),
            }
            for path in cd
        ],
        "reachable_from_d": node_ids(reachable_nodes(graph, n["d"])),
    }


def separator_extended_confounding() -> dict[str, Any]:
    graph, n = builders.separator_extended_confounding()
    analysis = graph.backdoor_graph().ancestor_graph().moralize()
    return {
        "all": node_sets(minimal_separators(analysis, n["A"], n["B"])),
        "mandatory_D": node_sets(
            minimal_separators(analysis, n["A"], n["B"], mandatory=n["D"])
        ),
        "forbidden_D": node_sets(
            minimal_separators(analysis, n["A"], n["B"], forbidden=n["D"])
        ),
    }


def transform_moral_bidirected_district() -> dict[str, Any]:
    graph, _ = builders.transform_moral_bidirected_district()
    return graph_data(graph.moralize())


def transform_canonical_mixed() -> dict[str, Any]:
    graph, _ = builders.transform_canonical_mixed()
    result = graph.canonicalize()
    data = graph_data(result.graph)
    data.update(
        {
            "latent_nodes": node_ids(result.latent_nodes),
            "selection_nodes": node_ids(result.selection_nodes),
        }
    )
    return data


def transform_latent_projection() -> dict[str, Any]:
    graph, _ = builders.transform_latent_projection()
    projected = graph.to_mag()
    data = graph_data(projected)
    data["latents"] = node_ids(projected.latents)
    return data


def transform_structural_measurement() -> dict[str, Any]:
    graph, _ = builders.transform_structural_measurement()
    structural = graph_data(graph.structural_part())
    measurement_graph = graph.measurement_part()
    measurement = graph_data(measurement_graph)
    measurement["latents"] = node_ids(measurement_graph.latents)
    return {"structural": structural, "measurement": measurement}


def adjust_m_bias_mandatory() -> dict[str, Any]:
    graph, n = builders.adjust_m_bias_mandatory()
    unadjusted = node_sets(graph.adjustment_sets(max_results=None))
    graph.adjusted_nodes = n["m"]
    return {
        "without_mandatory": unadjusted,
        "with_mandatory_m": node_sets(graph.adjustment_sets(max_results=None)),
    }


def adjust_joint_exposure_outcome() -> list[list[str]]:
    graph, _ = builders.adjust_joint_exposure_outcome()
    return node_sets(graph.adjustment_sets(max_results=None))


def adjust_direct_chain() -> dict[str, Any]:
    graph, n = builders.adjust_direct_chain()
    return {
        "empty_total": graph.is_adjustment_set(()),
        "b_direct": graph.is_adjustment_set(n["b"], effect="direct"),
        "Z_total": graph.is_adjustment_set(n["Z"]),
        "Z_direct": graph.is_adjustment_set(n["Z"], effect="direct"),
        "Z_b_direct": graph.is_adjustment_set((n["Z"], n["b"]), effect="direct"),
        "indirect_edges": sorted(edge_text(edge) for edge in graph.indirect_graph().edges),
    }


def adjust_direct_modes_deviation() -> dict[str, Any]:
    graph, _ = builders.adjust_direct_modes_deviation()
    return {
        mode: node_sets(
            graph.adjustment_sets(effect="direct", mode=mode, max_results=None)
        )
        for mode in ("canonical", "all")
    }


def equiv_shielded_triangle() -> dict[str, Any]:
    graph, _ = builders.equiv_shielded_triangle()
    return {
        "cpdag": sorted(edge_text(edge) for edge in graph.equivalence_class().edges),
        "dags": sorted(
            sorted(edge_text(edge) for edge in candidate.edges)
            for candidate in graph.equivalent_dags(max_results=None)
        ),
    }


def implication_mediator() -> dict[str, Any]:
    graph, _ = builders.implication_mediator()
    return {
        mode: conditional_independencies(
            graph.implied_conditional_independencies(mode=mode, max_results=None)
        )
        for mode in ("missing_edge", "basis_set")
    }


def implication_latent_allpairs_deviation() -> list[dict[str, list[str]]]:
    graph, _ = builders.implication_latent_allpairs_deviation()
    return conditional_independencies(
        graph.implied_conditional_independencies(mode="all_pairs", max_results=None)
    )


def instrument_conditional_confounded() -> list[dict[str, Any]]:
    graph, _ = builders.instrument_conditional_confounded()
    return instruments(graph.instrumental_variables())


def instrument_adjusted_deviation() -> list[dict[str, Any]]:
    graph, _ = builders.instrument_adjusted_deviation()
    return instruments(graph.instrumental_variables())


def tetrad_chokepoint() -> list[list[list[list[str]]]]:
    graph, _ = builders.tetrad_chokepoint()
    return tetrads(graph.vanishing_tetrads(max_results=None))


def tetrad_two_factor_138() -> dict[str, int]:
    graph, _ = builders.tetrad_two_factor_138()
    return {
        kind: len(graph.vanishing_tetrads(kind=kind, max_results=None))
        for kind in ("all", "within", "between", "epistemic")
    }


def mag_backdoor_visibility() -> dict[str, bool]:
    cases = {
        "dag": builders.mag_backdoor_dag_invisible(),
        "mag_without_witness": builders.mag_backdoor_visible(),
        "mag_with_witness": builders.mag_backdoor_witness(),
    }
    result = {}
    for name, (graph, n) in cases.items():
        result[name] = graph.backdoor_graph().has_edge(Edge(n["x"], n["y"]))
    return result


def mag_adjust_visibility() -> dict[str, Any]:
    graph, n = builders.mag_adjust_visibility()
    invisible = type(graph)(paths=[n["X"] >> n["Y"]])
    return {
        "without_witness": node_sets(
            invisible.adjustment_sets(exposure=n["X"], outcome=n["Y"], max_results=None)
        ),
        "with_witness": node_sets(
            graph.adjustment_sets(exposure=n["X"], outcome=n["Y"], max_results=None)
        ),
    }


def mag_ancestry_moralization() -> dict[str, Any]:
    graph, n = builders.mag_ancestry_moralization()
    return {
        "ancestor_graph": graph_data(graph.ancestor_graph(n["z"])),
        "moral_graph": graph_data(graph.moralize()),
    }


def pdag_orient_chain_deviation() -> dict[str, Any]:
    graph, _ = builders.pdag_orient_chain()
    return graph_data(graph.orient_pdag())


def pdag_adjust_confounding() -> list[list[str]]:
    graph, _ = builders.pdag_adjust_confounding()
    return node_sets(graph.adjustment_sets(max_results=None))


def pdag_transformations() -> dict[str, Any]:
    graph, n = builders.pdag_transformations()
    return {
        "ancestor_graph": graph_data(graph.ancestor_graph(n["c"])),
        "moral_graph": graph_data(graph.moralize()),
    }


def pag_separation_circle_tail() -> dict[str, bool]:
    graph, n = builders.pag_separation_circle_tail()
    return {
        "unconditioned": graph.dconnected(n["a"], n["c"]),
        "given_b": graph.dconnected(n["a"], n["c"], given=n["b"]),
    }


def pag_adjust_circle_chain() -> dict[str, Any]:
    graph, _ = builders.pag_adjust_circle_chain()
    return {
        "empty_valid": graph.is_adjustment_set(()),
        "minimal": node_sets(graph.adjustment_sets(max_results=None)),
    }


def pag_backdoor_circle_tail() -> dict[str, Any]:
    graph, _ = builders.pag_backdoor_circle_tail()
    return {
        "source": graph_data(graph),
        "backdoor": graph_data(graph.backdoor_graph()),
    }


CASES: dict[str, Case] = {
    "sep-admg-bidirected-chain": sep_admg_bidirected_chain,
    "sep-dag-collider-descendant": sep_dag_collider_descendant,
    "path-mag-mixed-star": path_mag_mixed_star,
    "separator-extended-confounding": separator_extended_confounding,
    "transform-moral-bidirected-district": transform_moral_bidirected_district,
    "transform-canonical-mixed": transform_canonical_mixed,
    "transform-latent-projection": transform_latent_projection,
    "transform-structural-measurement": transform_structural_measurement,
    "adjust-m-bias-mandatory": adjust_m_bias_mandatory,
    "adjust-joint-exposure-outcome": adjust_joint_exposure_outcome,
    "adjust-direct-chain": adjust_direct_chain,
    "adjust-direct-modes-deviation": adjust_direct_modes_deviation,
    "equiv-shielded-triangle": equiv_shielded_triangle,
    "implication-mediator": implication_mediator,
    "implication-latent-allpairs-deviation": implication_latent_allpairs_deviation,
    "instrument-conditional-confounded": instrument_conditional_confounded,
    "instrument-adjusted-deviation": instrument_adjusted_deviation,
    "tetrad-chokepoint": tetrad_chokepoint,
    "tetrad-two-factor-138": tetrad_two_factor_138,
    "mag-backdoor-visibility": mag_backdoor_visibility,
    "mag-adjust-visibility": mag_adjust_visibility,
    "mag-ancestry-moralization": mag_ancestry_moralization,
    "pdag-orient-chain-deviation": pdag_orient_chain_deviation,
    "pdag-adjust-confounding": pdag_adjust_confounding,
    "pdag-transformations": pdag_transformations,
    "pag-separation-circle-tail": pag_separation_circle_tail,
    "pag-adjust-circle-chain": pag_adjust_circle_chain,
    "pag-backdoor-circle-tail": pag_backdoor_circle_tail,
}


CASE_BUILDERS: dict[str, tuple[str, ...]] = {
    "sep-admg-bidirected-chain": ("sep_admg_bidirected_chain",),
    "sep-dag-collider-descendant": ("sep_dag_collider_descendant",),
    "path-mag-mixed-star": ("path_mag_mixed_star",),
    "separator-extended-confounding": ("separator_extended_confounding",),
    "transform-moral-bidirected-district": ("transform_moral_bidirected_district",),
    "transform-canonical-mixed": ("transform_canonical_mixed",),
    "transform-latent-projection": ("transform_latent_projection",),
    "transform-structural-measurement": ("transform_structural_measurement",),
    "adjust-m-bias-mandatory": ("adjust_m_bias_mandatory",),
    "adjust-joint-exposure-outcome": ("adjust_joint_exposure_outcome",),
    "adjust-direct-chain": ("adjust_direct_chain",),
    "adjust-direct-modes-deviation": ("adjust_direct_modes_deviation",),
    "equiv-shielded-triangle": ("equiv_shielded_triangle",),
    "implication-mediator": ("implication_mediator",),
    "implication-latent-allpairs-deviation": ("implication_latent_allpairs_deviation",),
    "instrument-conditional-confounded": ("instrument_conditional_confounded",),
    "instrument-adjusted-deviation": ("instrument_adjusted_deviation",),
    "tetrad-chokepoint": ("tetrad_chokepoint",),
    "tetrad-two-factor-138": ("tetrad_two_factor_138",),
    "mag-backdoor-visibility": (
        "mag_backdoor_dag_invisible",
        "mag_backdoor_visible",
        "mag_backdoor_witness",
    ),
    "mag-adjust-visibility": ("mag_adjust_visibility",),
    "mag-ancestry-moralization": ("mag_ancestry_moralization",),
    "pdag-orient-chain-deviation": ("pdag_orient_chain",),
    "pdag-adjust-confounding": ("pdag_adjust_confounding",),
    "pdag-transformations": ("pdag_transformations",),
    "pag-separation-circle-tail": ("pag_separation_circle_tail",),
    "pag-adjust-circle-chain": ("pag_adjust_circle_chain",),
    "pag-backdoor-circle-tail": ("pag_backdoor_circle_tail",),
}
