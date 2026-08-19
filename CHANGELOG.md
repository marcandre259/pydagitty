# Changelog

All notable user-facing changes are documented here. The project follows
semantic versioning within the normal flexibility of the `0.x` series.

## 0.1.0 - 2026-08-19

### Added

- Typed, dependency-free DAG/ADMG, MAG, PDAG, and experimental PAG graph
  objects and deterministic causal graph algorithms.
- Separation, paths, minimal separators, adjustment, graph transformations,
  equivalence analysis, implied independencies, instruments, and vanishing
  tetrads.
- Property-based tests, pinned Dagitty parity fixtures, analyst guides, API and
  compatibility references, reproducible benchmarks, and Graphviz rendering.
- Built-artifact and cross-platform smoke-test release gates.

### Changed

- `validate()` now advertises only implemented structural and cycle checks;
  the unimplemented `strict` argument was removed before the first stable
  release.
- Stable PyPI publication is restricted to reviewed `v*` tags.
- Graph-family maturity is explicit: DAG/ADMG is supported, MAG and PDAG are
  preview, and PAG is experimental.

### Intentional Dagitty Deviations

- Construction uses typed Python objects instead of Dagitty graph strings.
- Results use typed deterministic Python values; equivalent result ordering
  may differ from Dagitty.
- PAG adjacency includes all partial endpoint combinations, while PAG
  separation and back-door handling retain the pinned circle-to-tail
  approximation and do not claim complete PAG theory.
- Implied-independence endpoints and optional conditioning candidates exclude
  latent and selected nodes; selected nodes are fixed conditioning.
- `orient_pdag()` returns the first deterministic fully directed compatible
  DAG extension instead of a partially oriented PDAG.
- Canonical generated latent and selection nodes use independent name
  counters, so generated identifiers can differ while graph semantics agree.
- Direct-effect adjustment supports all three enumeration modes rather than
  rejecting `canonical` and `all`.
- Adjusted nodes are excluded from instrument candidates and conditioning
  candidates.
- Separation requires query endpoints and conditioned nodes to be disjoint.
- Transformations avoid temporary source mutation, limits have consistent
  validation and truncation reporting, and random DAG generation requires an
  explicit random number generator.

### Known Limitations

- `validate()` does not certify MAG maximality or ancestrality, PAG validity,
  or general CPDAG validity.
- PAG separation and adjustment behavior is a pinned approximation; PAG path
  enumeration is unsupported.
- Several enumerations are exponential. Consult `docs/performance.md`, set
  `max_results` where available, and inspect `EnumerationResult.truncated`.
- Graphical instrument results require additional linear structural-model and
  homogeneous-effect assumptions and do not estimate an effect.
