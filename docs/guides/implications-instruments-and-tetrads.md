# Implications, Instruments, and Tetrads

These APIs derive graphical consequences. They do not read data, estimate
parameters, calculate standard errors, or perform statistical tests.

## Implied Conditional Independencies

```python
from pydagitty import DAG, nodes

A, B, C = nodes("A B C")
chain = DAG(paths=[A >> B >> C])
result = chain.implied_conditional_independencies(
    mode="missing_edge", max_results=20
)

statement = result[0]
assert statement.left == {A}
assert statement.right == {C}
assert statement.given == {B}
assert not result.truncated
```

Modes are:

| Mode | Meaning |
| --- | --- |
| `missing_edge` | One or more minimal separating statements for each nonadjacent observed pair. |
| `basis_set` | A local Markov basis with possibly set-valued right sides. |
| `all_pairs` | Every separating conditioning subset for every observed pair; exponential. |

Scope is DAG supported and MAG/PDAG preview. PAG and provisional graph types
raise `UnsupportedGraphTypeError`. Latent and selected nodes are excluded as
endpoints and optional conditioning candidates. Selected nodes appear as fixed
members of each `.given`; `basis_set` rejects any selected nodes.

Use `max_results` and inspect `truncated`. A returned statement is implied by
the graph under the implemented separation semantics; empirical data can
violate it because the model or distributional assumptions are wrong.

## Graphical Instruments

```python
Z, X, Y = nodes("Z X Y")
iv_graph = DAG(paths=[Z >> X >> Y])
iv_graph.exposures = X
iv_graph.outcomes = Y

instruments = iv_graph.instrumental_variables()
assert [(item.node, item.given) for item in instruments] == [(Z, set())]
```

Instrument discovery is DAG-only and requires exactly one distinct exposure
and outcome, supplied as singular arguments or statuses. Latent, selected, and
adjusted nodes are not candidate instruments. Each `Instrument` contains a
candidate and the first deterministic conditioning set found for it.

The graphical criterion checks exclusion and relevance for a total effect.
Identification as an instrumental variable additionally requires a linear
structural model and homogeneous effect assumptions. This method does not
estimate an IV effect or validate those assumptions from data.

## Vanishing Tetrads

```python
L, A, B, C, D = nodes("L A B C D")
factor = DAG(paths=[L >> A, L >> B, L >> C, L >> D])
factor.latents = L

tetrads = factor.vanishing_tetrads(kind="within", max_results=10)
assert len(tetrads) == 3
assert not tetrads.truncated
assert all(L not in tetrad.nodes for tetrad in tetrads)
```

Tetrads are supported only for DAG/ADMG inputs and are generic vanishing
two-by-two covariance determinants under a linear-SEM trek criterion.
Bidirected DAG edges are interpreted through fresh latent common causes;
marked latent nodes are excluded from observed quadruples.

`kind` can be `all`, `within`, `between`, or `epistemic`. The filtered kinds
apply the pinned Dagitty parent typology after canonicalization. A `Tetrad`
records `i`, `j`, `k`, and `l` for
`cov(i,j) cov(k,l) - cov(i,k) cov(j,l) = 0`. The package does not calculate
covariances or test whether a sample tetrad is zero.

Run `python examples/model_analysis.py` for executable examples of all three
areas plus ordinary-DAG equivalence.
