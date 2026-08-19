# Dagitty Parity and Scope

This document describes the implemented PyDagitty API relative to Dagitty at
commit [`7a657776dc8f5e5ba4e323edb028e2c2aaf29327`](https://github.com/jtextor/dagitty/tree/7a657776dc8f5e5ba4e323edb028e2c2aaf29327).
Parity means corresponding deterministic graph behavior where documented. It
does not mean an R-compatible interface, identical containers, identical
ordering, or support for Dagitty's textual graph syntax.

## Attribution Baseline

The implementation is informed by Dagitty's JavaScript graph algorithms, R
API behavior, tests, and published algorithm references. PyDagitty expresses
that work through a native typed object model and Python-specific algorithms.
No PyDagitty source file is claimed to be a verbatim translation of an
upstream file.

Dagitty's root `LICENSE.txt` at the pinned commit contains GNU GPL v2. Its
`r/DESCRIPTION` states `License: GPL-2`; under R package license semantics this
means version 2 only. PyDagitty consequently uses the exact SPDX expression
`GPL-2.0-only` and ships the complete license in `LICENSE`.

## Object and Result Mapping

| Dagitty concept | PyDagitty API |
| --- | --- |
| Parsed graph string | `DAG`, `MAG`, `PDAG`, or `PAG` object construction |
| Variable | immutable `Node` |
| Edge mark pair | immutable `Edge` with two `Endpoint` values |
| Graph path text | immutable `PathExpression` during construction |
| `graphType`, `edges` | `graph.type`, `graph.edges` |
| Exposure/outcome/latent/adjusted status | graph status properties |
| Selection status | `graph.selected_nodes` |
| R list of node sets | `EnumerationResult[NodeSet]` |
| Independence text/list | `ConditionalIndependence` records |
| Instrument result | `Instrument(node, conditioning_set)` |
| Path result | `Path(nodes, edges)` preserving parallel edge choices |
| Canonical graph plus generated nodes | `Canonicalization` |

`NodeSet` is immutable, set-equal, and iterates in deterministic graph order.
`EnumerationResult.truncated` distinguishes an exhausted search from a bounded
result. Graph transformations return new graphs and do not temporarily alter
the source graph's statuses.

## Function Parity

| Dagitty R function or area | PyDagitty API | Status |
| --- | --- | --- |
| `dagitty`, `as.dagitty` | object constructors, `nodes()`, operators | Replaced, no parser |
| `graphType`, `edges` | `type`, `edges` | Implemented |
| Status getters/setters | status properties, `set_status()` | Implemented |
| Parent/child/ancestry queries | snake-case graph methods | Implemented |
| `neighbours`, `spouses`, `adjacentNodes` | graph methods; US aliases where applicable | Implemented |
| `markovBlanket`, `exogenousVariables` | graph methods | Implemented; blanket DAG-only |
| Cycle and topological functions | graph methods | Implemented |
| `isCollider` | `is_collider()` | Implemented; DAG-only |
| `dconnected`, `dseparated` | graph methods | Implemented with PAG caveat |
| `paths` | `paths()`, `iter_paths()`, `is_path_open()` | Implemented except PAG |
| `ancestorGraph`, `backDoorGraph` | graph methods | Implemented by listed types |
| `canonicalize`, `moralize` | graph methods | Implemented by listed types |
| `structuralPart`, `measurementPart` | graph methods | Implemented for DAG/DIGRAPH |
| `toMAG`, `orientPDAG` | `to_mag()`, `orient_pdag()` | Implemented with preconditions |
| `equivalenceClass`, `equivalentDAGs` | graph methods | Implemented with ordinary-DAG/CPDAG scope |
| `adjustmentSets`, `isAdjustmentSet` | graph methods | Implemented with type restrictions |
| `impliedConditionalIndependencies` | graph method | Implemented for DAG/MAG/PDAG |
| `instrumentalVariables` | graph method | Implemented for one-exposure/one-outcome DAGs |
| `completeDAG`, `randomDAG` | `complete_dag()`, `random_dag()` | Implemented |
| `vanishingTetrads` | `vanishing_tetrads()` | Implemented for DAGs |

## Graph-Type Matrix

`GRAPH` and `DIGRAPH` are permissive internal/result representations, although
their classes are exported. A check mark below means the operation accepts
that declared graph type, not that PyDagitty certifies every input as a valid
member of the corresponding mathematical graph family.

| Operation | DAG | MAG | PDAG | PAG | Notes |
| --- | --- | --- | --- | --- | --- |
| Primitive relationships and directed ancestry | Yes | Yes | Yes | Yes | Uses exact endpoint marks |
| `validate()` | Yes | Yes | Yes | Yes | Structural/cycle checks only |
| Topological ordering, collider, Markov blanket | Yes | No | No | No | Strict DAG definitions |
| d-connection/d-separation | Yes | Yes | Yes | Approx. | PAG circles become tails |
| Paths and openness | Yes | Yes | Yes | No | Simple paths; exact edge incidence |
| `ancestor_graph()` | Yes | Yes | Yes | No | MAG must be caller certified |
| `canonicalize()` | Yes | Yes | No | No | Directed/bidirected/undirected marks only |
| `moralize()` | Yes | Yes | Yes | No | Also supports internal `GRAPH` identity |
| `backdoor_graph()` | Yes | Yes | Yes | Approx. | Visibility logic; PAG circles become tails |
| `indirect_graph()` | Yes | Yes | Yes | Yes | Direct-edge removal transformation |
| Structural/measurement part | Yes | No | No | No | Also supports internal `DIGRAPH` |
| `to_mag()` | Yes | No | No | No | Latent projection; selected nodes rejected |
| `orient_pdag()` | No | No | Yes | No | Requires a compatible acyclic orientation |
| `equivalence_class()` | Yes | No | No | No | Fully directed simple DAG only |
| `equivalent_dags()` | Yes | No | Yes | No | PDAG input must be a CPDAG |
| Total adjustment | Yes | Yes | Yes | Yes | MAG/PAG cannot contain undirected edges |
| Direct adjustment | Yes | No | No | No | Selected nodes rejected |
| Implied independencies | Yes | Yes | Yes | No | Observed-variable policy below |
| Instruments | Yes | No | No | No | Linear-effect graphical criterion |
| Vanishing tetrads | Yes | No | No | No | Linear SEM graphical constraints |

Dagitty calls a graph with directed and bidirected edges a DAG. PyDagitty keeps
that name for compatibility, though ADMG is common terminology. DAG insertion
allows tail-arrow and arrow-arrow edges. MAG and PDAG also allow tail-tail
edges. PAG and internal DIGRAPH permit every endpoint pair.

## Validation and Model Assumptions

Insertion checks endpoint compatibility and rejects self-edges. `validate()`
checks edge compatibility and directed or semi-directed cycles as applicable.
It does not prove MAG maximality or ancestrality, PAG validity, equivalence
class validity, or every algorithm-specific theorem premise. The API does not
advertise theorem-level certification that it cannot provide.

MAG and PAG algorithms must therefore receive caller-certified models.
Completed-PDAG requirements are checked specifically by `equivalent_dags()`;
`orient_pdag()` instead finds the first deterministic compatible extension.
High-level methods reject locally detectable unsupported edge forms and status
combinations.

For PAG reachability and d-separation, circle endpoints are changed to tails
before traversal, matching the pinned Dagitty approximation. The same partial
endpoint approximation participates in PAG back-door handling. This is not a
complete implementation of PAG m-separation, definite-status paths,
possible-m-connection, or all PAG adjustment theory.

Instrument discovery checks graphical exclusion and relevance for a linear
total effect and returns a conditioning set. Identification additionally
requires the usual linear structural-model and homogeneous-effect assumptions;
the package does not estimate an effect.

## Status Semantics

| Operation | Status behavior |
| --- | --- |
| Separation and paths | Only explicit `given` is conditioned on |
| `ancestor_graph()` without nodes | Uses exposures, outcomes, and adjusted nodes as seeds |
| Adjustment | Arguments override exposure/outcome statuses; adjusted nodes are mandatory; selected nodes are fixed conditioning; latent nodes are unavailable |
| Instruments | Arguments override statuses; exactly one exposure and outcome required; latent/selected nodes cannot be instruments |
| Implied independencies | Latent and selected nodes are excluded as endpoints/candidates; selected nodes are fixed conditioning |

Effect analyses require nonempty, disjoint exposure and outcome sets. Exposure
and outcome nodes cannot also be latent, adjusted, or selected. Adjusted and
selected nodes cannot be latent. Invalid combinations may be represented but
are rejected at the relevant analysis boundary.

## Intentional Deviations

The following are deliberate differences from pinned Dagitty behavior or its R
surface:

1. Construction uses Python objects and operators, not Dagitty graph strings.
2. Results are typed Python records and collections, not serialized fragments,
   R lists, or data frames.
3. Edge endpoint compatibility is enforced during insertion. Compatible but
   cyclic models remain constructible for explicit validation and inspection.
4. Self-edges are rejected because a single node would need endpoint-by-
   incidence semantics not otherwise required by the supported algorithms.
5. Traversal state is local; nodes do not retain mutable visited annotations.
6. PAG adjacency recognizes every partial endpoint combination. Pinned
   Dagitty's `adjacentNodes` can omit some partial edges.
7. PAG d-connection exposes the pinned circle-to-tail, PDAG-like approximation
   instead of presenting it as complete PAG theory.
8. Direct-effect adjustment rejects non-DAG inputs at the public boundary,
   rather than passing them to a later failing analyzer.
9. Tetrad analysis explicitly requires a DAG.
10. Implied-independence modes consistently expose observed variables. Latent
    and selected nodes are not endpoint pairs or optional conditioning
    candidates; selected nodes appear as fixed conditioning. `basis_set`
    rejects selected nodes. Pinned `all.pairs` and `basis.set` can expose
    latent nodes.
11. Enumeration limits are consistently validated and honored. Zero means no
    search, and bounded structured results report truncation.
12. Transformations do not temporarily mutate source statuses or traversal
    annotations.
13. Topological ordering rejects cycles and uses graph insertion order as a
    deterministic tie-breaker.
14. Markov blankets use the DAG parent/child/co-parent definition and reject
    other graph families until separate mixed-graph semantics are implemented.
15. Different result ordering from Dagitty is permitted when deterministic and
    mathematically equivalent.
16. `random_dag()` requires an explicit `random.Random`; it never consumes
    module-global random state.
17. `to_mag()` performs latent projection only and rejects selected nodes
    rather than implicitly performing selection projection.
18. `orient_pdag()` returns the first deterministic, fully directed compatible
    DAG extension. Pinned Dagitty's similarly named operation only performs
    compelled orientations and returns a PDAG.
19. Canonicalization uses independent latent (`L`) and selection (`S`) name
    counters. Generated identifiers may therefore differ from pinned Dagitty
    while the transformed graph remains mathematically equivalent.
20. Direct-effect adjustment supports `minimal`, `canonical`, and `all` modes;
    pinned Dagitty restricts direct-effect enumeration to minimal sets.
21. Adjusted nodes are unavailable as instruments or instrument-conditioning
    candidates, consistently with their graph-owned mandatory-conditioning
    role in PyDagitty.
22. Separation rejects query endpoints that also appear in `given`, making the
    standard disjoint-set precondition explicit instead of inheriting pinned
    Dagitty's endpoint-overlap behavior.

## Enumeration and Complexity

Paths default to `max_results=100`; equivalent DAGs also default to 100.
Adjustment sets, implied independencies, separators, and tetrads default to no
limit. Searches can be exponential. A limit must be `None` or a non-negative
integer; booleans are rejected. Use `EnumerationResult.truncated` rather than
assuming a full result after setting a bound.

`all_pairs` independencies and `mode="all"` adjustment enumerate conditioning
subsets. Equivalent DAG enumeration can likewise grow rapidly. Path iterators
capture a graph snapshot before iteration so later source mutation does not
change the active traversal.

## Deferred and Excluded Modules

| Dagitty feature | Proposed Python area | Current decision |
| --- | --- | --- |
| Implied covariance matrices | `pydagitty.stats` | Deferred; needs numerical linear algebra and coefficient handling |
| SEM and logistic simulation | `pydagitty.stats` | Deferred; needs RNG, arrays, and tabular conventions |
| `ciTest`, local tests, result plots | `pydagitty.stats` / `pydagitty.viz` | Deferred; needs a statistical and plotting stack |
| Coordinates and spring layout | `pydagitty.viz` | Deferred presentation/numerical concern |
| Static graph rendering | `pydagitty.viz` | Implemented through the optional Graphviz adapter |
| Lavaan and external graph adapters | `pydagitty.interop` | Deferred ecosystem integration |
| Bundled `getExample` graphs | `pydagitty.examples` | Deferred until the object API stabilizes |
| Stable Dagitty/Graphviz serialization | `pydagitty.interop` | Deferred; visualization DOT is not a stable interchange format |
| Browser GUI, publishing, downloading | None | Excluded from the core package |
| JavaScript/R bridge | None | Excluded; implementation is native Python |
| NetworkX-backed public graph | None | Excluded; no NetworkX runtime dependency |
| Experimental `treeID` and polynomial solving | None | Outside the initial roadmap |
| Complete strict MAG/PAG validators | Core candidate | Deferred; weak validation is not certification |
| Complete PAG separation/adjustment theory | Core candidate | Deferred; current behavior is pinned approximation |
| Selection projection in `to_mag()` | Separate future operation | Deferred, not implicit |

## Parity Testing

Applicable upstream JavaScript and R fixtures are represented under
`tests/parity/` as Python object builders and normalized expected JSON. The
machine-checked manifest records source locations, the pinned commit, risk,
and whether each case expects parity, a documented deviation, or a
literature-backed result. These fixtures are adaptations under the project
license, not represented as verbatim copies. CI does not require JavaScript or
R.

Development checks are:

```bash
python -m pytest
python -m ruff check .
python -m mypy
```

Hypothesis is a development dependency for generated graph properties such as
edge canonicalization, separation symmetry, topological ordering, immutable
transformation metadata, and adjustment-set validation.
