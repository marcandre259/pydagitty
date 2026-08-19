"""Dependency-free construction, separation, and adjustment workflow."""

from pydagitty import DAG, nodes


def main() -> None:
    confounder, exposure, mediator, outcome = nodes("Z X M Y")
    graph = DAG(
        paths=[
            confounder >> exposure,
            confounder >> outcome,
            exposure >> mediator >> outcome,
        ]
    )
    graph.exposures = exposure
    graph.outcomes = outcome

    assert graph.validate()
    assert graph.dconnected(exposure, outcome)
    assert graph.dconnected(exposure, outcome, given=confounder)

    paths = graph.paths(exposure, outcome, max_results=20)
    assert not paths.truncated
    assert len(paths) == 2

    sets = graph.adjustment_sets(mode="minimal", max_results=20)
    assert sets.items == ({confounder},)
    assert not sets.truncated
    assert graph.is_adjustment_set(confounder)
    assert not graph.is_adjustment_set(mediator)

    print("minimal adjustment sets:")
    for adjustment_set in sets:
        print("  ", tuple(node.identifier for node in adjustment_set))
    print("This identifies a graphical adjustment set; it does not estimate an effect.")


if __name__ == "__main__":
    main()
