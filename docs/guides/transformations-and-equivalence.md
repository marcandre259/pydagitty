# Transformations and Equivalence

Graph transformations return independent objects and preserve the source.
They carry retained statuses and metadata where meaningful, but endpoint-
changing/generated edges can drop coefficient, style, or control-point keys.

## Ancestors, Back-Door, and Moral Graphs

```python
from pydagitty import DAG, nodes

Z, X, M, Y, Q = nodes("Z X M Y Q")
graph = DAG(nodes=[Q], paths=[Z >> X, Z >> Y, X >> M >> Y])
graph.exposures = X
graph.outcomes = Y

ancestral = graph.ancestor_graph()
backdoor = graph.backdoor_graph()
moral = ancestral.moralize()

assert Q not in ancestral
assert not backdoor.has_edge(next(edge for edge in graph.edges if X in edge.nodes and M in edge.nodes))
assert X in graph and M in graph.children(X)  # Source unchanged.
assert moral.adjacent(Z, X)
```

`ancestor_graph()` supports DAG (supported) and MAG/PDAG (preview). With no
argument it seeds exposures, outcomes, and adjusted nodes. `moralize()` also
supports MAG/PDAG at preview maturity and provisional `GRAPH` as an identity
case. It returns a provisional undirected `GRAPH` suitable for internal
separator operations, not a general stable graph framework.

`backdoor_graph()` supports DAG, MAG, PDAG, and PAG with family maturity. It
removes visible first edges of proper possibly causal paths. MAG/PAG visibility
requires caller-certified models; PAG handling is experimental.

`indirect_graph()` removes strict direct edges from the requested exposures to
nodes currently marked as outcomes. Set `graph.outcomes` before using it
directly.

## Canonicalization and Latent Projection

```python
from pydagitty import Edge, Endpoint

A, B = nodes("A B")
admg = DAG(edges=[Edge(A, B, Endpoint.ARROW, Endpoint.ARROW)])
canonical = admg.canonicalize()

assert len(canonical.latent_nodes) == 1
assert canonical.graph.latents == set(canonical.latent_nodes)
```

`canonicalize()` supports DAG and preview MAG inputs. It replaces each
bidirected edge with a generated latent common parent and each undirected MAG
edge with a generated selected collider, returning `Canonicalization`.

`to_mag()` is DAG-only latent projection:

```python
L, A, B = nodes("L A B")
source = DAG(paths=[L >> A, L >> B])
source.latents = L
projected = source.to_mag()

assert projected.has_edge(Edge(A, B, Endpoint.ARROW, Endpoint.ARROW))
assert L not in projected
```

The returned `MAG` is preview. `to_mag()` requires an acyclic DAG and rejects
selected nodes because selection projection is not implemented. It does not
certify arbitrary external MAGs.

## Structural and Measurement Parts

`structural_part()` returns the subgraph induced by latent-status nodes.
`measurement_part()` retains directed edges with observed children and
bidirected edges whose ends are both observed. They support DAG and provisional
DIGRAPH only; status assignment defines "latent" for these transformations.

## Ordinary DAG Equivalence

Dagitty-style DAG permits bidirected edges, but ordinary Markov equivalence here
requires a simple, fully directed, acyclic DAG.

```python
A, B, C = nodes("A B C")
chain = DAG(paths=[A >> B >> C])
cpdag = chain.equivalence_class()
equivalents = cpdag.equivalent_dags(max_results=10)

assert len(equivalents) == 3
assert not equivalents.truncated
assert all(candidate.is_acyclic() for candidate in equivalents)
```

`equivalence_class()` returns a preview `PDAG` CPDAG. Bidirected edges,
parallel adjacency, incomplete direction, or a cycle raise `InvalidGraphError`.

`equivalent_dags()` accepts an ordinary DAG or a preview PDAG that is actually
a completed PDAG. An arbitrary extendable PDAG is not sufficient. The method
checks that a PDAG maps back to the same CPDAG and raises `InvalidGraphError`
otherwise.

`orient_pdag()` has a different contract: it returns the first deterministic
compatible acyclic extension of a simple directed/undirected PDAG and does not
require completion. It is preview and can raise `InvalidGraphError` when no
orientation works.

Equivalence enumeration can be exponential. Inspect `truncated`; a bounded
result is only a prefix of the equivalence class.
