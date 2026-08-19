# Mixed-Graph Caveats

PyDagitty's graph classes share an object API, but they do not share one level
of theoretical coverage. Endpoint compatibility is not graph-family
certification.

## Terminology

- **Ordinary DAG**: directed edges only, with no directed cycle.
- **Dagitty-style DAG**: directed and bidirected edges, with no directed cycle.
  This broader graph is often called an **ADMG**.
- **MAG**: a maximal ancestral graph. PyDagitty accepts directed, bidirected,
  and undirected endpoints but does not prove maximality or ancestrality.
- **PDAG**: a partially directed graph. Different methods need either a
  compatible extension or the stronger completed-PDAG property.
- **PAG**: a partial ancestral graph representing a MAG equivalence class.
  PyDagitty does not implement complete PAG validity or separation theory.

`GRAPH` and `DIGRAPH` are provisional undirected/permissive result types, not
additional mature causal model families.

## Release Tiers

| Family | Tier | Safe interpretation |
| --- | --- | --- |
| DAG/ADMG | Supported | Strongest 0.1.0 evidence, subject to each operation's ordinary-DAG restrictions. |
| MAG | Preview | Use only caller-certified valid MAGs and operation-specific endpoint restrictions. |
| PDAG | Preview | Use only where the operation's orientation/completion premise is satisfied. |
| PAG | Experimental | Treat output as pinned approximation behavior, never complete PAG theory. |
| GRAPH/DIGRAPH | Provisional | Consume documented transformation/helper results; avoid general input use. |

## What `validate()` Establishes

`validate()` checks endpoint compatibility and directed or semi-directed cycles
as applicable. It does not establish:

- MAG maximality or ancestrality;
- PAG validity or membership in an equivalence class;
- CPDAG completion;
- complete operation-specific causal identification premises.

There is intentionally no `strict` option or hidden theorem validator.
MAG/PAG certification must come from the caller's model provenance or another
tool.

## PAG Approximation

For `reachable_nodes()`, `dconnected()`, and `dseparated()`, each PAG circle
endpoint is treated as a tail before traversal. Related partial handling enters
PAG back-door and total-adjustment behavior. This follows the pinned Dagitty
approximation but is not:

- complete PAG m-separation;
- definite-status path analysis;
- possible-m-connection;
- complete generalized PAG adjustment theory.

PAG path enumeration and `is_path_open()` are rejected explicitly. Implied
independencies, equivalence, instruments, and tetrads also reject PAG input.

## Operation Checklist

| Operation | Mixed-graph boundary |
| --- | --- |
| Exact parent/child/spouse/neighbor queries | Available on all types; only inspect local marks. |
| Directed ancestry/cycles | Follow strict directed edges only. |
| Separation | MAG/PDAG preview; PAG experimental circle-to-tail approximation. |
| Paths | MAG/PDAG preview; PAG unsupported. |
| `ancestor_graph` | MAG/PDAG preview; PAG unsupported. |
| `canonicalize` | MAG preview; PDAG/PAG unsupported. |
| `moralize` | MAG/PDAG preview; PAG unsupported. |
| `backdoor_graph` | MAG/PDAG preview; PAG experimental. |
| Total adjustment | MAG/PDAG preview; PAG experimental. MAG/PAG cannot contain undirected edges. |
| Direct adjustment | DAG only. |
| `to_mag` | Starts from DAG; returned MAG remains preview. No selection projection. |
| `orient_pdag` | Preview compatible extension; no completed-PDAG requirement. |
| `equivalent_dags` from PDAG | Preview and requires a completed PDAG. |
| Implied independencies | MAG/PDAG preview; PAG unsupported. |
| Markov blanket, strict collider, topology | DAG only. |
| Instruments and tetrads | DAG only. |

## Failure Interpretation

`UnsupportedGraphTypeError` means the declared family is outside an
operation's contract. `InvalidGraphError` means a locally detectable premise
failed. A successful call means neither that a preview/experimental input was
globally valid nor that all causal identification assumptions hold.

Likewise, `EnumerationResult.truncated=False` only reports search exhaustion.
It does not elevate PAG output to complete theory or certify a MAG. Preserve
the graph family, caller certification, approximation mode, and result bound
when reporting an analysis.

When a complete mixed-graph theorem is required, use a tool that explicitly
implements and validates that theorem rather than interpreting PyDagitty's
shared method availability as a maturity claim.
