# PyDagitty 0.1.0 Technical Roadmap

Status: Implemented; hosted cross-platform and tagged-release gates pending

Target: Public `0.1.0` release

Audience: Python causal analysts

Upstream reference: [`jtextor/dagitty`](https://github.com/jtextor/dagitty),
commit `7a657776dc8f5e5ba4e323edb028e2c2aaf29327`

This roadmap is the execution plan for `0.1.0`. It supersedes the delivery
milestones in [the original implementation plan](implementation-plan.md) where
the two documents conflict. The implementation plan remains the design record
for the existing object model and algorithms.

## 1. Release Outcome

`0.1.0` will turn the existing pre-alpha implementation into a documented,
risk-tested causal graph library. The milestone prioritizes evidence for the
algorithms already present over new features.

The release claim is intentionally tiered:

| Graph family | `0.1.0` maturity | Required evidence |
| --- | --- | --- |
| Dagitty-style `DAG`, including directed and bidirected ADMG edges | Supported | Deep parity, literature checks, properties, guides, and API reference |
| `MAG` | Preview | Representative parity cases and explicit caller-certification requirements |
| `PDAG` | Preview | Representative orientation, equivalence, separation, and adjustment cases |
| `PAG` | Experimental | Tests for the documented pinned approximation and prominent theory limitations |
| `GRAPH` and `DIGRAPH` | Provisional result types | Tests where returned internally; no general-purpose stability promise |

The term `DAG` must be explained consistently. PyDagitty follows Dagitty by
allowing directed and bidirected edges in `DAG`; the latter is commonly called
an ADMG in the literature.

## 2. Release Principles

- Use risk-based evidence rather than exhaustive testing of every graph.
- Use pinned Dagitty behavior plus published causal-graph literature as the
  correctness oracle.
- Block the release for incorrect causal conclusions or silent failure.
- Permit deterministic ordering and representation differences when the
  mathematical result is equivalent.
- Record every intentional semantic deviation in a fixture, the parity
  reference, and the changelog.
- Preserve the dependency-free runtime core.
- Measure combinatorial behavior before optimizing it.
- Publish stable artifacts only from reviewed version tags.

## 3. Non-Goals

- Dagitty text parsing or import/export.
- A stable native serialization format.
- NetworkX, lavaan, or other ecosystem adapters.
- Complete MAG or PAG certification.
- Complete PAG m-separation, possible-m-connection, or adjustment theory.
- New major causal algorithms.
- Statistical estimation, simulation, or numerical runtime dependencies.
- Performance rewrites without parity tests protecting behavior.
- A `1.0` API stability guarantee.

## 4. Workstream A: Public Contract

This workstream must land first because fixtures and documentation need an
unambiguous target.

### A1. Remove the unusable strict validation option

- Change `Graph.validate(self, *, strict: bool = False)` to `Graph.validate(self)`.
- Remove the unconditional `NotImplementedError` branch.
- Keep `validate()` explicitly limited to endpoint, self-edge, and cycle checks.
- Update the README, parity reference, API documentation, and tests.
- Reserve theorem-level graph-family certification for future purpose-built
  APIs rather than another placeholder argument.

Acceptance criteria:

- No public call signature advertises unimplemented strict validation.
- `validate()` behavior remains unchanged for existing calls without `strict`.
- MAG/PAG documentation still states that inputs must be caller-certified.

### A2. Define the supported 0.x surface

- Inventory every symbol in `pydagitty.__all__` and every public `Graph` method.
- Classify each as supported, preview, experimental, or provisional.
- Treat documented supported names as the 0.x compatibility surface.
- Use release notes and deprecation where practical before breaking supported
  APIs; experimental and provisional APIs may change with clear release notes.
- Explain that semantic maturity depends on graph family even when a method is
  available on multiple graph classes.

Acceptance criteria:

- The API reference assigns a maturity level to every public symbol.
- `GRAPH` and `DIGRAPH` are not described as stable general-purpose inputs.
- The compatibility policy distinguishes API compatibility from algorithmic
  correctness.

### A3. Establish release metadata

- Add `CHANGELOG.md` with an initial `0.1.0` section and documented deviations.
- Replace pre-alpha wording with the agreed `0.1.0` maturity language.
- Update the package development-status classifier from Pre-Alpha to Alpha.
- Correct stale license-planning text to reflect the selected `GPL-2.0-only`
  expression and verify that translated-source and fixture attribution is
  complete.

## 5. Workstream B: Parity Fixture Infrastructure

Add a fixture layer that keeps upstream provenance separate from ordinary unit
tests and does not require JavaScript or R during CI.

Proposed layout:

```text
tests/
  parity/
    manifest.json
    builders.py
    normalize.py
    expected/
      <fixture-id>.json
    test_adjustment.py
    test_equivalence.py
    test_implications.py
    test_instruments.py
    test_separation.py
    test_transformations.py
    test_mixed_graphs.py
```

Each manifest entry must contain:

| Field | Purpose |
| --- | --- |
| `id` | Stable local fixture identifier |
| `source` | Upstream test file, R test, or literature citation |
| `upstream_commit` | Pinned commit for Dagitty-derived behavior |
| `graph_type` | Declared PyDagitty graph family |
| `operation` | Public behavior under test |
| `expectation` | `parity`, `intentional-deviation`, or `literature` |
| `risk` | `high`, `medium`, or `low` |
| `builder` | Python object-builder function |
| `expected` | Normalized expectation file or explicit assertion location |
| `notes` | Preconditions, caveats, or deviation rationale |

Implementation rules:

- Construct graphs through `Node`, `Edge`, and `PathExpression`; do not add a
  graph-string parser as fixture infrastructure.
- Commit normalized expected data rather than invoking upstream at test time.
- Normalize node sets independently of presentation ordering.
- Preserve path edge incidence where parallel endpoint-defined edges matter.
- Assert deterministic PyDagitty ordering separately from mathematical set
  equality.
- Retain a short origin notice on adapted GPL-compatible fixtures.
- Make missing manifest entries, builders, or expected files fail collection
  with a useful error.

Acceptance criteria:

- One end-to-end fixture from each high-risk algorithm area proves the harness.
- Fixtures run with the normal `python -m pytest` command.
- CI has no JavaScript, R, NetworkX, or numerical dependency.
- Every fixture is traceable to a source or documented local invariant.

## 6. Workstream C: Risk-Based Correctness Evidence

### C1. High-risk DAG/ADMG behavior

These areas receive the deepest parity and literature-backed coverage:

| Area | Minimum evidence |
| --- | --- |
| d-connection and d-separation | Chains, forks, colliders, conditioned descendants, bidirected confounding, multiple query sets, and symmetry |
| Path openness and enumeration | Open/closed paths, parallel edges, bounds, truncation, and snapshot behavior |
| Minimal separators | Multiple minimal solutions, mandatory/forbidden nodes, no-solution cases, and bounded search |
| Adjustment | Total/direct modes, minimality, canonical sets, multiple exposures/outcomes, latent/selected nodes, and invalid roles |
| Transformations | Ancestor, canonical, moral, back-door, indirect, structural/measurement, and latent projection |
| Equivalence | CPDAG construction, compatible orientation, equivalent DAG enumeration, acyclicity, and bounds |
| Implied independencies | Missing-edge, basis-set, and all-pairs modes with latent/selected policies |
| Instruments | Relevance, exclusion, conditioning-set search, and unsupported status combinations |
| Vanishing tetrads | Upstream typologies, latent structures, bounds, and invalid graph types |

### C2. Mixed-graph tiers

- Add representative MAG cases for separation, ancestry, canonicalization,
  moralization, back-door behavior, adjustment, and implied independencies.
- Add representative PDAG cases for separation, orientation, equivalent DAGs,
  transformations, and adjustment.
- Test PAG behavior against the pinned circle-to-tail approximation only.
- Test that unsupported PAG paths and theorem-level guarantees fail clearly.
- Do not describe passing pinned PAG fixtures as complete PAG theory.

### C3. Property tests

Extend `tests/test_properties.py` or split it by domain when it becomes large.
Add generated small-graph properties for:

- Clone, induced-subgraph, and transformation metadata independence.
- Moralization output shape and idempotence of its internal undirected result.
- Canonicalization endpoint restrictions and generated-node roles.
- Every enumerated adjustment set passing `is_adjustment_set()`.
- Removal of a non-mandatory member invalidating each minimal adjustment set.
- Every equivalent DAG being acyclic and mapping back to the same CPDAG.
- Latent projection excluding explicitly latent source nodes.
- Enumeration limits returning no more than the requested result count.

Generated tests must use small bounded graphs, deterministic reproduction data,
and health-check suppression only with a documented reason.

### C4. Mismatch policy

| Finding | Release treatment |
| --- | --- |
| Incorrect separation, adjustment, equivalence, or other causal conclusion | Blocker |
| Silent truncation, ignored bound, or malformed result | Blocker |
| Crash on a supported valid input | Blocker |
| Dagitty disagreement supported by literature | Intentional deviation with fixture, rationale, and changelog entry |
| Deterministic ordering or representation difference | Allowed and documented where user-visible |
| Failure limited to preview/experimental theory outside the stated contract | Documented known limitation; does not block unless the API claims support |

## 7. Workstream D: Analyst Documentation

Use repository Markdown for `0.1.0`; a versioned documentation site is not a
release requirement.

Proposed documentation set:

```text
docs/
  api.md
  compatibility.md
  guides/
    constructing-graphs.md
    separation-and-paths.md
    adjustment.md
    transformations-and-equivalence.md
    implications-instruments-and-tetrads.md
    mixed-graph-caveats.md
  parity.md
  performance.md
  publishing.md
```

Documentation requirements:

- Cover every supported top-level symbol and public graph method.
- State graph-family preconditions next to each operation, not only in the
  parity matrix.
- Explain standard DAG, Dagitty-style DAG/ADMG, MAG, PDAG, and PAG terminology.
- Include complete analyst workflows using only the Python object API.
- Show how to interpret `EnumerationResult.truncated` and choose
  `max_results`.
- Distinguish graphical identification from effect estimation.
- Keep optional Graphviz installation and runtime requirements explicit.
- Validate important examples through tests or directly executable scripts so
  documentation cannot silently drift.
- Replace PyPI-facing links that only work from a repository checkout with
  durable project URLs or self-contained text.

Acceptance criteria:

- A new user can construct, analyze, and visualize a confounded graph from the
  guides without consulting source code.
- Every supported API has a signature, graph-family scope, result semantics,
  failure behavior, and at least one example where useful.
- Preview and experimental labels are visible from both the API reference and
  relevant guides.

## 8. Workstream E: Performance Baseline

Performance work is observational and non-gating for `0.1.0`, except that
broken result bounds or pathological regressions discovered during the work
must be triaged under the mismatch policy.

Add reproducible benchmark scenarios for:

- Sparse DAG separation at increasing node counts.
- Path and minimal-separator enumeration.
- Minimal and exhaustive adjustment as candidate count increases.
- Broad CPDAG equivalent-DAG enumeration.
- Instrument conditioning-set enumeration.
- Tetrads as observed-variable count increases.

Benchmark design:

- Use fixed graph builders and fixed random seeds.
- Record Python version, platform, graph dimensions, arguments, runtime, result
  count, and truncation state.
- Keep benchmarks outside the default test run.
- Provide one command that emits machine-readable results.
- Run benchmarks manually or through a non-gating GitHub workflow and retain
  the result artifact.
- Document practical envelopes and exponential failure modes in
  `docs/performance.md`.
- Optimize only after a parity fixture protects the affected behavior.

## 9. Workstream F: CI and Distribution

### F1. Quality jobs

- Keep full tests, Ruff, and strict mypy on Linux for Python 3.10 through 3.13.
- Avoid running lint and mypy four times if the workflow can separate them from
  the Python test matrix without weakening coverage.
- Add a dedicated documentation-example check.

### F2. Artifact jobs

- Build the wheel and source distribution once after quality jobs pass.
- Run `twine check` on both artifacts.
- Install each artifact into a clean environment rather than relying only on
  editable installation.
- Smoke-test import, graph construction, separation, adjustment, version
  metadata, and optional Graphviz source generation.

### F3. Cross-platform evidence

- Run representative artifact smoke tests on Ubuntu, macOS, and Windows.
- Cover the minimum and latest supported Python versions across the smoke
  matrix.
- Keep system Graphviz rendering in a dedicated environment where the `dot`
  executable is installed; do not make all platform jobs install it.

### F4. Publication

- Remove PyPI publication from the ordinary CI path for pushes to `main`.
- Publish normal releases only for reviewed tags matching `v*`.
- Keep development publication as an optional separate workflow if continued
  dev builds remain useful.
- Require quality, artifact validation, and smoke jobs before requesting the
  PyPI trusted-publishing token.
- Preserve least-privilege GitHub permissions and the protected `pypi`
  environment.
- Update `docs/publishing.md` to describe the final workflow exactly.

## 10. Delivery Sequence

The following slices are intended to be independently reviewable pull requests
or equivalent change sets:

| Slice | Scope | Depends on |
| --- | --- | --- |
| R0 | Contract cleanup, strict-option removal, maturity matrix, changelog skeleton | None |
| R1 | Parity manifest, builders, normalization, and one fixture per high-risk area | R0 |
| R2 | Separation, paths, separators, and core transformation parity | R1 |
| R3 | Adjustment and latent-projection parity plus properties | R2 |
| R4 | Equivalence, implications, instruments, and tetrad parity | R1; R2 where shared primitives apply |
| R5 | Representative MAG/PDAG and pinned-approximation PAG cases | R2; R3 |
| R6 | Remaining graph/model properties and mismatch resolution | R2-R5 |
| R7 | Analyst guides, API reference, compatibility policy, and tested examples | R0; can proceed alongside R2-R6 |
| R8 | Reproducible benchmarks and performance guide | R2-R6 |
| R9 | Artifact tests, cross-OS smoke matrix, and tag-gated publishing | R0; can proceed alongside R2-R8 |
| R10 | Release audit, release notes, final artifacts, and `v0.1.0` tag | R1-R9 |

No new major algorithm work should enter R0-R10 unless it fixes a release
blocker discovered by the evidence work.

## 11. Required Checks

The local release-candidate checks must include:

```bash
python -m pytest
python -m ruff check .
python -m mypy
python -m build
python -m twine check dist/*
```

CI additionally installs and smoke-tests the built distributions on the agreed
platform matrix. The release process must verify that the tag-derived package
version is exactly `0.1.0`.

## 12. Definition of Done

`0.1.0` is ready only when all of the following are true:

- [x] The public contract and maturity labels are documented.
- [x] `validate(strict=True)` is no longer advertised or accepted.
- [x] The parity manifest covers every scoped high-risk algorithm area.
- [x] All scoped Dagitty parity and intentional-deviation fixtures pass.
- [x] Literature-backed disagreements have recorded rationales.
- [x] DAG/ADMG properties and mixed-graph representative tests pass.
- [x] No known supported input produces an incorrect causal conclusion.
- [x] Enumeration limits and truncation reporting are tested.
- [x] Supported public APIs are typed and documented.
- [x] Analyst guides and important examples are executable and passing.
- [x] Performance scenarios and practical caveats are published.
- [x] Wheel and source distribution installation tests pass.
- [ ] Representative Ubuntu, macOS, and Windows smoke tests pass.
- [x] `CHANGELOG.md` contains release notes and all intentional deviations.
- [x] Stable publication is tag-gated and protected by successful checks.
- [ ] The `v0.1.0` artifacts pass `twine check` and report version `0.1.0`.

## 13. Remaining Execution Assumptions

- There are no external consumers relying on the unimplemented `strict`
  parameter before `0.1.0`.
- The pinned Dagitty source and its GPL-compatible fixtures remain available
  during fixture adaptation.
- Exact fixture counts are chosen during the R1 inventory; risk categories and
  behavioral coverage, not an arbitrary count, determine completeness.
- Performance thresholds are not release gates until the first reproducible
  baseline exists.
- Complete mixed-graph certification and complete PAG theory remain future
  milestones rather than hidden `0.1.0` requirements.
