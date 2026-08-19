"""Dependency-free implications, instruments, tetrads, and equivalence examples."""

from pydagitty import DAG, nodes


def main() -> None:
    first, middle, last = nodes("A B C")
    chain = DAG(paths=[first >> middle >> last])

    implications = chain.implied_conditional_independencies(max_results=20)
    assert len(implications) == 1
    assert implications[0].left == {first}
    assert implications[0].right == {last}
    assert implications[0].given == {middle}
    assert not implications.truncated

    equivalent = chain.equivalent_dags(max_results=20)
    assert len(equivalent) == 3
    assert not equivalent.truncated

    instrument, exposure, outcome = nodes("Z X Y")
    iv_graph = DAG(paths=[instrument >> exposure >> outcome])
    discovered = iv_graph.instrumental_variables(exposure=exposure, outcome=outcome)
    assert [(item.node, item.given) for item in discovered] == [(instrument, set())]

    latent, a, b, c, d = nodes("L I1 I2 I3 I4")
    factor = DAG(paths=[latent >> a, latent >> b, latent >> c, latent >> d])
    factor.latents = latent
    tetrads = factor.vanishing_tetrads(kind="within", max_results=10)
    assert len(tetrads) == 3
    assert not tetrads.truncated

    print(f"implications: {len(implications)}")
    print(f"equivalent DAGs: {len(equivalent)}")
    print(f"graphical instruments: {len(discovered)}")
    print(f"within-factor tetrads: {len(tetrads)}")
    print("These are graphical consequences, not fitted statistical results.")


if __name__ == "__main__":
    main()
