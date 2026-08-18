# PyDagitty

PyDagitty is a dependency-free Python implementation of deterministic causal
graph algorithms inspired by [Dagitty](https://github.com/jtextor/dagitty).
It uses typed Python objects rather than Dagitty's graph string language and
does not require R, JavaScript, NetworkX, or a numerical runtime.

This is a pre-alpha release. DAG functionality is the most mature. MAG, PDAG,
and especially PAG users should read [the parity and caveat reference](docs/parity.md)
before relying on results.

## Installation

PyDagitty requires Python 3.10 or newer.

```bash
python -m pip install pydagitty
```

Development releases are published automatically from `main` after CI passes.
See [the publishing guide](docs/publishing.md) for versioning and release details.

For development tools:

```bash
python -m pip install -e '.[dev]'
```

## Object API

`Node` is an immutable, hashable, case-sensitive identifier. Graphs own node
roles and mutable metadata, so the same node can have different roles in
different graphs. `Edge` and construction-time `PathExpression` values are
also immutable. Graphs are mutable, insertion ordered, and resolve equal
external nodes to their graph-owned node.

Use `nodes()` as a convenience constructor, not as a graph parser:

```python
from pydagitty import DAG, nodes

A, B, U, Y = nodes("A B U Y")
graph = DAG(paths=[A >> B << U >> Y])
graph.exposures = A
graph.outcomes = Y

assert graph.parents(B) == {A, U}
assert graph.ancestors(Y, proper=True) == {U}
```

Construction and mutation methods such as `add_node()`, `add_edge()`,
`append_path()`, `remove_node()`, `remove_edge()`, `reverse_edge()`, and
`set_status()` mutate the graph and return it for fluent use. Transformations
such as `ancestor_graph()`, `canonicalize()`, `moralize()`,
`backdoor_graph()`, and `to_mag()` return new graphs.

Graph status sets are independent and replace their previous contents when
assigned: `exposures`, `outcomes`, `latents`, `adjusted_nodes`, and
`selected_nodes`. Analysis arguments override exposure/outcome statuses where
accepted. Separation and path methods condition only on their explicit
`given` argument.

Bounded enumerations return `EnumerationResult(items, truncated)`. Package
collections have deterministic graph-insertion order; arbitrary caller-owned
sets do not promise a stable input order.

## Operators

Python has no overloadable `->`, so path expressions use:

| Python | Edge |
| --- | --- |
| `A >> B` | `A -> B` |
| `A << B` | `A <- B` |
| `A @ B` | `A <-> B` |
| `A - B` | `A -- B` |

Expressions can contain multiple segments:

```python
from pydagitty import DAG, nodes

A, B, C, U, Y = nodes("A B C U Y")
graph = DAG(paths=[A >> B << U >> Y, B @ C])
```

Shift operators have lower precedence than `@` and `-`; reflected path joins
make expressions such as `A >> B @ C` and `A >> B - C` represent their visual
paths. Parentheses are still recommended in generated or complex code.

Circle endpoints have no operator. Construct them explicitly:

```python
from pydagitty import Edge, Endpoint, PAG

pag = PAG(edges=[Edge(A, B, Endpoint.CIRCLE, Endpoint.ARROW)])
```

Self-edges are unsupported. Multiple different endpoint-defined edges between
the same two nodes are allowed.

## Analysis Examples

Separation and paths:

```python
assert graph.dseparated(A, Y)
assert graph.dconnected(A, Y, given={B})

result = graph.paths(A, Y, open_only=True, max_results=20)
for path in result:
    print([node.identifier for node in path.nodes])
print(result.truncated)
```

Adjustment sets:

```python
X, Z, Y = nodes("X Z Y")
confounded = DAG(paths=[Z >> X, Z >> Y, X >> Y])
confounded.exposures = X
confounded.outcomes = Y

sets = confounded.adjustment_sets(mode="minimal")
assert sets.items[0] == {Z}
assert confounded.is_adjustment_set({Z})
```

Generators require an explicit random number generator for reproducibility:

```python
import random
from pydagitty import complete_dag, random_dag

complete = complete_dag(4)
sample = random_dag(10, p=0.2, rng=random.Random(2026))
```

The package also provides canonicalization, moralization, latent projection,
PDAG orientation, Markov-equivalent DAG enumeration, implied conditional
independencies, graphical instrument discovery for linear effects, and
vanishing tetrads. See [docs/parity.md](docs/parity.md) for graph-family
preconditions and intentional differences from Dagitty R.

## Graph Support Caveats

- Dagitty's `DAG` terminology permits directed and bidirected edges; this is
  often called an ADMG elsewhere.
- `validate()` checks endpoint compatibility and cycles. It does not certify
  MAG maximality/ancestrality, PAG validity, or completed-PDAG validity;
  `validate(strict=True)` is not implemented.
- MAG and PAG analyses therefore require caller-certified valid input.
- PAG d-connection and back-door handling follow the pinned Dagitty behavior
  by replacing circle endpoints with tails. This is not complete PAG
  m-separation or possible-m-connection analysis.
- PAG path enumeration is unsupported. DAG, MAG, and PDAG paths are simple
  paths, with parallel edge choices retained as distinct paths.
- Direct-effect adjustment, instruments, Markov blankets, strict collider
  tests, topological ordering, and tetrads are DAG-only. Additional operation
  limits are listed in the parity reference.
- Enumerating paths, adjustment sets, independencies, equivalent DAGs, and
  tetrads can be exponential. Use `max_results`; inspect `truncated`.

## Development

Run the complete local checks from the repository root:

```bash
python -m pytest
python -m ruff check .
python -m mypy
```

Hypothesis is included in the `dev` extra for property tests. CI runs tests,
lint, and strict type checking on supported Python versions.

## Attribution and License

PyDagitty is informed by and adapts algorithms and behavioral fixtures from
Dagitty by Johannes Textor and contributors, pinned for parity work at commit
[`7a657776dc8f5e5ba4e323edb028e2c2aaf29327`](https://github.com/jtextor/dagitty/tree/7a657776dc8f5e5ba4e323edb028e2c2aaf29327).
The upstream root `LICENSE.txt` contains GPL v2, and its `r/DESCRIPTION`
declares `License: GPL-2`, which denotes version 2 only under R package
semantics.

The Python files are adaptations and reimplementations for this object API;
they are not claimed to be verbatim translations of upstream files. PyDagitty
is licensed under the GNU General Public License, version 2 only
(`GPL-2.0-only`). See [LICENSE](LICENSE).
