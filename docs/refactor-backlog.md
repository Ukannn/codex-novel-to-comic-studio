# Architecture task pool

## Safe implementation queue

| ID | Task | Owner | Status / acceptance |
| --- | --- | --- | --- |
| G01 | Map architecture, history, dependencies and state ownership | Integration + independent audit | Done; baseline 11 tests |
| G02 | Canonical settings and explicit production preference input | Integration | In progress; preserve old calls, test configured behavior |
| G03 | Atomic JSON I/O; migrate all package callers | Integration | In progress; exact bytes and failure preservation tests |
| G04 | Pure validators and director checks in the package | Validation | In progress; CLI imports/report shape unchanged |
| G05 | One grid algorithm for composition and lettering | Rendering | In progress; differing margins/gutters preserved |
| G06 | Primary finished-page QC plus explicit fallback QC | Rendering | In progress; JSON and explicit-path semantics retained |
| G07 | Deterministic image resource cleanup | Rendering | In progress; export formats/order unchanged |
| G08 | Read each state input once, remove dead helpers | Integration | Planned; all state phases and stale checks preserved |
| G09 | AST architecture rules, public CLI contracts and CI | Integration | Planned; cycles/reverse dependencies/default drift rejected |
| G10 | Independent review of each batch and integrated verification | Independent audit | Ongoing; findings resolved before handoff |
| G11 | Align developer/Agent documentation with implemented boundaries | Integration | Planned; documented commands exercised |

## Decisions requiring a separate product/compatibility choice

| ID | Question | Why not silently change it |
| --- | --- | --- |
| D01 | Should state require valid director content and passing QC, rather than existence? | Changes current recovery/completion semantics and existing tests |
| D02 | Should approval markers include input hashes or require freshness? | Invalidates previously approved work; needs migration rules |
| D03 | Should export freshness be checked against every finished page? | Changes meaning of `complete` and may require artifact manifests |
| D04 | Are webtoon, fixed-budget and other declared preference modes production-supported? | Config accepts them but current story validators enforce story-first pages |
| D05 | How should re-ingestion remove obsolete chapter files? | Potential data deletion; requires an explicit overwrite/cleanup policy |
| D06 | How should source chapter IDs map to adapted comic chapter IDs? | Current source uses `ch001` while production examples use `ch01`; meaning differs |
| D07 | Should true automated Agent dispatch replace the documented editorial workflow? | Requires scheduling, failure recovery, model/tool and cost decisions |
| D08 | How should sibling novel workspaces receive generic-tool updates? | Separate repositories and local production assets need an explicit rollout plan |

## Deliberately unnecessary

No UI framework, authentication service, database, cache, network retry engine,
new directory hierarchy or generic service/container abstraction is introduced.
The audit found no core dependency cycles and no competing remote service clients.
