import pytest

from pydagitty import (
    DAG,
    MAG,
    PAG,
    PDAG,
    Edge,
    Endpoint,
    InvalidGraphError,
    UnsupportedGraphTypeError,
    nodes,
)


def _sets(result) -> set[frozenset[str]]:
    return {frozenset(node.identifier for node in item) for item in result}


def test_total_adjustment_identifies_a_single_confounder() -> None:
    x, y, z = nodes("X Y Z")
    graph = DAG(paths=[z >> x, z >> y, x >> y])
    graph.exposures = x
    graph.outcomes = y

    minimal = graph.adjustment_sets()
    canonical = graph.adjustment_sets(mode="canonical")

    assert _sets(minimal) == {frozenset({"Z"})}
    assert _sets(canonical) == {frozenset({"Z"})}
    assert graph.is_adjustment_set(z)
    assert not graph.is_adjustment_set(())
    assert not graph.is_adjustment_set(x)
    assert all(graph.is_adjustment_set(item) for item in minimal)


def test_adjustment_modes_mandatory_nodes_and_limit() -> None:
    x, y, z, w, irrelevant = nodes("X Y Z W Q")
    graph = DAG(nodes=[irrelevant], paths=[z >> x, z >> y, w >> x, w >> y, x >> y])
    graph.exposures = x
    graph.outcomes = y

    assert _sets(graph.adjustment_sets(mode="minimal")) == {frozenset({"Z", "W"})}
    assert _sets(graph.adjustment_sets(mode="canonical")) == {frozenset({"Z", "W"})}
    assert _sets(graph.adjustment_sets(mode="all")) == {
        frozenset({"Z", "W"}),
        frozenset({"Z", "W", "Q"}),
    }
    graph.adjusted_nodes = z
    assert _sets(graph.adjustment_sets()) == {frozenset({"Z", "W"})}
    assert not graph.is_adjustment_set(w)
    limited = graph.adjustment_sets(mode="all", max_results=1)
    assert len(limited) == 1
    assert limited.truncated
    assert graph.adjustment_sets(max_results=0).items == ()


def test_selection_adjustment_requires_outcome_selection_separation() -> None:
    exposure, outcome, confounder, selected = nodes("X Y U S")
    graph = DAG(
        paths=[
            confounder >> exposure,
            confounder >> outcome,
            exposure >> selected,
        ]
    )
    graph.exposures = exposure
    graph.outcomes = outcome
    graph.selected_nodes = selected

    assert not graph.is_adjustment_set(confounder)
    assert graph.adjustment_sets().items == ()


def test_filtered_adjustment_limit_reports_exhaustion_correctly() -> None:
    confounder, exposure, mediator, outcome, selected = nodes("A X C Y S")
    graph = DAG(
        paths=[
            confounder >> exposure,
            confounder >> mediator >> outcome,
            exposure >> selected,
        ]
    )
    graph.exposures = exposure
    graph.outcomes = outcome
    graph.selected_nodes = selected

    result = graph.adjustment_sets(max_results=1)

    assert result.items == ()
    assert not result.truncated


def test_total_adjustment_forbids_mediators_and_validates_effect_statuses() -> None:
    x, mediator, y = nodes("X M Y")
    graph = DAG(paths=[x >> mediator >> y])
    graph.exposures = x
    graph.outcomes = y

    assert graph.is_adjustment_set(())
    assert not graph.is_adjustment_set(mediator)
    graph.latents = x
    with pytest.raises(InvalidGraphError):
        graph.adjustment_sets()
    graph.latents = ()
    graph.outcomes = x
    with pytest.raises(InvalidGraphError):
        graph.adjustment_sets()


def test_joint_exposure_paths_stop_at_the_next_exposure() -> None:
    first, covariate, second, outcome = nodes("X1 A X2 Y")
    graph = DAG(paths=[first >> covariate >> second >> outcome])

    assert graph.is_adjustment_set(
        covariate,
        exposure=(first, second),
        outcome=outcome,
    )


def test_pdag_adjustment_uses_partial_not_arbitrary_oriented_semantics() -> None:
    exposure, middle, outcome = nodes("X M Y")
    graph = PDAG(paths=[exposure - middle, middle - outcome])

    assert graph.adjustment_sets(exposure=exposure, outcome=outcome).items == ()
    assert not graph.is_adjustment_set(middle, exposure=exposure, outcome=outcome)

def test_direct_effect_adjustment_blocks_indirect_and_backdoor_paths() -> None:
    x, mediator, y, confounder = nodes("X M Y Z")
    graph = DAG(
        paths=[
            x >> mediator >> y,
            x >> y,
            confounder >> x,
            confounder >> y,
        ]
    )
    graph.exposures = x
    graph.outcomes = y

    direct = graph.adjustment_sets(effect="direct")

    assert _sets(direct) == {frozenset({"M", "Z"})}
    assert graph.is_adjustment_set((mediator, confounder), effect="direct")
    assert not graph.is_adjustment_set(confounder, effect="direct")
    with pytest.raises(UnsupportedGraphTypeError):
        MAG(nodes=[x, y]).adjustment_sets(exposure=x, outcome=y, effect="direct")


@pytest.mark.parametrize("graph_class", [PDAG, MAG, PAG])
def test_total_adjustment_publicly_supports_other_causal_graph_types(graph_class) -> None:
    x, y, witness = nodes("X Y W")
    graph = graph_class(paths=[witness >> x, x >> y])

    result = graph.adjustment_sets(exposure=x, outcome=y)

    assert _sets(result) == {frozenset()}
    assert graph.is_adjustment_set((), exposure=x, outcome=y)


def test_mag_and_pag_adjustment_reject_undirected_edges() -> None:
    x, y = nodes("X Y")
    undirected = Edge(x, y, Endpoint.TAIL, Endpoint.TAIL)

    with pytest.raises(InvalidGraphError):
        MAG(edges=[undirected]).adjustment_sets(exposure=x, outcome=y)
    with pytest.raises(InvalidGraphError):
        PAG(edges=[undirected]).adjustment_sets(exposure=x, outcome=y)


def test_implied_independencies_for_a_chain_in_all_modes() -> None:
    a, b, c = nodes("A B C")
    graph = DAG(paths=[a >> b, b >> c])

    missing = graph.implied_conditional_independencies(mode="missing_edge")
    basis = graph.implied_conditional_independencies(mode="basis_set")
    all_pairs = graph.implied_conditional_independencies(mode="all_pairs")

    assert len(missing) == 1
    assert missing[0].left == {a}
    assert missing[0].right == {c}
    assert missing[0].given == {b}
    assert len(basis) == 1
    assert basis[0].left == {c}
    assert basis[0].right == {a}
    assert basis[0].given == {b}
    assert missing.items == all_pairs.items


def test_implications_exclude_latent_and_selected_endpoints() -> None:
    a, b, latent, selected = nodes("A B L S")
    graph = DAG(nodes=[a, b, latent, selected])
    graph.latents = latent
    graph.selected_nodes = selected

    results = graph.implied_conditional_independencies(mode="missing_edge")

    assert len(results) == 1
    assert results[0].left == {a}
    assert results[0].right == {b}
    assert results[0].given == {selected}
    assert latent not in results[0].left | results[0].right | results[0].given
    with pytest.raises(ValueError):
        graph.implied_conditional_independencies(mode="basis_set")


def test_mag_basis_uses_directed_topological_order_not_insertion_order() -> None:
    c, a, b = nodes("C A B")
    graph = MAG(nodes=[c, a, b], paths=[b >> a, a >> c])

    basis = graph.implied_conditional_independencies(mode="basis_set")

    assert any(
        statement.left == {c}
        and statement.right == {b}
        and statement.given == {a}
        for statement in basis
    )


def test_pdag_missing_edge_can_require_non_moral_minimal_conditioning() -> None:
    a, b, c, d = nodes("A B C D")
    graph = PDAG(paths=[a >> c, b - c, d >> b])

    result = graph.implied_conditional_independencies(mode="missing_edge")

    assert any(
        statement.left == {c}
        and statement.right == {d}
        and statement.given == {a, b}
        for statement in result
    )


def test_implication_modes_validate_limits_and_graph_type() -> None:
    a, b, c = nodes("A B C")
    graph = DAG(nodes=[a, b, c])

    limited = graph.implied_conditional_independencies(mode="all_pairs", max_results=2)

    assert len(limited) == 2
    assert limited.truncated
    assert graph.implied_conditional_independencies(max_results=0).items == ()
    with pytest.raises(ValueError):
        graph.implied_conditional_independencies(mode="unknown")
    with pytest.raises(TypeError):
        graph.implied_conditional_independencies(max_results=True)
    with pytest.raises(UnsupportedGraphTypeError):
        PAG(nodes=[a, b]).implied_conditional_independencies()


def test_unconditional_and_conditional_instruments() -> None:
    z, x, y = nodes("Z X Y")
    simple = DAG(paths=[z >> x, x >> y])
    simple.exposures = x
    simple.outcomes = y

    instruments = simple.instrumental_variables()

    assert len(instruments) == 1
    assert instruments[0].node == z
    assert instruments[0].conditioning_set == set()
    assert instruments[0].given == set()

    u, z2, x2, y2 = nodes("U Z2 X2 Y2")
    conditional = DAG(paths=[u >> z2, u >> y2, z2 >> x2, x2 >> y2])
    result = conditional.instrumental_variables(exposure=x2, outcome=y2)
    assert [(item.node, item.given) for item in result] == [(z2, {u})]


def test_instruments_require_relevance_and_exclusion() -> None:
    irrelevant, exposure, outcome = nodes("I X Y")
    irrelevant_graph = DAG(nodes=[irrelevant], paths=[exposure >> outcome])
    assert irrelevant_graph.instrumental_variables(exposure=exposure, outcome=outcome) == []

    invalid, exposure2, outcome2 = nodes("Z X2 Y2")
    exclusion_graph = DAG(paths=[invalid >> exposure2, invalid >> outcome2, exposure2 >> outcome2])
    assert exclusion_graph.instrumental_variables(exposure=exposure2, outcome=outcome2) == []


def test_instruments_exclude_latent_nodes_and_require_single_effect_nodes() -> None:
    z, x, y = nodes("Z X Y")
    graph = DAG(paths=[z >> x, x >> y])
    graph.exposures = x
    graph.outcomes = y
    graph.latents = z

    assert graph.instrumental_variables() == []
    graph.exposures = (x, z)
    with pytest.raises(InvalidGraphError):
        graph.instrumental_variables()
    with pytest.raises(UnsupportedGraphTypeError):
        PDAG(nodes=[x, y]).instrumental_variables(exposure=x, outcome=y)


def test_post_exposure_nonmediator_can_be_an_instrument() -> None:
    exposure, instrument, outcome = nodes("X Z Y")
    graph = DAG(paths=[exposure >> instrument, exposure >> outcome])

    result = graph.instrumental_variables(exposure=exposure, outcome=outcome)

    assert [item.node for item in result] == [instrument]


def test_instruments_reject_adjusted_effect_nodes() -> None:
    instrument, exposure, outcome = nodes("Z X Y")
    graph = DAG(paths=[instrument >> exposure, exposure >> outcome])
    graph.adjusted_nodes = exposure

    with pytest.raises(InvalidGraphError):
        graph.instrumental_variables(exposure=exposure, outcome=outcome)


def test_instruments_exclude_adjusted_conditioning_candidates() -> None:
    adjusted, instrument, exposure, outcome = nodes("W I X Y")
    graph = DAG(
        paths=[
            adjusted >> outcome,
            adjusted >> instrument,
            instrument >> exposure,
            exposure >> outcome,
            exposure @ outcome,
        ]
    )
    graph.adjusted_nodes = adjusted

    assert graph.instrumental_variables(exposure=exposure, outcome=outcome) == []
