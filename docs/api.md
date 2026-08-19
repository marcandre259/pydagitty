# Public API Reference

This reference describes the API currently exported by `pydagitty.__all__` and
every public method and property on `Graph`. It documents the callable source
as it exists in this repository. See [Compatibility](compatibility.md) for the
0.x change policy and [Mixed-Graph Caveats](guides/mixed-graph-caveats.md)
before using MAG, PDAG, or PAG results.

## Maturity Labels

| Label | Meaning |
| --- | --- |
| **Supported** | Part of the intended 0.x compatibility surface. DAG/ADMG behavior receives the strongest correctness claim. |
| **Preview** | Usable with the stated preconditions, but mixed-graph evidence and API stability are narrower. Applies to MAG and PDAG semantics. |
| **Experimental** | May change as theory coverage improves. Applies to PAG semantics and especially the pinned circle-to-tail approximation. |
| **Provisional** | Exported to represent internal/transformation results; not promised as a general-purpose graph API. Applies to `GRAPH` and `DIGRAPH`. |

Maturity belongs to both a symbol and the graph family on which it operates.
For example, `Graph.dseparated()` is a supported method on a `DAG`, preview on
certified `MAG` and `PDAG` inputs, and experimental on a `PAG`.

## Common Conventions

- A node-set argument accepts one `Node` or an iterable of `Node`. Bare strings
  are rejected. Unknown identifiers raise `UnknownNodeError`.
- Graphs are mutable and insertion ordered. Nodes and edges are immutable.
- Mutation methods return `self`; transformations return independent graphs.
- `NodeSet` is immutable, compares as a mathematical set, and retains its
  construction order for iteration.
- A bounded search returns `EnumerationResult(items, truncated)`. `truncated`
  is `True` only when at least one additional result was found beyond the
  bound. `max_results=0` requests no search and returns an empty,
  non-truncated result. `None` removes the result bound and can be expensive.
- Invalid Python values raise `TypeError` or `ValueError`. Package-specific
  graph failures use the exceptions described below.
- Status properties are graph-owned and independent. Assigning a status
  replaces that complete status set.

## Graph Families

| Class | Maturity | Accepted endpoint forms | Contract |
| --- | --- | --- | --- |
| `DAG` | Supported | directed (`->`) and bidirected (`<->`) | Dagitty-style DAG. With bidirected edges, this is commonly called an ADMG. Directed cycles are invalid. |
| `MAG` | Preview | directed, bidirected, undirected | Inputs must be caller-certified as ancestral and maximal. `validate()` does not certify either property. |
| `PDAG` | Preview | directed, bidirected, undirected | Individual operations impose extension or completed-PDAG requirements. Merely constructing a `PDAG` does not establish them. |
| `PAG` | Experimental | all tail, arrow, and circle endpoint pairs | No complete PAG validity or m-separation implementation. Some methods use a pinned circle-to-tail approximation. |
| `GRAPH` | Provisional | undirected only | Undirected result type used by skeletons, moralization, components, and separators. |
| `DIGRAPH` | Provisional | all endpoint pairs | Permissive internal/result representation. No general-purpose semantic stability promise. |
| `Graph` | Supported object surface | selected by `GraphType`; defaults to `DIGRAPH` | Prefer a concrete causal graph class. Semantics and maturity follow the declared type. |

## Export Inventory

Every name below is in `pydagitty.__all__`.

| Symbol | Maturity | Purpose and scope |
| --- | --- | --- |
| `Node` | Supported | Immutable, case-sensitive node identifier. |
| `Edge` | Supported | Immutable edge with one `Endpoint` at each incidence. |
| `Endpoint` | Supported | `TAIL`, `ARROW`, or `CIRCLE`; circle semantics are experimental. |
| `PathExpression` | Supported | Immutable construction DSL value. |
| `NodeSet` | Supported | Immutable set with deterministic iteration order. |
| `Path` | Supported | Exact path, including the chosen edge at every segment. |
| `EnumerationResult` | Supported | Bounded result sequence and truncation flag. |
| `ConditionalIndependence` | Supported | Setwise `left`, `right`, and `given` statement. |
| `Instrument` | Supported | Graphical instrument and conditioning set for a linear effect. |
| `Canonicalization` | Supported | Canonical graph plus generated latent and selection nodes. |
| `Tetrad` | Supported | Four-node covariance constraint record. |
| `GraphType` | Supported | Declared family enum; members carry the family maturity above. |
| `NodeStatus` | Supported | `EXPOSURE`, `OUTCOME`, `LATENT`, `ADJUSTED`, or `SELECTED`. |
| `Graph` | Supported | Base object API; prefer concrete classes for inputs. |
| `DAG` | Supported | Directed/bidirected Dagitty-style DAG class. |
| `MAG` | Preview | Caller-certified MAG class. |
| `PDAG` | Preview | Partially directed graph class. |
| `PAG` | Experimental | Partial ancestral graph class with limited theory support. |
| `GRAPH` | Provisional | Internal undirected result class. |
| `DIGRAPH` | Provisional | Internal permissive result class. |
| `PyDagittyError` | Supported | Base package exception. |
| `InvalidEdgeError` | Supported | Malformed, stale, absent, or type-incompatible edge. |
| `InvalidGraphError` | Supported | Graph violates a declared or operation-specific requirement. |
| `UnknownNodeError` | Supported | Node identifier is not owned by the graph. |
| `UnsupportedGraphTypeError` | Supported | Operation is unavailable for the declared graph family. |
| `nodes` | Supported | Convenience node factory, not a graph parser. |
| `has_arrowhead` | Supported | Test an edge incidence for an arrow endpoint. |
| `has_tail` | Supported | Test an edge incidence for a tail endpoint. |
| `has_circle` | Supported | Test an edge incidence for a circle endpoint. |
| `reachable_nodes` | Supported | DAG/ADMG reachability; preview for MAG/PDAG, experimental PAG approximation. |
| `is_path_open` | Supported | DAG/ADMG exact-path openness; preview for MAG/PDAG; PAG unsupported. |
| `connected_components` | Provisional | Components of an undirected `GRAPH`. |
| `minimal_separators` | Provisional | Minimal vertex separators of an undirected `GRAPH`. |
| `complete_dag` | Supported | Complete ordinary DAG in a supplied topological order. |
| `random_dag` | Supported | Reproducible ordinary DAG generator using an explicit RNG. |
| `vanishing_tetrads` | Supported | DAG/ADMG graphical tetrads for linear SEMs. |

## Value Objects and Enums

### `Node(identifier: str)`

Identity is the exact, case-sensitive, nonempty string. Equal nodes can be
used to address a graph-owned node. Non-string identifiers raise `TypeError`;
the empty string raises `ValueError`.

### `Endpoint`

`Endpoint.TAIL`, `Endpoint.ARROW`, and `Endpoint.CIRCLE` describe incidences,
not whole edges. Use `edge.endpoint_at(node)` rather than relying on canonical
storage order.

### `Edge(node1, node2, left=Endpoint.TAIL, right=Endpoint.ARROW)`

Nodes must be `Node` instances and must differ. Storage is canonicalized by
identifier while endpoint incidence is preserved. Public attributes and
helpers are `node1`, `node2`, `left`, `right`, `left_node`, `right_node`,
`left_endpoint`, `right_endpoint`, `nodes`, `endpoint_at(node)`,
`other(node)`, and `with_nodes(node1, node2)`. A self-edge or incompatible
replacement raises `InvalidEdgeError`; a nonincident lookup raises
`ValueError`.

### `PathExpression(nodes, endpoints)`

Construction-only immutable path. `first`, `cursor`, and `edges` expose its
first node, final node, and materialized segments. Operators create expressions:

| Expression | Edge |
| --- | --- |
| `A >> B` | `A -> B` |
| `A << B` | `A <- B` |
| `A @ B` | `A <-> B` |
| `A - B` | `A -- B` |

There is no circle operator; use `Edge` explicitly. Parenthesize complex
expressions for readability.

### `NodeSet(nodes=())`

Deduplicates `Node` values while preserving first occurrence for iteration.
It supports set equality, hashing, length, membership, iteration, and
`as_frozenset()`.

### `EnumerationResult(items=(), truncated=False)`

An immutable, indexable, iterable result. `items` is a tuple. A false
`truncated` means the search was exhausted under the requested operation, or
that `max_results=0` deliberately skipped it; it does not certify the input
model or the causal theorem used by an experimental operation.

### Result Records

```python
Path(nodes: tuple[Node, ...], edges: tuple[Edge, ...])
ConditionalIndependence(left, right, given=())
Instrument(node: Node, conditioning_set=())
Canonicalization(graph: Graph, latent_nodes=(), selection_nodes=())
Tetrad(i: Node, j: Node, k: Node, l: Node)
```

`ConditionalIndependence` fields are `NodeSet` values. `Instrument.given` is
an alias for `conditioning_set`. `Tetrad.nodes` returns `(i, j, k, l)` and all
four entries must be distinct. `Path` verifies exact node-edge incidence.

### `GraphType` and `NodeStatus`

`GraphType` members are `DAG`, `MAG`, `PDAG`, `PAG`, `GRAPH`, and `DIGRAPH`.
`NodeStatus` members are `EXPOSURE`, `OUTCOME`, `LATENT`, `ADJUSTED`, and
`SELECTED`.

## Top-Level Functions

### Construction and endpoint helpers

```python
nodes(specification: str | Iterable[str]) -> tuple[Node, ...]
has_arrowhead(edge: Edge, node: Node) -> bool
has_tail(edge: Edge, node: Node) -> bool
has_circle(edge: Edge, node: Node) -> bool
complete_dag(nodes: int | Iterable[Node]) -> DAG
random_dag(nodes: int | Iterable[Node], p: float = 0.5, *, rng: random.Random) -> DAG
```

`nodes("X Z Y")` splits on whitespace; an iterable preserves identifiers
exactly. The endpoint helpers propagate `TypeError` or `ValueError` from
`Edge.endpoint_at()`. Generators accept either a non-negative count, producing
`x1` through `xN`, or unique nodes in fixed topological order. `random_dag`
requires an explicit `random.Random`, validates `0 <= p <= 1`, and never uses
global random state.

### Traversal and undirected helpers

```python
reachable_nodes(graph, first, given=()) -> NodeSet
is_path_open(graph, path, *, given=()) -> bool
connected_components(graph, *, avoiding=()) -> tuple[NodeSet, ...]
minimal_separators(
    graph, first, second, *, mandatory=(), forbidden=(), max_results=None
) -> EnumerationResult[NodeSet]
```

`reachable_nodes` supports `DAG`, `MAG`, `PDAG`, and `PAG`; PAG circles are
treated as tails, an experimental approximation. `is_path_open` supports
`DAG`, `MAG`, and `PDAG`, classifies only internal nodes, and requires every
path edge to belong to the graph. The undirected helpers require `GRAPH` and
are provisional. Wrong families raise `UnsupportedGraphTypeError`; invalid
limits raise `TypeError` or `ValueError`.

### Tetrads

```python
vanishing_tetrads(
    graph: Graph, *, kind: str = "all", max_results: int | None = None
) -> EnumerationResult[Tetrad]
```

Supports `DAG` only, including its bidirected shorthand. `kind` is `"all"`,
`"within"`, `"between"`, or `"epistemic"`. Marked latent nodes are excluded
from observed quadruples. Results are generic vanishing covariance constraints
under the documented linear-SEM trek criterion, not fitted or tested
statistics. Other graph types raise `UnsupportedGraphTypeError`; invalid
graphs, kinds, and limits fail before returning results.

## Graph Construction and Properties

```python
Graph(graph_type: GraphType | None = None, *, nodes=(), edges=(), paths=())
DAG(graph_type: GraphType | None = None, *, nodes=(), edges=(), paths=())
MAG(graph_type: GraphType | None = None, *, nodes=(), edges=(), paths=())
PDAG(graph_type: GraphType | None = None, *, nodes=(), edges=(), paths=())
PAG(graph_type: GraphType | None = None, *, nodes=(), edges=(), paths=())
GRAPH(graph_type: GraphType | None = None, *, nodes=(), edges=(), paths=())
DIGRAPH(graph_type: GraphType | None = None, *, nodes=(), edges=(), paths=())
```

Edges and path nodes are registered automatically. Construction is atomic for
the supplied edge/path batch. Omit `graph_type` for concrete classes; they have
a fixed type, accept only the matching enum when it is supplied, and raise
`ValueError` for a conflict. Endpoint incompatibility or a self-edge raises
`InvalidEdgeError`.

| Property/protocol | Result and semantics |
| --- | --- |
| `type`, `graph_type` | Declared `GraphType`; aliases. |
| `nodes`, `edges` | Insertion-ordered tuples. |
| `node_attributes`, `edge_attributes` | Read-only nested mapping views. Nested attribute values themselves are not frozen. |
| `exposures`, `outcomes`, `latents`, `adjusted_nodes`, `selected_nodes` | Get a `NodeSet`; assignment replaces the status membership. |
| `len(graph)`, iteration, `node in graph` | Node count, insertion-order iteration, and identifier-based `Node` membership. |

## Graph Methods

All methods below are available through `Graph`; unsupported declared types
fail as stated. In scope columns, **S**, **P**, **E**, and **V** mean supported,
preview, experimental, and provisional. `all` means the method is structurally
available on every family, but its semantic maturity still follows that family.

### Lookup and Mutation

| Signature | Scope | Result and failure semantics |
| --- | --- | --- |
| `node(identifier: str) -> Node` | all | Returns the owned node; `UnknownNodeError` if absent. |
| `add_node(node, **attributes) -> Graph` | all | Idempotently adds/updates and returns `self`; non-`Node` raises `TypeError`. |
| `add_edge(edge, **attributes) -> Graph` | all | Adds endpoints and edge, or updates attributes of an equal edge; incompatible endpoints raise `InvalidEdgeError`. |
| `append_path(*paths) -> Graph` | all | Atomically adds all path segments; wrong values raise `TypeError`, incompatible segments `InvalidEdgeError`. |
| `has_edge(edge) -> bool` | all | False for absent or endpoint-unowned edges; malformed argument raises `TypeError`. |
| `remove_edge(edge) -> Graph` | all | Removes an exact edge; absent/stale edge raises `InvalidEdgeError`. |
| `remove_node(node) -> Graph` | all | Removes node, incident edges, metadata, and statuses; unknown node raises `UnknownNodeError`. |
| `reverse_edge(edge) -> Graph` | all | Reverses only strict directed edges and migrates metadata; non-directed, absent, or colliding reversal raises `InvalidEdgeError`. |
| `set_node_attributes(node, **attributes) -> Graph` | all | Updates owned-node metadata; unknown node raises `UnknownNodeError`. |
| `set_edge_attributes(edge, **attributes) -> Graph` | all | Updates exact-edge metadata; absent edge raises `InvalidEdgeError`. |
| `set_status(status, nodes) -> Graph` | all | Replaces one status set; wrong status raises `TypeError`, unknown node `UnknownNodeError`. |
| `status(status) -> NodeSet` | all | Returns one status set; wrong status raises `TypeError`. |

### Incidence, Relationships, and Ancestry

These methods inspect exact endpoint marks. They do not certify that a MAG,
PDAG, or PAG has the corresponding mathematical global properties.

| Signature | Scope | Result and failure semantics |
| --- | --- | --- |
| `incident_edges(nodes) -> tuple[Edge, ...]` | all | Union of incident edges in graph order. |
| `edges_between(first, second) -> tuple[Edge, ...]` | all | All parallel endpoint-defined edges; empty for the same node. |
| `parents(nodes) -> NodeSet` | all | Strict tail-to-arrow parents. |
| `children(nodes) -> NodeSet` | all | Strict tail-to-arrow children. |
| `spouses(nodes) -> NodeSet` | all | Arrow-to-arrow neighbors. |
| `neighbours(nodes) -> NodeSet` | all | Tail-to-tail neighbors. |
| `neighbors(nodes) -> NodeSet` | all | US spelling alias of `neighbours`. |
| `possible_parents(nodes) -> NodeSet` | all | Endpoint-local possible parents. |
| `possible_children(nodes) -> NodeSet` | all | Endpoint-local possible children. |
| `possible_neighbours(nodes) -> NodeSet` | all | Endpoint-local possible undirected neighbors. |
| `possible_neighbors(nodes) -> NodeSet` | all | US spelling alias. |
| `adjacent_nodes(nodes) -> NodeSet` | all | Nodes sharing any edge. |
| `adjacent(first, second) -> bool` | all | Whether any edge joins the pair. |
| `ancestors(nodes, *, proper=False) -> NodeSet` | all | Closure over strict parents; includes seeds unless `proper=True`. |
| `descendants(nodes, *, proper=False) -> NodeSet` | all | Closure over strict children. |
| `possible_ancestors(nodes, *, proper=False) -> NodeSet` | all | Closure over possible parents. |
| `possible_descendants(nodes, *, proper=False) -> NodeSet` | all | Closure over possible children. |
| `anteriors(nodes, *, proper=False) -> NodeSet` | all | Alias of `possible_ancestors`. |
| `posteriors(nodes, *, proper=False) -> NodeSet` | all | Alias of `possible_descendants`. |
| `exogenous_variables() -> NodeSet` | all | Nodes without strict parents. |

All node arguments in this table are resolved first; wrong values raise
`TypeError` and unknown nodes raise `UnknownNodeError`.

### Validation and DAG Queries

| Signature | Scope | Result and failure semantics |
| --- | --- | --- |
| `find_cycle() -> tuple[Node, ...] | None` | all | First deterministic strict directed cycle, closed by repeating its first node. |
| `is_acyclic() -> bool` | all | Whether strict directed edges have no cycle. |
| `validate() -> bool` | S/P/E/V by family | Returns `True` after endpoint/self-edge and family cycle checks; raises `InvalidGraphError` on failure. It never certifies MAG maximality/ancestrality, PAG validity, or CPDAG validity. |
| `topological_ordering() -> tuple[Node, ...]` | DAG S | Insertion-order-tied strict directed ordering; non-DAG raises `UnsupportedGraphTypeError`, cycle `InvalidGraphError`. Bidirected edges do not contribute indegree. |
| `is_collider(first, middle, last) -> bool` | DAG S | Tests strict `first -> middle <- last`; non-DAG raises `UnsupportedGraphTypeError`. |
| `markov_blanket(nodes) -> NodeSet` | DAG S | DAG parents, children, and co-parents; non-DAG raises `UnsupportedGraphTypeError`. |

### Copying and Structural Transformations

| Signature | Scope | Result and failure semantics |
| --- | --- | --- |
| `clone() -> Graph` | all | Deep-copies graph-owned metadata into an independent same-type graph. |
| `copy() -> Graph` | all | Alias of `clone`. |
| `merge(*others) -> Graph` | all | Returns a merged clone; inputs must be `Graph` objects of exactly the same declared type. |
| `induced_subgraph(nodes) -> Graph` | all | Same-type node-induced copy with retained metadata/statuses. |
| `induced(nodes) -> Graph` | all | Alias of `induced_subgraph`. |
| `edge_induced_subgraph(edges) -> Graph` | all | Same-type exact-edge-induced copy; absent edges raise `InvalidEdgeError`. |
| `edge_induced(edges) -> Graph` | all | Alias of `edge_induced_subgraph`. |
| `skeleton() -> GRAPH` | input maturity by family; result V | Undirected copy; parallel edges collapse to one edge without mutating the source. |
| `ancestor_graph(nodes=None) -> Graph` | DAG S; MAG/PDAG P | Induced anterior graph. Default seeds are exposures, outcomes, and adjusted nodes. PAG/GRAPH/DIGRAPH raise `UnsupportedGraphTypeError`. |
| `canonicalize() -> Canonicalization` | DAG S; MAG P | Returns a DAG replacing bidirected edges with generated latent parents and undirected edges with generated selected colliders. Other families raise `UnsupportedGraphTypeError`; unsupported endpoint forms raise `InvalidGraphError`. |
| `moralize() -> GRAPH` | DAG S; MAG/PDAG P; GRAPH V | Returns an undirected moral graph; unsupported families raise `UnsupportedGraphTypeError`. |
| `backdoor_graph(exposure=None, outcome=None) -> Graph` | DAG S; MAG/PDAG P; PAG E | Removes visible first edges on proper possibly causal paths. Empty effect sets return an unchanged clone. MAG/PAG require caller certification; PAG uses partial circle-to-tail handling. |
| `indirect_graph(exposure=None) -> Graph` | DAG S; MAG/PDAG P; PAG E | Removes strict direct exposure-to-status-outcome edges. The outcome comes from `graph.outcomes`; unsupported noncausal families raise `UnsupportedGraphTypeError`. |
| `structural_part() -> Graph` | DAG S; DIGRAPH V | Subgraph induced by nodes marked latent. |
| `measurement_part() -> Graph` | DAG S; DIGRAPH V | Keeps directed edges with observed children and bidirected edges with two observed ends. |
| `to_mag() -> MAG` | DAG S; result P | Latent projection. Requires an acyclic DAG and no selected nodes; otherwise `InvalidGraphError`. It does not perform selection projection. |

Transformations preserve retained node attributes and statuses. Exact retained
edges preserve attributes; generated or endpoint-changed edges can discard
coefficient/layout keys. Do not infer statistical parameter transport from a
graph transformation.

### Visualization

```python
to_graphviz(
    *, name=None, engine="dot", format="svg", graph_attr=None,
    node_attr=None, edge_attr=None, show_statuses=True
) -> graphviz.Digraph
```

Supported as an adapter for every graph family, with endpoint meaning inherited
from that family's maturity. It preserves isolated nodes, parallel edges, and
endpoint marks without mutating the graph. The optional Python package is
required even to produce DOT source:

```bash
python -m pip install 'pydagitty[viz]'
```

Rendering or displaying additionally needs the Graphviz `dot` executable.
Missing Python support raises `ModuleNotFoundError`; a non-boolean
`show_statuses` raises `TypeError`. DOT output is presentation, not a stable
serialization format.

### Separation and Paths

| Signature | Scope | Result and failure semantics |
| --- | --- | --- |
| `dconnected(first, second, given=()) -> bool` | DAG S; MAG/PDAG P; PAG E | Whether any source is m-connected to a target. Endpoints and `given` must be disjoint; statuses are ignored. PAG circles become tails. |
| `dseparated(first, second, given=()) -> bool` | same | Boolean complement of `dconnected`. An empty target set is separated. |
| `iter_paths(first, second, *, directed=False, given=(), open_only=False, max_results=100) -> Iterator[Path]` | DAG S; MAG/PDAG P | Snapshot-based deterministic simple-path iterator. `directed=True` follows strict children; `open_only` filters using `given`. It cannot report truncation. |
| `paths(first, second, *, directed=False, given=(), open_only=False, max_results=100) -> EnumerationResult[Path]` | DAG S; MAG/PDAG P | Materializes paths and reports truncation. Parallel edges produce distinct paths. |

PAG paths raise `UnsupportedGraphTypeError`. Wrong boolean/limit values raise
`TypeError`; negative limits raise `ValueError`. See
[Separation and Paths](guides/separation-and-paths.md).

### Equivalence and Orientation

| Signature | Scope | Result and failure semantics |
| --- | --- | --- |
| `orient_pdag() -> DAG` | PDAG P | First deterministic compatible acyclic extension. Requires a simple directed/undirected PDAG; impossible orientation raises `InvalidGraphError`. It does not require a completed PDAG. |
| `equivalence_class() -> PDAG` | ordinary DAG S; result P | CPDAG of a simple, fully directed, acyclic DAG. Bidirected/parallel/undirected structure raises `InvalidGraphError`. |
| `equivalent_dags(*, max_results=100) -> EnumerationResult[DAG]` | ordinary DAG S; CPDAG P | Enumerates deterministic Markov-equivalent DAGs. A PDAG input must be a completed PDAG; invalid structure raises `InvalidGraphError`. |

### Adjustment

```python
is_adjustment_set(
    nodes, *, exposure=None, outcome=None, effect="total"
) -> bool

adjustment_sets(
    *, exposure=None, outcome=None, effect="total", mode="minimal",
    max_results=None
) -> EnumerationResult[NodeSet]
```

Total-effect scope is DAG **Supported**, MAG/PDAG **Preview**, and PAG
**Experimental**. MAG/PAG inputs must be caller-certified and contain no
undirected edges; PDAG orientation must be possible. Direct-effect scope is
DAG only and selected nodes are rejected.

Effect arguments override statuses. Otherwise nonempty, disjoint exposure and
outcome statuses are required. Exposure/outcome nodes cannot also be latent,
adjusted, or selected; adjusted and selected nodes cannot be latent. Existing
adjusted nodes are mandatory, selected nodes are fixed conditioning and never
returned, and latent/forbidden nodes cannot be returned. `effect` is `"total"`
or `"direct"`; enumeration `mode` is `"minimal"`, `"canonical"`, or `"all"`.
Detectable invalid models or roles raise `InvalidGraphError`; wrong families
raise `UnsupportedGraphTypeError`; invalid options/limits raise
`ValueError`/`TypeError`. A false result or empty exhausted enumeration means
no set met the implemented graphical criterion, not that an effect is zero.
See [Adjustment](guides/adjustment.md).

### Implications, Instruments, and Tetrads

| Signature | Scope | Result and failure semantics |
| --- | --- | --- |
| `implied_conditional_independencies(*, mode="missing_edge", max_results=None) -> EnumerationResult[ConditionalIndependence]` | DAG S; MAG/PDAG P | Modes: `missing_edge`, `basis_set`, `all_pairs`. Latent/selected endpoints are excluded; selected nodes are fixed in `.given`. `basis_set` rejects selected nodes. Invalid graph/type/mode/limit fails explicitly. |
| `instrumental_variables(*, exposure=None, outcome=None) -> list[Instrument]` | DAG S | Requires exactly one distinct exposure and outcome, from arguments or statuses. Returns the first deterministic qualifying conditioning set per candidate. Invalid roles/model raise `InvalidGraphError`; non-DAG raises `UnsupportedGraphTypeError`. |
| `vanishing_tetrads(*, kind="all", max_results=None) -> EnumerationResult[Tetrad]` | DAG S | Method form of top-level `vanishing_tetrads`; same semantics and failures. |

Instrument output establishes the implemented graphical exclusion and relevance
criterion for a total effect. Use as an IV also requires a linear structural
model and homogeneous effect assumptions. Neither instruments, implications,
adjustment sets, nor tetrads estimate or statistically test an effect.

## Exceptions

```text
PyDagittyError
|- InvalidEdgeError
|- InvalidGraphError
|- UnknownNodeError
`- UnsupportedGraphTypeError
```

- `InvalidEdgeError`: malformed, absent, stale, self, colliding, or endpoint-
  incompatible edge operation.
- `InvalidGraphError`: locally detectable graph or algorithm precondition
  failure, including cycles, invalid role combinations, or an invalid CPDAG.
- `UnknownNodeError`: query/status input has no graph-owned identifier.
- `UnsupportedGraphTypeError`: operation does not accept the declared family.
- `TypeError` and `ValueError`: ordinary Python type and option/domain errors.

## Complete Examples

- [Constructing Graphs](guides/constructing-graphs.md)
- [Separation and Paths](guides/separation-and-paths.md)
- [Adjustment](guides/adjustment.md)
- [Transformations and Equivalence](guides/transformations-and-equivalence.md)
- [Implications, Instruments, and Tetrads](guides/implications-instruments-and-tetrads.md)
- Executable [confounding workflow](../examples/confounding_workflow.py)
- Executable [model-analysis workflow](../examples/model_analysis.py)
