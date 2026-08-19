# Separation and Paths

Separation answers whether any open route connects node sets under explicit
conditioning. Path enumeration explains individual routes. These operations do
not use `adjusted_nodes` or `selected_nodes` implicitly.

## Chain, Fork, and Collider

```python
from pydagitty import DAG, nodes

A, B, C, D = nodes("A B C D")
chain = DAG(paths=[A >> B >> C])
collider = DAG(paths=[A >> B << C, B >> D])

assert chain.dconnected(A, C)
assert chain.dseparated(A, C, given=B)
assert collider.dseparated(A, C)
assert collider.dconnected(A, C, given=B)
assert collider.dconnected(A, C, given=D)
```

A conditioned non-collider closes a path. A collider opens when it or a strict
directed descendant is conditioned on. Inputs can be node sets; connection is
true when any source reaches any target. Endpoint sets and `given` must be
disjoint; overlap raises `InvalidGraphError` rather than assigning nonstandard
semantics to a conditioned query endpoint.

Scope is supported for `DAG`/ADMG, preview for caller-certified `MAG` and
`PDAG`, and experimental for `PAG`. PAG separation replaces every circle with
a tail before traversal. That pinned approximation is not complete PAG
m-separation, definite-status path analysis, or possible-m-connection.

## Inspect Paths

```python
X, Z, Y = nodes("X Z Y")
graph = DAG(paths=[Z >> X, Z >> Y, X >> Y])

result = graph.paths(X, Y, given=Z, max_results=20)
assert not result.truncated

for path in result:
    labels = tuple(node.identifier for node in path.nodes)
    print(labels, graph.dseparated(X, Y, given=Z))

open_paths = graph.paths(X, Y, given=Z, open_only=True, max_results=20)
assert [tuple(path.nodes) for path in open_paths] == [(X, Y)]
```

`paths()` returns simple paths in deterministic depth-first order. Different
parallel edges yield distinct `Path` values even if their node sequences are
equal. `directed=True` follows strict parent-to-child edges. `open_only=True`
filters with the explicit `given` set.

`is_path_open(graph, path, given=...)` classifies one exact path and checks that
its nodes and edges belong to the graph. Path operations support DAG, MAG, and
PDAG only. PAG path calls fail with `UnsupportedGraphTypeError` rather than
silently applying incomplete PAG path theory.

## Bounds and Snapshots

```python
bounded = graph.paths(X, Y, max_results=1)
if bounded.truncated:
    print("At least one path was omitted; increase max_results.")
```

Path search can be exponential. The default bound is 100. A finite limit is a
result cap, not a timeout. `truncated=True` means more paths were found than
returned. `truncated=False` means this search was exhausted. `max_results=0`
requests no search; `None` removes the cap.

`iter_paths()` avoids materializing a result and returns no truncation flag. It
captures a clone when called, before iteration begins, so later source mutation
does not affect the iterator. Use `paths()` whenever completeness reporting
matters.

## Reachability

```python
from pydagitty import reachable_nodes

reached = reachable_nodes(chain, A, given=B)
assert C not in reached
```

`reachable_nodes()` is the lower-level endpoint-aware operation behind
connection checks. It has the same DAG/MAG/PDAG/PAG scope and PAG approximation
as separation.

Separation is a graphical implication under the input model. It is not a
statistical conditional-independence test and does not establish that an
empirical distribution satisfies the implication.
