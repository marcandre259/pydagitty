# Compatibility Policy

This policy applies to the 0.x series. PyDagitty has not made a 1.0 stability
promise. The [API reference](api.md) is the inventory of the current public
surface; the roadmap maturity tiers limit the strength of each promise.

## Two Different Contracts

**API compatibility** concerns documented supported names, signatures, return
shapes, exceptions, and object behavior. For supported APIs, releases should
use release notes and a practical deprecation period before an avoidable
breaking change. A correctness or safety defect can require an immediate
change when preserving behavior would return a wrong causal conclusion.

**Algorithmic correctness** concerns whether a result follows the stated
graphical criterion under its preconditions. A name remaining importable does
not make all graph-family semantics equally mature. DAG/ADMG has the strongest
0.1.0 target. MAG and PDAG are preview; PAG is experimental.

## Maturity and Change Policy

| Tier | 0.x compatibility treatment |
| --- | --- |
| Supported | Documented names and ordinary valid-input behavior are the compatibility surface. Prefer deprecation and release notes before breaking them. Correctness fixes may change outputs. |
| Preview | Documented preconditions and failures are intentional, but signatures, ordering, and edge-case semantics may change as parity evidence grows. Changes are called out in release notes. |
| Experimental | May change without deprecation when needed to replace an approximation or align with causal-graph theory. Never infer complete theory coverage. |
| Provisional | Internal/result-oriented exported classes and helpers can change as implementation boundaries evolve. Do not use them as a general graph framework. |

A supported method used with a preview or experimental graph has that graph
family's lower maturity. The class and operation tables in
[the API reference](api.md) make this explicit.

## Supported Surface

The supported 0.x surface consists of names marked **Supported** in
`docs/api.md`, including documented `Graph` methods when used on supported
graph families and inputs. Names in implementation modules that are absent
from `pydagitty.__all__` are not public merely because Python can import them.
The module-level `pydagitty.viz.to_graphviz` function is an implementation
adapter; use the documented `Graph.to_graphviz()` method.

The following are not compatibility promises:

- private names, internal module layout, or lazy delegation details;
- exact `repr()` formatting;
- runtime or memory performance;
- ordering relative to Dagitty R or JavaScript when PyDagitty's result is
  deterministic and mathematically equivalent;
- DOT output as a serialization format;
- general-purpose use of `GRAPH` or `DIGRAPH`;
- theorem-level MAG/PAG validity certification;
- behavior outside an operation's documented graph-family preconditions.

## Result Compatibility

Deterministic insertion-based ordering is useful and tested, but callers should
compare causal sets as sets unless the API specifically makes order part of the
meaning. `NodeSet` equality is set equality. `Path` retains exact edge
incidence, so paths with the same node sequence but different parallel edges
are distinct.

Enumeration bounds are contractual:

- `max_results=None` means no result bound, not a performance guarantee.
- A non-negative integer bounds returned items.
- `max_results=0` means no search and yields `truncated=False`.
- `truncated=True` means the returned prefix is incomplete.
- `truncated=False` means the implemented search exhausted its space; it does
  not certify an experimental theory approximation or the input model.

## Validation Boundary

Construction rejects self-edges and endpoint forms incompatible with the
declared class. `validate()` checks endpoint compatibility and directed or
semi-directed cycles as applicable. It does not prove:

- MAG ancestrality or maximality;
- PAG validity;
- that a PDAG is completed;
- every theorem-specific premise for adjustment, separation, or equivalence.

MAG and PAG inputs must therefore be certified by the caller using reasoning or
tools outside this package. Algorithm methods add local checks where possible.
`validate()` intentionally has no `strict` option: theorem-level graph-family
certification will use purpose-built APIs if it is implemented in the future.

## Terminology Compatibility

PyDagitty retains Dagitty's term `DAG` for graphs with directed and bidirected
edges. In much of the literature, that broader family is called an acyclic
directed mixed graph (ADMG), while an ordinary DAG has directed edges only.
Whenever an operation says "ordinary DAG" or "fully directed DAG", bidirected
edges are excluded. This matters for CPDAG construction and Markov-equivalent
DAG enumeration.

PyDagitty uses Python objects, not Dagitty graph strings, R lists, data frames,
or identical ordering. Parity means corresponding deterministic graph behavior
where documented, not interface compatibility with R or JavaScript.

## Optional Dependencies and Platforms

The causal graph core has no runtime dependency outside Python 3.10 or newer.
Visualization requires the optional `graphviz` Python package. Rendering also
requires a compatible Graphviz system installation and executable. Absence of
that optional software does not affect core compatibility.

## Deprecation and Release Notes

When practical, a supported API removal or signature change should be announced
in release notes, retain a warning period, and identify a replacement. A
deprecation may be skipped for security, data-corruption, or causal-correctness
fixes, or before a documented symbol first enters the supported tier. Preview,
experimental, and provisional changes need clear release notes but do not
promise a deprecation period.

Report suspected behavioral mismatches with the graph family, complete object
construction, operation and arguments, observed result, expected result, and a
literature or pinned-Dagitty reference when available.
