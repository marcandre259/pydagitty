# Performance

PyDagitty's benchmark suite is dependency-free and intentionally non-gating. It
provides reproducible workload baselines, not statistically rigorous hardware
comparisons. Run it from the repository root in an environment where PyDagitty
is installed:

```bash
python benchmarks/run.py
```

The command writes one JSON document to standard output. Redirect it to retain
an artifact:

```bash
python benchmarks/run.py > benchmark.json
```

The default runs all scenarios at scale 1 with `max_results=100` and is sized
for quick manual use. Select scenarios by repeating `--scenario`, and increase
fixture sizes with `--scale`:

```bash
python benchmarks/run.py --scenario sparse-separation --scale 5
python benchmarks/run.py --scenario paths --scenario minimal-separators --scale 2
python benchmarks/run.py --scenario adjustment --max-results 250
```

Use `python benchmarks/run.py --help` for the scenario names and arguments.
`--max-results none` requests unbounded enumeration and should be used only on
fixtures whose complete result space is known to be small.

The non-gating `Benchmarks` GitHub Actions workflow runs the same command on
demand and retains its JSON result as an artifact. Its `scale` and
`max-results` inputs make larger comparisons explicit rather than slowing
ordinary CI.

A verified scale-1 sample is retained in
`benchmarks/results/cpython-3.12-linux-scale1.json`. It records the exact Python
and platform details and is a reproducibility example, not a cross-machine
performance threshold.

## Reproducibility and output

The sparse DAG uses seed 2026, and all other scenarios use deterministic graph
builders and insertion order. Fixture construction and query generation happen
outside the timed region. Each benchmark is measured once with
`time.perf_counter()`; run the command several times and compare medians when
investigating small changes.

The JSON document records:

- Python implementation and version, and the platform string.
- Selected scenarios, scale, fixed seed, and global result limit.
- Graph node/edge counts and scenario-specific dimensions.
- Algorithm arguments, elapsed seconds, result count, result kind, and
  truncation state.

`truncated` is `true` when the API found another result after reaching the
bound, `false` when it exhausted the search, and `null` when the operation has
no bounded-enumeration result. Elapsed times should only be compared on the
same machine, Python implementation/version, scenario dimensions, and
arguments. Result counts and truncation are useful reproducibility checks
across platforms, but timing values are expected to vary.

## Scenarios

| Scenario | Fixture and scaling | Primary growth |
| --- | --- | --- |
| `sparse-separation` | Fixed-seed sparse DAG; nodes and queries grow with scale | Roughly linear in reachable nodes and edges per query |
| `paths` | Layered width-two DAG with source-to-target path choices | Exponential in layer count |
| `minimal-separators` | Parallel length-three paths with two separator choices each | Exponential in parallel-path count |
| `adjustment` | Independent back-door paths; emits minimal and all-set records | Minimal sets can be exponential; exhaustive subsets are exponential in candidates |
| `equivalent-dags` | Complete DAG whose CPDAG is fully undirected | Up to factorial class size and exponential orientation search |
| `instruments` | One conditional instrument with an increasing confounder set | Up to `2^c` conditioning subsets per candidate |
| `tetrads` | Single-factor model with increasing observed variables | `3 * C(n, 4)` possible tetrad layouts, plus a graph test per layout |

Scale is a workload multiplier, not a promise that every dimension doubles.
Inspect each output record rather than comparing scale values alone.

## Practical envelope

Scale 1 and the default limit are the manual smoke envelope: 100 sparse-DAG
nodes and 25 separation queries, at most 100 retained results per bounded
enumeration, five adjustment back-door paths, five complete-DAG nodes, five
instrument confounders, and eight observed tetrad variables. These dimensions
are deliberately small enough to run all scenarios during local development.

There is no graph-size-only safe envelope for enumeration. A graph with few
nodes can have exponentially many paths, separators, adjustment sets, or
equivalent DAGs. Increase one scenario at a time, retain a finite result limit,
and watch both elapsed time and `truncated`. For sparse separation, larger node
counts are more predictable, but scale also increases query and conditioning
counts; use separate scale runs rather than extrapolating from one timing.

## Enumeration limits

Simple paths, minimal separators, adjustment sets, equivalent DAGs, and tetrads
can produce very large collections. Always pass a practical `max_results` in
interactive or service code, inspect `EnumerationResult.truncated`, and treat a
truncated collection as a prefix rather than a complete answer. A larger limit
increases both retained memory and search work. A limit prevents an
accidentally huge returned tuple, but it is not a general execution-time or
memory deadline.

Important current limits:

- Minimal adjustment enumeration obtains the underlying minimal-separator
  collection before applying the adjustment result bound. `max_results` bounds
  returned adjustment sets but may not bound all intermediate separator work.
- `instrumental_variables()` returns a list and has no `max_results` argument.
  Its conditioning-subset search can be exponential. Keep candidate ancestor
  sets small and benchmark representative graphs before using it in latency-
  sensitive code.
- Tetrad enumeration is polynomial in the observed-variable count rather than
  exponential, but quartic output growth becomes large quickly and each layout
  performs a vertex-disjoint-path test.

Do not optimize parity-sensitive algorithms from timing data alone. First add
or identify a correctness fixture that protects the affected behavior, then
compare identical benchmark JSON dimensions and arguments before and after the
change.
