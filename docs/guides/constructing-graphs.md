# Constructing Graphs

PyDagitty uses typed objects rather than Dagitty's graph-string syntax. This
guide builds a confounded causal graph entirely through the public object API.

## Choose the Family

Use `DAG` for the supported release path. Dagitty-style `DAG` permits both
directed and bidirected edges. A directed/bidirected acyclic graph is often
called an ADMG in the literature. `MAG` and `PDAG` are preview, `PAG` is
experimental, and `GRAPH`/`DIGRAPH` are provisional result types.

## Nodes and Paths

```python
from pydagitty import DAG, nodes

Z, X, M, Y = nodes("Z X M Y")
graph = DAG(paths=[Z >> X, Z >> Y, X >> M >> Y])
graph.exposures = X
graph.outcomes = Y

assert graph.validate()
assert graph.parents(X) == {Z}
assert graph.children(X) == {M}
```

`nodes()` is only a convenience factory. Identifiers are exact,
case-sensitive strings. A graph resolves an equal external `Node` by
identifier, but querying an unknown node raises `UnknownNodeError`.

Path operators are:

| Python | Meaning |
| --- | --- |
| `A >> B` | `A -> B` |
| `A << B` | `A <- B` |
| `A @ B` | `A <-> B` |
| `A - B` | `A -- B` |

`DAG` accepts `->` and `<->`, not `--`. Parenthesize mixed operators in complex
expressions. Circles have no operator:

```python
from pydagitty import Edge, Endpoint, PAG

A, B = nodes("A B")
pag = PAG(edges=[Edge(A, B, Endpoint.CIRCLE, Endpoint.ARROW)])
```

That constructs an experimental PAG object; it does not certify that the PAG
is graph-theoretically valid.

## Explicit Edges and Metadata

```python
from pydagitty import Edge, Endpoint

confounding = Edge(X, Y, Endpoint.ARROW, Endpoint.ARROW)
admg = DAG(paths=[X >> Y]).add_edge(confounding, note="unobserved common cause")

assert admg.spouses(X) == {Y}
assert admg.edge_attributes[confounding]["note"] == "unobserved common cause"
```

An `Edge` is canonicalized by node identifier while preserving endpoint
incidence. Use `edge.endpoint_at(node)`, not `node1`/`node2` order, to interpret
direction. Different endpoint-defined edges may be parallel. Self-edges are
rejected.

Node and edge metadata are descriptive, not inputs to causal algorithms unless
a specific method says otherwise. Public metadata mappings are read-only views;
use `set_node_attributes()` and `set_edge_attributes()` to update them.

## Statuses

```python
graph.latents = ()
graph.adjusted_nodes = Z
graph.selected_nodes = ()

assert graph.adjusted_nodes == {Z}
```

The five statuses are independent: exposure, outcome, latent, adjusted, and
selected. Assignment replaces the whole set. Algorithms interpret statuses
differently:

- separation and paths use only explicit `given`;
- adjustment arguments override exposure/outcome statuses, adjusted nodes are
  mandatory, and selected nodes are fixed conditioning;
- instruments require one exposure and one outcome;
- implied independencies hide latent and selected endpoints.

Contradictory statuses can be represented for inspection but effect-analysis
methods reject invalid combinations.

## Mutation and Copies

```python
Q = nodes("Q")[0]
graph.add_node(Q, label="unrelated")
copy = graph.clone()
copy.remove_node(Q)

assert Q in graph
assert Q not in copy
```

`add_node`, `add_edge`, `append_path`, removals, reversal, metadata setters,
and status setters mutate and return the graph. `clone`, subgraphs, and causal
transformations return independent graphs. Batch path insertion is atomic if
an endpoint form is invalid.

## Visualization

Install the optional Python adapter:

```bash
python -m pip install 'pydagitty[viz]'
```

Then produce DOT without rendering:

```python
dot = graph.to_graphviz(graph_attr={"rankdir": "LR"})
print(dot.source)
```

Creating DOT needs the Python `graphviz` package. Rendering or notebook display
also needs the Graphviz system `dot` executable. `to_graphviz()` preserves
isolated nodes, parallel edges, endpoint marks, and optional status styling,
but its DOT is not a stable interchange format.

The complete dependency-free construction and analysis workflow is executable
as `python examples/confounding_workflow.py` from an installed or editable
checkout.
