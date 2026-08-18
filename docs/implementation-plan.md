# PyDagitty Technical Implementation Plan

Status: Implemented pre-alpha; this document remains the parity and hardening roadmap

Target: Python 3.10+

Upstream reference: [`jtextor/dagitty`](https://github.com/jtextor/dagitty), commit `7a657776dc8f5e5ba4e323edb028e2c2aaf29327`
License: GPL-2.0-compatible; the exact SPDX expression will be fixed after auditing the notices on every translated upstream source file

## 1. Objective

PyDagitty will provide a native Python implementation of Dagitty's deterministic causal-graph algorithms and the graph-oriented portion of the Dagitty R API. It will use Python objects for graph construction instead of Dagitty's DOT-like string language, and it will not depend on NetworkX or a JavaScript runtime.

The first stable release must support the graph families accepted by the central Dagitty R algorithms:

| Graph family | Public name | Supported endpoints | Intended use |
| --- | --- | --- | --- |
| Directed acyclic mixed graph | `DAG` | `->`, `<->` | DAG analysis with optional latent-confounding shorthand |
| Maximal ancestral graph | `MAG` | `->`, `<->`, `--` | Marginal models with latent and selection variables |
| Partially directed acyclic graph | `PDAG` | `->`, `<->`, `--` | Markov-equivalence classes and uncertain directions |
| Partial ancestral graph | `PAG` | All Dagitty endpoint combinations | Equivalence classes of MAGs |

Dagitty calls a graph containing directed and bidirected edges a DAG. PyDagitty will retain that terminology for behavioral compatibility even though such a graph is often called an ADMG in the literature.

## 2. Scope

### 2.1 Stable core target

The stable core target will include:

- Native node, edge, path, graph-type, and node-status objects.
- Direct construction and mutation through nodes, edges, and path expressions.
- DAG, MAG, PDAG, PAG, and internal undirected/directed graph representations.
- Graph validation and all basic relationship queries.
- Directed ancestry, possible ancestry, cycle detection, and topological ordering.
- d-connection and d-separation for the graph types supported by Dagitty R.
- Path enumeration and open-path classification.
- Ancestor, back-door, canonical, moral, structural, and measurement transformations.
- DAG-to-MAG projection, DAG-to-CPDAG conversion, PDAG orientation, and equivalent-DAG enumeration.
- Total- and direct-effect adjustment-set analysis.
- Implied conditional independencies.
- Conditional instrumental variables.
- Complete and random DAG generation.

Delivery is incremental. A DAG-focused preview is releasable after separation, core transformations, and DAG adjustment are complete. MAG/PDAG and then PAG capabilities receive separate preview maturity labels until their parity suites pass. The first `1.0` release requires the complete stable core target; users do not need to wait for `1.0` to exercise validated DAG functionality.

### 2.2 Subsequent deterministic SEM milestone

Vanishing tetrads will be implemented after the main causal API is stable. This requires canonicalization, trek graphs, vertex cuts, and careful control of combinatorial output, but does not require a statistical runtime.

### 2.3 Deferred optional modules

The following Dagitty R features are useful but are not part of the dependency-free causal core:

| Feature | Proposed module | Reason for deferral |
| --- | --- | --- |
| Implied covariance matrices | `pydagitty.stats` | Requires numerical linear algebra and random coefficient handling |
| SEM and logistic simulation | `pydagitty.stats` | Requires NumPy-compatible RNG, matrix operations, and tabular output |
| Local statistical tests | `pydagitty.stats` | Requires a broad statistical stack and data-frame conventions |
| Coordinates and spring layout | `pydagitty.viz` | Presentation concern and optional numerical dependency |
| Lavaan and external graph adapters | `pydagitty.interop` | Ecosystem-specific conversion concern |
| Bundled examples | `pydagitty.examples` | Useful after the object API stabilizes |

Static rendering is now available through the optional Graphviz adapter in
`pydagitty.viz`; coordinate storage and a native spring layout remain deferred.

### 2.4 Explicit non-goals

- No Dagitty string parser in the core package.
- No stable Dagitty or Graphviz serializer in the initial release.
- No NetworkX runtime dependency or NetworkX-backed public graph object.
- No browser GUI, website, graph publishing, or graph downloading.
- No JavaScript bridge or V8 dependency.
- No port of non-R-exposed experimental algorithms such as `treeID` in the initial roadmap.
- No promise to reproduce accidental upstream bugs. Intentional deviations must be documented and tested.

## 3. Public API Design

The public API will use Python snake case. Compatibility means feature and result parity with Dagitty R, not preservation of R function names or R container types.

### 3.1 Basic construction

```python
from pydagitty import DAG, nodes

A, B, U, Y = nodes("A B U Y")

graph = DAG()
graph.append_path(A >> B << U >> Y)
graph.exposures = {A}
graph.outcomes = {Y}

assert graph.parents(B) == {A, U}
sets = graph.adjustment_sets()
```

`nodes()` is only a convenience for creating named `Node` objects. It is not a graph-language parser.

Graphs must also support construction from iterables for generated or data-driven models:

```python
graph = DAG(
    nodes=[A, B, U, Y],
    paths=[A >> B, U >> B, U >> Y],
)
```

`edges=` accepts only concrete `Edge` objects. `paths=` accepts one- or multi-segment `PathExpression` objects. This prevents a multi-segment path from being silently treated as one edge.

### 3.2 Operator DSL

Python has no overloadable `->` operator. The expression DSL will therefore use:

| Python expression | Causal edge |
| --- | --- |
| `A >> B` | `A -> B` |
| `A << B` | `A <- B` |
| `A @ B` | `A <-> B` |
| `A - B` | `A -- B` |

`A >> B << U >> Y` is evaluated left to right because shifts have equal precedence. It produces `A -> B <- U -> Y`.

`PathExpression` will be immutable and will contain an ordered node sequence plus explicit endpoint pairs for every segment. Its cursor is the final syntactic node. Every operator returns a new expression rather than mutating an existing one.

Matrix multiplication and subtraction bind more tightly than shifts. The implementation must therefore support joining a node to an already-created path at either end. For example, Python evaluates `A >> B @ C` as `A >> (B @ C)`; `Node.__rshift__` must prepend `A -> B` to the existing `B <-> C` path. This makes common mixed expressions behave according to their visual reading rather than their evaluation grouping.

The following cases require dedicated tests:

```python
A >> B << U >> Y       # A -> B <- U -> Y
A >> B @ C             # A -> B <-> C
A @ B >> C             # A <-> B -> C
A >> B - C             # A -> B -- C
A - B >> C             # A -- B -> C
```

The operator DSL will not overload equality or comparison operators because doing so would break node identity, hashing, and Python's chained-comparison behavior.

Both `Node` and `PathExpression` implement the normal and reflected forms needed for `>>`, `<<`, `@`, and `-`. Joining a node to a path prepends at the path's first syntactic node; joining a path to a node appends at its cursor. Joining two paths connects the left cursor to the right first node and retains both segment sequences. No existing endpoint needs to be equal for a join: the selected operator creates the connecting segment. Parenthesized and unparenthesized forms must normalize to the same expression when they visually describe the same path.

### 3.3 PAG edges

Circle endpoints do not have an unambiguous Python operator. They will use an explicit edge constructor:

```python
from pydagitty import Edge, Endpoint, PAG

graph = PAG()
graph.add_edge(
    Edge(A, B, left=Endpoint.CIRCLE, right=Endpoint.ARROW)
)
```

The endpoint representation covers every Dagitty edge:

| Symbol | Left endpoint | Right endpoint |
| --- | --- | --- |
| `--` | `TAIL` | `TAIL` |
| `->` | `TAIL` | `ARROW` |
| `<->` | `ARROW` | `ARROW` |
| `@-@` | `CIRCLE` | `CIRCLE` |
| `@->` | `CIRCLE` | `ARROW` |
| `@--` | `CIRCLE` | `TAIL` |

### 3.4 Graph mutation

Construction methods mutate and return `self` for fluent use:

- `add_node(node)`
- `add_edge(edge)`
- `append_path(*paths)`
- `remove_node(node)`
- `remove_edge(edge)`
- `reverse_edge(edge)`
- `set_status(status, nodes)`

Adding an edge automatically registers missing endpoint nodes. An exact duplicate edge is idempotent. Different edge types between the same pair are allowed because Dagitty permits, for example, both `A -> B` and `A <-> B`.

Incoming node objects are resolved to the graph-owned node with the same identifier. Queries and status assignment accept `Node` or an iterable of `Node`; they do not accept bare strings. Unknown query/status nodes raise `UnknownNodeError`. Automatic node registration occurs only during explicit node, edge, path, or constructor insertion.

`append_path()` validates and normalizes every segment before committing any mutation. A failure cannot leave a partially appended path. Constructor insertion follows the same atomic normalization path.

Self-edges are rejected as an intentional initial deviation. Supporting them correctly would require endpoint-by-incidence semantics at a single node, and they are not needed by the R-facing causal algorithms. This policy can be revisited only with explicit relationship, path, cycle, and degree semantics.

`reverse_edge()` accepts only a strict tail-arrow edge. It atomically migrates edge attributes to the reversed key and raises `InvalidEdgeError` if the reverse already exists, the edge is stale, or the edge is symmetric or partial.

Declared graph type and edge-endpoint compatibility are checked when an edge is added. Upstream-compatible semantic validation is explicit because incremental construction must be inexpensive and Dagitty permits inspecting invalid models with `find_cycle` and `is_acyclic`. Full MAG/PAG certification is outside the stable-core validation promise.

High-level algorithms enforce locally decidable preconditions and raise a typed error for unsupported inputs. Where full MAG/PAG validity cannot yet be certified, they require a caller-certified model and state that limitation in the method documentation.

### 3.5 Analysis and transformation style

Relationship queries and analyses are graph methods:

```python
graph.parents(B)
graph.ancestors(Y, proper=True)
graph.dseparated(A, Y, given={B})
graph.adjustment_sets(exposure=A, outcome=Y)
graph.instrumental_variables(exposure=A, outcome=Y)
```

Transformations return new graphs and never mutate their inputs:

```python
ancestor = graph.ancestor_graph({Y})
backdoor = graph.backdoor_graph(exposure=A, outcome=Y)
mag = graph.to_mag()
```

Graph objects themselves remain mutable to support interactive model construction. Analysis implementations must not leave traversal marks, generated statuses, or temporary edges on the graph.

### 3.6 Statuses

Each graph owns five independent node-status sets:

- `exposures`
- `outcomes`
- `latents`
- `adjusted_nodes`
- `selected_nodes`

Assigning a status property replaces the complete set, matching the Dagitty R setter behavior. A node may hold multiple statuses unless a specific algorithm rejects the combination.

`selected_nodes` is public even though the current R setter does not expose it consistently. Selection status is required for canonicalization and selection-aware adjustment.

Status resolution is operation-specific:

| Operation | Status behavior |
| --- | --- |
| `dconnected`, `dseparated`, `paths` | Use only the explicit `given` argument; graph statuses are not implicit conditioning |
| `ancestor_graph()` without nodes | Seed with exposures, outcomes, and adjusted nodes, matching the R wrapper |
| `is_adjustment_set`, `adjustment_sets` | Arguments override exposure/outcome statuses; adjusted nodes are mandatory; selected nodes are fixed conditioning; latent nodes are forbidden candidates |
| `instrumental_variables` | Arguments override exposure/outcome statuses; exactly one of each is required |
| `implied_conditional_independencies` | Exposures, outcomes, and adjusted statuses do not alter the model; selected nodes are fixed conditioning |

Exposure and outcome sets must be non-empty and disjoint for effect-analysis operations. Exposure/outcome nodes cannot be latent, adjusted, or selected for those operations. Adjusted and selected nodes cannot be latent. Invalid combinations remain representable for inspection but are rejected at the relevant algorithm boundary.

### 3.7 Result types

Structured immutable results replace R lists and serialized graph fragments:

| Operation | Python result |
| --- | --- |
| Adjustment sets | `EnumerationResult[NodeSet]` |
| Conditional independencies | `EnumerationResult[ConditionalIndependence]` |
| Instruments | `list[Instrument]` |
| Paths | `EnumerationResult[Path]` or an iterator |
| Canonicalization | `Canonicalization(graph, latent_nodes, selection_nodes)` |
| Cycle detection | Closed `tuple[Node, ...]` or `None` |
| Equivalent DAGs | Iterator or `EnumerationResult[Graph]` |

`ConditionalIndependence`, `Instrument`, `Path`, and `Canonicalization` will be frozen dataclasses. `NodeSet` is an immutable ordered set whose equality is set-like and whose iteration follows graph insertion order. `ConditionalIndependence.left`, `.right`, and `.given` are `NodeSet` values so basis statements can represent setwise, not only pairwise, independence. `Path` contains both an ordered node tuple and the exact ordered edge tuple; paths with the same nodes but different parallel edge choices remain distinct.

Outer result ordering and `NodeSet` iteration are deterministic. The package does not claim deterministic iteration for arbitrary built-in `set` or `frozenset` values supplied by callers.

### 3.8 Enumeration limits

Paths, separators, adjustment sets, conditional independencies, tetrads, and equivalent DAGs can grow exponentially. Public APIs must accept `max_results: int | None` and stop enumeration as soon as the limit is reached. The value must be `None` or a non-negative integer; booleans and negative values are rejected, and zero returns no items without beginning the search.

Defaults will preserve Dagitty R behavior where practical:

| Operation | Default |
| --- | --- |
| Equivalent DAGs | `100` |
| Simple paths | `100` |
| Adjustment sets | No limit |
| Implied independencies | No limit |

Iterator forms should be added for algorithms that naturally enumerate results. List conveniences return `EnumerationResult(items, truncated)`, using one-result lookahead to distinguish an exact-size exhaustive result from truncation. Enumerators operate on a graph snapshot captured when iteration starts, so later mutation of the source graph cannot change an in-progress enumeration.

## 4. Internal Data Model

### 4.1 Node identity

`Node` will be a frozen, hashable dataclass containing only a non-empty string identifier. Node roles and attributes belong to a graph, not the node object, because the same `Node("X")` may be used in multiple graphs with different roles.

Node identifiers are compared exactly and are Unicode-safe. The implementation will not impose Dagitty parser restrictions because there is no textual grammar to protect.

### 4.2 Edge identity

`Edge` will be an immutable relation containing:

- Left node.
- Right node.
- Endpoint at the left node.
- Endpoint at the right node.

Internally, edges are canonicalized by node identifier. Swapping nodes also swaps their endpoints, so `Edge(A, B, TAIL, ARROW)` and `Edge(B, A, ARROW, TAIL)` identify the same directed relation. This gives one equality rule for symmetric and asymmetric edges and prevents duplicate reverse representations.

Both endpoints are incidences, not a single endpoint lookup on a node. Self-edges are rejected, so `edge.endpoint_at(node)` is unambiguous for every supported edge.

Node and edge attributes are graph-owned mappings keyed by node or canonical edge. This keeps hash identity independent of mutable metadata. Initial attributes needed for future parity are:

- Node residual variance, conventionally `eps`.
- Edge path coefficient, conventionally `beta`.
- Optional layout coordinates and control points, preserved but not interpreted by the core.

### 4.3 Graph storage

The graph will maintain:

- An insertion-ordered `dict[str, Node]`.
- An insertion-ordered `dict[EdgeKey, Edge]`.
- An incident-edge index for each node.
- Graph-owned node and edge attribute dictionaries.
- One ordered node set per managed status.
- A declared `GraphType`.

Each incident-edge index is an insertion-ordered dictionary, not a set. It is sufficient to derive parents, children, spouses, neighbours, and general adjacency in `O(degree(node))` without maintaining several indexes that can drift during mutation.

Traversal state must always be local to an algorithm. Unlike upstream Dagitty, nodes will not contain mutable `visited` or algorithm-specific fields.

### 4.4 Graph types and validation

`GraphType` will include `DAG`, `MAG`, `PDAG`, `PAG`, `GRAPH`, and `DIGRAPH`. The last two are internal result types used by moralization, flow, and other transformations.

Validation is split into three levels:

| Level | Checks |
| --- | --- |
| Structural | Endpoint values, self-edge policy, duplicate identity, graph-type edge compatibility |
| Upstream-compatible | The effective graph checks in the pinned Dagitty implementation |
| Strict/theorem | Complete ancestral, maximality, equivalence-class, and algorithm-specific preconditions where implemented |

`validate()` initially performs upstream-compatible validation:

- DAG: directed and bidirected edges only; no directed cycle.
- MAG: directed, bidirected, and undirected edges; no semi-directed cycle.
- PDAG: directed, bidirected, and undirected edges; no semi-directed cycle.
- PAG: all endpoint combinations; no semi-directed cycle.
- GRAPH: undirected edges only.
- DIGRAPH: permissive internal mixed representation.

Absence of a semi-directed cycle does not prove that a MAG is ancestral and maximal or that a PAG is valid. Dagitty itself marks full MAG and PAG validation as incomplete. MAG/PAG algorithms therefore require caller-certified valid models and document that `validate()` is not such a certificate. Full `validate(strict=True)` support is a post-1.0 candidate, not a stable-core promise. Algorithms enforce locally decidable requirements, such as the absence of undirected MAG/PAG edges for adjustment, but must not claim general graph validity from the weak check.

### 4.5 Public algorithm support matrix

This matrix is the source of truth for public precondition checks:

| Operation | Graph types | Additional requirements | Status behavior |
| --- | --- | --- | --- |
| Primitive parents/children/spouses/neighbours/adjacency | All | Strict endpoint relation only | Ignored |
| Directed ancestry/cycles | All | Follows strict `->` only | Ignored |
| Exogenous variables | All | No incoming strict `->` edge | Ignored |
| Topological ordering | DAG | No directed cycle | Ignored |
| Markov blanket | DAG | Parent/child/co-parent definition | Ignored |
| Collider test | DAG | Strict `u -> v <- w` | Ignored |
| `dconnected`, `dseparated` | DAG, MAG, PDAG, PAG | Caller-certified MAG/PAG; PAG uses pinned approximation | Explicit `given` only |
| `paths` | DAG, MAG, PDAG | `max_results` applies | Explicit `given` only |
| `ancestor_graph` | DAG, MAG, PDAG | Caller-certified MAG | Default seed uses exposure/outcome/adjusted |
| `canonicalize` | DAG, MAG | Structurally valid endpoints | Preserved; generated L/S statuses added |
| `moralize` | DAG, MAG, PDAG, GRAPH | GRAPH is an identity case | Statuses preserved for retained nodes |
| `backdoor_graph` | DAG, MAG, PDAG, PAG | Caller-certified MAG/PAG | Exposure/outcome arguments override statuses |
| `to_mag` | DAG | Selected nodes rejected; latent projection only | Latent nodes marginalized |
| Structural/measurement parts | DAG, DIGRAPH | Latent-status semantics | Retained statuses preserved |
| `orient_pdag` | PDAG | Must have a compatible recursive orientation | Preserved |
| `equivalence_class` | DAG | Directed edges only | Ignored |
| `equivalent_dags` | DAG, PDAG | Directed DAG or PDAG validated as completed (a CPDAG) | Ignored |
| Total adjustment | DAG, PDAG, MAG, PAG | PDAG orientation must succeed; MAG/PAG must have no undirected edge | Adjusted mandatory; selected fixed; latent forbidden |
| Direct adjustment | DAG | No selected nodes | Adjusted mandatory; latent forbidden |
| Implied independencies | DAG, MAG, PDAG | See observed-variable deviation | Selected fixed conditioning |
| Instruments | DAG | Exactly one exposure/outcome | Latent/selected nodes cannot be instruments |
| Vanishing tetrads | DAG | Deterministic SEM milestone | Latent nodes excluded from observed quadruples |
| Complete/random DAG generators | New DAG | Explicit node order; random generator receives RNG | No initial statuses |

### 4.6 Argument normalization

Public methods use one normalization contract. A singular argument accepts `Node`; a node-set argument accepts `Node` or an iterable of `Node`. Bare strings are rejected rather than treated as iterables. Equal external nodes resolve to the graph-owned instance by exact identifier. Queries and status assignments reject unknown identifiers; graph-building operations register them.

### 4.7 Exceptions

The package will define a small typed hierarchy:

- `PyDagittyError`
- `InvalidGraphError`
- `UnsupportedGraphTypeError`
- `UnknownNodeError`
- `InvalidEdgeError`

Ordinary Python type errors remain `TypeError`. Invalid option values remain `ValueError`. The package should not create one exception class per algorithm.

## 5. Proposed Package Layout

```text
pyproject.toml
LICENSE
README.md
src/
  pydagitty/
    __init__.py
    model.py
    traversal.py
    transformations.py
    adjustment.py
    implications.py
    instruments.py
    generators.py
    sem.py
    exceptions.py
tests/
  unit/
  parity/
  properties/
  performance/
docs/
  implementation-plan.md
```

Responsibilities:

| Module | Responsibility |
| --- | --- |
| `model.py` | Nodes, endpoints, edges, path expressions, graph storage, statuses, primitive queries, validation |
| `traversal.py` | Reachability, cycles, topological ordering, d/m-separation, paths, components, cuts, separators |
| `transformations.py` | Pure graph-to-graph transformations |
| `adjustment.py` | Adjustment criteria and set enumeration |
| `implications.py` | Conditional-independence generation and result types |
| `instruments.py` | Conditional instrumental-variable algorithms |
| `generators.py` | Complete and random DAG constructors |
| `sem.py` | Deterministic trek and tetrad algorithms; optional numerical functions remain elsewhere |

Public methods may delegate to these modules. The modules are implementation boundaries, not separate user-facing APIs.

## 6. Algorithm Plan

### 6.1 Primitive relationships and traversal

Implement endpoint predicates first:

- `has_arrowhead(edge, node)`
- `has_tail(edge, node)`
- `has_circle(edge, node)`
- Strict parent and child predicates for tail-arrow edges.
- Spouse predicate for arrow-arrow edges.
- Neighbour predicate for tail-tail edges.
- Possible-parent and possible-neighbour predicates for partial edges.

Build all public relationship queries from the incident-edge index and these predicates. This prevents inconsistent edge semantics across algorithms.

Directed ancestors and descendants use iterative graph traversal over strict parent/child relationships. Possible anteriors and posteriors additionally follow the endpoint combinations used by generalized adjustment.

Cycle detection follows strict directed edges only, matching Dagitty R. It returns the first deterministic closed cycle. Topological ordering uses Kahn's algorithm with graph insertion order as the tie-breaker and rejects directed cycles.

### 6.2 d-connection and m-separation

Port Dagitty's Bayes-ball state traversal without storing state on nodes. Traversal state distinguishes arrival through an arrowhead-like side from arrival through a child/tail-like side. The conditioned set `Z` and ancestors of `Z` determine legal transitions through colliders and non-colliders.

Required behavior:

- Empty `X` is never connected to a non-empty `Y`.
- Empty `Y` returns the set of all nodes reachable from `X` given `Z` for the lower-level operation.
- `dseparated(X, Y, Z)` is the Boolean complement of `dconnected(X, Y, Z)` when `Y` is non-empty.
- DAG, MAG, and PDAG semantics match upstream tests.
- PAG handling initially follows the pinned implementation behavior by converting partial endpoints to a PDAG-like representation before traversal.

The PAG approximation must be visible in API documentation. It is neither complete PAG m-separation nor possible-m-connection analysis. A later standards-based implementation may be added under an explicit mode rather than silently changing parity behavior.

### 6.3 Path enumeration

Simple path enumeration uses depth-first search with a local visited set and yields structured `Path` objects containing exact edge incidences. Directed-only traversal follows strict children. General traversal follows all supported incident edges. Parallel edge choices produce distinct paths even when their node sequence is identical.

Path openness is evaluated from endpoint marks at each internal node:

- A node is a collider when both adjacent path edges have arrowheads at that node.
- A collider is open when it or one of its descendants is conditioned on.
- A non-collider is blocked when conditioned on.

Enumeration and openness classification must be separate so tests can validate each independently.

### 6.4 Graph transformations

Implement transformations in dependency order:

1. Clone, merge, induced subgraph, edge-induced subgraph, and skeleton.
2. Ancestor graph using anteriors for graph types with uncertain endpoints.
3. Canonical DAG by replacing bidirected edges with latent common causes and undirected edges with selected colliders.
4. Moral graph, including bidirected districts and their parents.
5. Indirect graph for direct-effect adjustment.
6. Proper back-door graph, including visible-edge checks for MAG/PAG inputs.
7. Structural and measurement graph extraction.
8. DAG-to-CPDAG conversion using strong edge protection.
9. PDAG orientation through the recursive `X -> Y -- Z` rule and compatibility checks.
10. DAG-to-MAG latent projection.
11. Equivalent-DAG enumeration from a CPDAG.

Transformation metadata follows explicit rules: unchanged retained edges copy metadata; reversed edges migrate it; generated edges start without coefficients, control points, or style unless the transformation defines a mapping; collapsed edges do not arbitrarily inherit metadata from one source edge. Retained nodes preserve attributes and statuses. Generated latent and selected nodes use collision-free deterministic names and receive only their generated status.

`to_mag()` performs latent projection only and rejects selected nodes. Selection projection is a separate future operation rather than an implicit interpretation of `to_mag()`.

### 6.5 Undirected separators

Adjustment and implication enumeration depend on minimal vertex separators. Port the extended Takata enumeration used by Dagitty:

- Respect mandatory and forbidden nodes.
- Operate on moralized undirected ancestor graphs.
- Stop immediately at `max_results`.
- Return each separator once in deterministic order.
- Avoid mutating status sets to represent mandatory or forbidden nodes.

Initial separator support routines are connected components avoiding a node set and near separators. Minimum vertex cuts are added with tetrad support. Biconnected components and block trees are implemented only if a scoped parity fixture or later active-bias algorithm requires them. Algorithms that need annotations keep them in local dictionaries keyed by nodes or edges.

### 6.6 Adjustment criteria

Total-effect adjustment follows the generalized criterion used by Dagitty:

1. Resolve exposure and outcome from arguments or graph statuses.
2. Compute nodes on proper possible causal paths.
3. Reject sets containing forbidden possible descendants.
4. Construct the proper back-door graph.
5. Treat selected nodes as a fixed conditioning set, separate from returned covariates.
6. Require the outcome to be m-separated from the selected set in the proper back-door graph.
7. Test m-separation between exposure and outcome given candidate covariates plus selected nodes.

Total adjustment supports valid DAG inputs, PDAG inputs for which recursive orientation succeeds, and caller-certified valid MAG/PAG inputs without undirected edges. Incompatible PDAG orientation raises `InvalidGraphError`. Minimal adjustment sets are generated by moralizing the relevant ancestor graph and enumerating minimal separators. Existing `adjusted_nodes` are mandatory. Latent nodes, selected nodes, exposures, outcomes, and forbidden possible descendants cannot appear in returned sets. Canonical adjustment computes possible ancestors of exposures and outcomes minus sources, targets, latents, selected nodes, and forbidden descendants. Exhaustive `all` mode enumerates observed candidate subsets and validates each set.

Direct-effect adjustment is DAG-only, rejects selected nodes, and uses the indirect graph plus Pearl's single-door criterion. Calling it for MAG, PDAG, or PAG inputs raises `UnsupportedGraphTypeError`, correcting the R wrapper's broader check that ultimately fails in the underlying analyzer.

### 6.7 Implied conditional independencies

Support the R API's three modes:

| Mode | Method |
| --- | --- |
| `missing_edge` | Enumerate one or more minimal separators for each non-adjacent observed pair |
| `basis_set` | Local Markov basis with set-valued right sides |
| `all_pairs` | Enumerate all conditioning subsets for every observed pair |

PyDagitty uses observed-variable semantics consistently: latent and selected nodes are excluded from endpoint pairs and candidate conditioning sets. Selected nodes are included in each result's `.given` set as fixed conditioning so the statement is self-contained. `missing_edge` and `all_pairs` validate each statement by m-separation in that context. `basis_set` rejects graphs with selected nodes because the ordinary local Markov basis does not remain valid merely by adding selection conditioning. This intentionally differs from pinned R behavior, where `all.pairs` and `basis.set` can expose latent nodes. `all_pairs` is explicitly exponential and must honor `max_results`, improving on the current R wrapper where the limit is not consistently applied.

### 6.8 Instrumental variables

Conditional instrument discovery is DAG-only and requires exactly one exposure and outcome. The implementation will:

1. Canonicalize bidirected edges into latent common causes.
2. Build the proper back-door graph.
3. Exclude exposure, outcome, selected nodes, and latent nodes as candidates.
4. Find an ancestral separating set for each candidate.
5. Reject conditioning sets containing descendants of the outcome, the exposure itself, or mediators; do not categorically reject every descendant of the exposure.
6. Confirm relevance through d-connection to the exposure.

Return `Instrument(node, conditioning_set)` records and document the linear-model assumption. This API discovers graphical instruments; it does not estimate effects.

### 6.9 Markov equivalence

`equivalence_class()` accepts a directed-only DAG and produces a CPDAG. Bidirected edges are rejected because ordinary DAG Markov equivalence is not defined for the broader Dagitty DAG shorthand.

`equivalent_dags()` accepts a directed DAG or a PDAG validated as completed (a CPDAG), recursively orients undirected edges, rejects cycles and new v-structures, and yields only DAGs whose CPDAG equals the input equivalence class. Arbitrary PDAG consistent extension is a separate future operation. Completed-PDAG input requires completeness and extendability checks. The traversal order and limit are deterministic.

### 6.10 Vanishing tetrads

The deterministic SEM milestone will port:

- Canonicalization of bidirected edges.
- Trek graph construction.
- Minimum vertex cuts.
- Observed-variable quadruple enumeration.
- `within`, `between`, and `epistemic` filters.

It will return immutable four-node records and enforce DAG input, even though the upstream R wrapper currently omits that runtime check. Symbolic `treeID` and general polynomial solving remain out of scope.

### 6.11 Graph generators

`complete_dag()` creates nodes in supplied order and adds `node[i] -> node[j]` for every `i < j`. `random_dag()` uses the same fixed topological order and independently includes each eligible edge with probability `p`.

`random_dag()` accepts an explicit `random.Random` instance; it never uses module-global random state. It validates `0 <= p <= 1`, defines edge-trial order lexicographically by node position, and defaults generated names to `x1` through `xN` when given a count.

## 7. Dagitty R Parity Matrix

### 7.1 Graph model and deterministic causal API

| Dagitty R function | Python API | Release |
| --- | --- | --- |
| `graphType` | `graph.type` | Initial |
| `edges` | `graph.edges` | Initial |
| `exposures`, `outcomes`, `latents`, `adjustedNodes` | Status properties | Initial |
| `setVariableStatus` | `set_status()` and properties | Initial |
| `parents`, `children`, `ancestors`, `descendants` | Same snake-case graph methods | Initial |
| `neighbours`, `spouses`, `adjacentNodes` | Same snake-case graph methods | Initial |
| `markovBlanket`, `exogenousVariables` | Same snake-case graph methods | Initial |
| `isAcyclic`, `findCycle`, `topologicalOrdering` | Same snake-case graph methods | Initial |
| `isCollider` | `is_collider()` | Initial |
| `dconnected`, `dseparated` | Same snake-case graph methods | Initial |
| `paths` | `paths()` / `iter_paths()` | Initial |
| `ancestorGraph`, `backDoorGraph` | `ancestor_graph()`, `backdoor_graph()` | Initial |
| `canonicalize`, `moralize` | Same snake-case graph methods | Initial |
| `structuralPart`, `measurementPart` | Same snake-case graph methods | Initial |
| `toMAG`, `orientPDAG` | `to_mag()`, `orient_pdag()` | Initial |
| `equivalenceClass`, `equivalentDAGs` | `equivalence_class()`, `equivalent_dags()` | Initial |
| `adjustmentSets`, `isAdjustmentSet` | `adjustment_sets()`, `is_adjustment_set()` | Initial |
| `impliedConditionalIndependencies` | `implied_conditional_independencies()` | Initial |
| `instrumentalVariables` | `instrumental_variables()` | Initial |
| `completeDAG`, `randomDAG` | `complete_dag()`, `random_dag()` | Initial |
| `vanishingTetrads` | `vanishing_tetrads()` | Deterministic SEM milestone |

### 7.2 Deferred or replaced R features

| Dagitty R function | Decision |
| --- | --- |
| `dagitty`, `as.dagitty` | Replaced by object constructors and path expressions |
| `convert`, `lavaanToGraph` | Deferred to interoperability adapters |
| `coordinates`, `graphLayout` | Deferred to native layout support |
| `plot.dagitty` | Replaced by optional `to_graphviz()` static rendering |
| `getExample` | Deferred until examples can be expressed with the stable object API |
| `downloadGraph` | Excluded from the core |
| `impliedCovarianceMatrix` | Deferred to optional statistics support |
| `simulateSEM`, `simulateLogistic` | Deferred to optional statistics support |
| `ciTest`, `localTests`, `plotLocalTestResults` | Deferred to optional statistics and visualization support |

## 8. Upstream Deviations

The initial implementation intentionally differs from upstream in these areas:

- Public construction uses objects rather than graph strings.
- Public outputs are typed Python objects rather than serialized strings or R data frames.
- Edge endpoint compatibility is enforced at insertion, while endpoint-compatible semantic errors such as directed cycles remain representable.
- Self-edges are rejected.
- Traversal state is local and cannot leak through mutable node annotations.
- PAG adjacency includes every partial endpoint type; upstream `adjacentNodes` omits some partial edges.
- PAG d-connection explicitly labels and isolates the pinned implementation's PDAG-like approximation.
- Direct-effect adjustment explicitly rejects non-DAG inputs at the public boundary.
- Tetrad analysis explicitly validates DAG input.
- Implied-independence modes consistently expose observed variables and fixed selection conditioning rather than leaking latent nodes in `basis_set` and `all_pairs`.
- Enumeration limits are consistently honored.
- Transformations do not temporarily mutate node statuses on the source graph.
- Topological ordering rejects directed cycles and has deterministic tie-breaking.
- Markov blanket is documented and enforced as DAG-only until mixed-graph semantics are separately implemented.

Each deviation requires a test and a release-note entry. Differences in result ordering alone are acceptable if the order is deterministic and the mathematical result is identical.

## 9. Testing Strategy

### 9.1 Unit tests

Unit tests will cover:

- Node and edge equality, hashing, canonical orientation, and Unicode identifiers.
- Every operator expression and precedence case from section 3.2.
- Normal and reflected path joins for every operator pair, both evaluation groupings, and explicit parentheses.
- Multiple edge types between a node pair.
- Graph mutation and incident-index integrity.
- Atomic path insertion, graph-owned node normalization, reverse-edge collision handling, and metadata migration.
- Status replacement and graph-owned metadata.
- Validation for every graph type and endpoint combination.
- Relationship queries for all six endpoint forms.
- Copy and transformation immutability.
- Deterministic result ordering.

### 9.2 Upstream parity tests

Translate applicable GPL-compatible upstream JavaScript and R fixtures into object-based Python tests. Maintain a fixture manifest that assigns exact test cases, required internal algorithms, expected parity or deviation, and milestone. Whole upstream suites are not milestone acceptance units because several suites mix unrelated public and experimental features. Candidate source suites include:

- `test/adjustment-dags.js`
- `test/adjustment-other.js`
- `test/ancestry.js`
- `test/biasing-paths.js`
- `test/dseparation.js`
- `test/graph-analysis.js`
- `test/graph-transformations.js`
- `test/graph-types.js`
- `test/graph-validation.js`
- `test/instrumental-variables.js`
- `test/manipulation.js`
- `test/pags.js`
- `test/selection-nodes.js`
- `test/separators.js`
- `test/testable-implications.js`
- `test/tetrad-analyis.js`
- Relevant cases from `test/misc.js` and `test/test-graphs.js`
- R tests for basics, adjustments, chain graphs, instruments, Markov blankets, and tetrads

The original graph text should not become a hidden parser dependency. Each fixture will have a Python builder function using nodes, edges, and path expressions.

### 9.3 Differential fixtures

During development, generate normalized expected JSON from the pinned upstream JavaScript implementation for representative graphs. Commit the normalized expectations, not a JavaScript runtime dependency. Each fixture records:

- Upstream commit.
- Graph type, nodes, endpoint pairs, and statuses.
- Algorithm arguments.
- Canonically sorted result.

Differential coverage is especially important for MAG/PAG adjustment, edge visibility, latent projection, separators, instruments, and equivalent DAGs.

### 9.4 Property tests

Use Hypothesis as a development dependency for small generated graphs. Properties include:

- Edge canonicalization is invariant under endpoint-preserving reversal.
- Clone and induced-subgraph operations do not share mutable metadata.
- `dseparated` is symmetric in `X` and `Y`.
- DAG topological order places every strict parent before its child.
- Canonicalization removes bidirected and undirected edges and marks generated nodes correctly.
- Moralization produces only undirected edges; its internal GRAPH identity case makes repeated moralization idempotent.
- Every enumerated adjustment set passes `is_adjustment_set`.
- With no mandatory nodes, removing any member of a minimal adjustment set makes it invalid. With mandatory nodes, removal must either fail the criterion or violate the mandatory-set constraint.
- Every equivalent DAG is acyclic and has the same CPDAG.
- `to_mag` contains no explicitly latent nodes from the source DAG.

### 9.5 Performance tests

Maintain non-gating benchmarks for:

- Bayes-ball on sparse DAGs with thousands of nodes.
- Minimal separators on representative adjustment graphs.
- Adjustment enumeration as the candidate set grows.
- Equivalent-DAG enumeration for broad CPDAGs.
- Tetrad enumeration as the number of observed variables grows.

Performance changes should be measured against fixed generated graphs and fixed seeds. Optimization must not replace clear parity code until correctness tests exist.

## 10. Licensing and Attribution

This project is a direct port of GPL-2.0-compatible Dagitty algorithms. Milestone 0 must audit file-level grants and copyright notices before selecting an exact SPDX expression such as `GPL-2.0-only` or `GPL-2.0-or-later`; the project will not infer that choice from the repository license text alone. The repository must include:

- The complete applicable GPL license text and exact SPDX metadata.
- Attribution to the Dagitty authors.
- The pinned upstream commit in project documentation.
- Source-file notices on translated algorithm modules identifying the corresponding upstream files.
- Citations retained from upstream comments for published algorithms such as generalized adjustment and Takata separator enumeration.

Translated upstream test cases remain under the compatible project license and should retain a short origin notice.

## 11. Delivery Milestones

### Milestone 0: Project foundation

Deliverables:

- Package scaffold and GPL licensing.
- Test, lint, formatting, and type-check commands.
- Contributor documentation describing the upstream parity process.
- File-level license audit and selected SPDX expression.

Acceptance criteria:

- Editable installation succeeds on the minimum and current supported Python versions.
- Empty test, lint, and type-check pipelines run in CI.

### Milestone 1: Object model and DSL

Deliverables:

- `Node`, `Endpoint`, `Edge`, `PathExpression`, `GraphType`, and graph constructors.
- Directed, reverse-directed, bidirected, undirected, and explicit partial-edge construction.
- Mutation, statuses, attributes, cloning, and structural validation.

Acceptance criteria:

- All operator precedence examples produce the specified endpoint sequences.
- Every Dagitty edge form can be represented without strings.
- Parallel edge types and graph-owned metadata remain consistent after deletion and cloning.

### Milestone 2: Primitive graph API

Deliverables:

- All relationship and ancestry queries.
- Cycle detection, upstream-compatible validation, and topological ordering.
- Complete and random DAG generation.

Acceptance criteria:

- Relevant upstream basics, ancestry, manipulation, graph-type, and validation fixtures pass.
- No traversal algorithm mutates node or graph metadata.

### Milestone 3: Separation and paths

Deliverables:

- Bayes-ball/m-separation.
- d-connection, d-separation, path enumeration, and path openness.
- Connected components and the separator primitives required by the scoped cases.

Acceptance criteria:

- Scoped upstream d-separation, path, PAG, and separator cases in the fixture manifest pass.
- Limits stop enumeration without exploring unnecessary remaining branches.

Release checkpoint: publish a DAG-focused preview after the DAG cases in Milestones 0-3 and the prerequisite DAG transformations/adjustment slice are complete.

### Milestone 4: Transformations and equivalence

Deliverables:

- Ancestor, canonical, moral, back-door, indirect, structural, and measurement graphs.
- DAG-to-MAG and DAG-to-CPDAG conversion.
- PDAG orientation and equivalent-DAG enumeration.

Acceptance criteria:

- Scoped transformation and equivalence cases in the fixture manifest pass; unrelated active-bias, dependency-graph, and experimental cases are not implied.
- Input graphs and metadata are unchanged after every transformation.
- Equivalent DAG output is deterministic and bounded.

### Milestone 5: Adjustment

Deliverables:

- Adjustment criterion validation.
- Minimal, canonical, and exhaustive total-effect sets.
- Minimal direct-effect sets.
- DAG, MAG, PDAG, and PAG handling matching documented Dagitty restrictions.

Acceptance criteria:

- Scoped upstream JavaScript and R adjustment cases pass, including selection-status cases exercised by adjustment.
- Every generated set validates independently.
- Minimality is verified for every minimal result.

Release checkpoint: promote DAG support to stable and MAG/PDAG support to preview when their type-specific adjustment and transformation cases pass. PAG remains preview until its pinned-behavior cases and caveat documentation pass.

### Milestone 6: Implications and instruments

Deliverables:

- Missing-edge, basis-set, and all-pairs conditional independencies.
- Conditional instrumental variables and conditioning sets.

Acceptance criteria:

- Upstream testable-implication and instrumental-variable fixtures pass.
- Latent and selected nodes follow the observed-variable deviation documented in section 8.
- Structured results compare independent of presentation formatting.

### Milestone 7: Deterministic SEM constraints

Deliverables:

- Trek graph and minimum vertex-cut support required by tetrads.
- Vanishing tetrads and typology filters.

Acceptance criteria:

- Upstream JavaScript and R tetrad fixtures pass.
- Enumeration limits and DAG validation are enforced.

### Milestone 8: Stable core release

Deliverables:

- API reference and causal examples using only object construction.
- Complete R parity/deviation table.
- Performance baseline and package release automation.

Acceptance criteria:

- All stable-core scoped parity tests pass on supported Python versions.
- Public API is fully typed and documented.
- No runtime dependency on NetworkX, JavaScript, R, or numerical libraries.
- Deferred features are clearly separated from stable-core claims.

## 12. Critical Path and Risks

The implementation dependency chain is:

```text
model and endpoints
  -> primitive traversal
  -> d/m-separation
  -> transformations and separators
  -> adjustment, implications, and instruments
  -> tetrads
```

Primary risks and mitigations:

| Risk | Mitigation |
| --- | --- |
| Endpoint semantics diverge across algorithms | Central endpoint predicates and exhaustive six-edge unit tests |
| Weak MAG/PAG checks are mistaken for validity certification | Distinguish upstream-compatible and strict validation; require caller-certified models until strict validators exist |
| PAG support is mistaken for complete theoretical support | Match and document the pinned approximation first; isolate it behind a conversion step |
| Ported algorithms retain mutation-based JavaScript assumptions | Local traversal state, pure transformations, and immutability regression tests |
| Separator and subset enumeration becomes unusable | Iterator implementations, branch-level limits, and performance fixtures |
| R wrapper behavior differs from the underlying JavaScript restriction | Validate effective restrictions at the Python public boundary and record deviations |
| DSL expressions behave differently because of Python precedence | Immutable path merging from both ends and explicit precedence tests |
| Result comparison is unstable | Preserve graph insertion order and use the ordered immutable `NodeSet` result type |
| A direct port loses attribution or license context | Pin the upstream commit and add notices to translated source and tests |

## 13. Definition of Done

A feature is complete only when:

- Its graph-type and validity preconditions are explicit.
- Its public inputs and structured outputs are typed.
- It does not mutate the source graph unless it is a documented construction method.
- It has direct unit tests and translated upstream parity coverage.
- Exponential behavior has a documented limit mechanism.
- Ordering of package-defined result collections is deterministic.
- Any behavior differing from Dagitty R is listed in the parity documentation.
- Algorithm references and translated-source attribution are retained.
