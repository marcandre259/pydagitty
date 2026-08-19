# Adjustment

Adjustment methods identify covariate sets under graphical criteria. They do
not estimate a causal effect, choose an estimator, inspect data, or guarantee
that consistency, positivity, and measurement assumptions hold.

## A Confounded Total Effect

```python
from pydagitty import DAG, nodes

Z, X, Y = nodes("Z X Y")
graph = DAG(paths=[Z >> X, Z >> Y, X >> Y])
graph.exposures = X
graph.outcomes = Y

result = graph.adjustment_sets(mode="minimal", max_results=20)
assert result.items == ({Z},)
assert not result.truncated
assert graph.is_adjustment_set(Z)
assert not graph.is_adjustment_set(())
```

Arguments can override statuses:

```python
assert graph.is_adjustment_set(Z, exposure=X, outcome=Y, effect="total")
```

Exposure and outcome sets must be nonempty and disjoint. They cannot also be
latent, adjusted, or selected. Adjusted and selected nodes cannot be latent.
Invalid combinations raise `InvalidGraphError` instead of returning `False`.

## Modes

`mode="minimal"` returns sets minimal after honoring mandatory adjusted nodes.
`mode="canonical"` tests the canonical ancestor-based candidate set.
`mode="all"` enumerates every valid observed candidate subset in cardinality
and graph order and can be exponential.

```python
Q = nodes("Q")[0]
graph.add_node(Q)
all_sets = graph.adjustment_sets(mode="all", max_results=1)
assert len(all_sets) == 1
assert all_sets.truncated
```

Never assume a bounded prefix is complete. Increase `max_results` or use
`None` only when the candidate space is tractable. `max_results=0` deliberately
performs no search and returns `truncated=False`.

## Status Semantics

- `adjusted_nodes` are mandatory members of every returned set.
- `selected_nodes` are fixed conditioning for total-effect analysis and are not
  returned as adjustment covariates.
- latent nodes cannot be returned.
- exposures, outcomes, and forbidden possible descendants cannot be returned.
- no status is inferred from node metadata or names.

An empty `items` tuple with `truncated=False` means no set met the implemented
criterion under these roles. It does not mean the causal effect is zero.

## Direct Effects

```python
X, M, Y, Z = nodes("X M Y Z")
direct_graph = DAG(paths=[X >> M >> Y, X >> Y, Z >> X, Z >> Y])
direct = direct_graph.adjustment_sets(
    exposure=X, outcome=Y, effect="direct", max_results=20
)
assert direct.items == ({M, Z},)
```

Direct-effect adjustment is supported only for `DAG` and rejects selected
nodes. It uses the indirect graph and a single-door criterion. Calling it on a
MAG, PDAG, PAG, GRAPH, or DIGRAPH raises `UnsupportedGraphTypeError`.

## Mixed-Graph Scope

Total-effect adjustment is:

| Family | Maturity and preconditions |
| --- | --- |
| DAG/ADMG | Supported; `validate()` must pass. |
| MAG | Preview; caller-certified valid MAG, no undirected edge. |
| PDAG | Preview; local validation and a compatible acyclic orientation must succeed, while the criterion retains partial-graph semantics. |
| PAG | Experimental; caller-certified valid PAG, no undirected edge, with incomplete pinned approximation behavior. |

`validate()` is not MAG/PAG certification. A result from an endpoint-compatible
mixed graph does not upgrade that input to a valid model. See
[Mixed-Graph Caveats](mixed-graph-caveats.md).
