# Architecture task pool

## Safe implementation queue

| ID | Task | Owner | Status / acceptance |
| --- | --- | --- | --- |
| G01 | Map architecture, history, dependencies and state ownership | Integration + independent audit | Done; baseline 11 tests |
| G02 | Canonical settings and explicit production preference input | Integration | Done; all five consumers migrated, old calls preserved |
| G03 | Atomic text/JSON I/O; migrate all package callers | Integration | Done; exact bytes, modes, symlinks and failure preservation tested |
| G04 | Pure validators and director checks in the package | Validation | Done; CLI imports/report shape unchanged |
| G05 | One grid algorithm for composition and lettering | Rendering | Done; differing margins/gutters preserved |
| G06 | Primary finished-page QC plus explicit fallback QC | Rendering | Done; JSON and explicit-path semantics retained |
| G07 | Deterministic image resource cleanup | Rendering | Done; export formats/order unchanged |
| G08 | Read each state input once, remove dead helpers | Integration | Done; all state phases and stale checks preserved |
| G09 | AST architecture rules, public CLI contracts and CI | Integration | Done; cycles/reverse dependencies/default drift rejected |
| G10 | Independent review of each batch and integrated verification | Independent audit | Done; 96 tests and all-command smoke pass; review findings fixed |
| G11 | Align developer/Agent documentation with implemented boundaries | Integration | Done; explicit settings and language authority documented |
| G12 | Prevent false completion after failed initial ingest | Rendering + audit | Done; reproduced before fix, novel completion signal published last |
| G13 | Keep generated narrative/plan artifacts outside reusable code | Integration + audit | Done; Git ignore and trackable-template contracts tested |

## Decisions requiring a separate product/compatibility choice

| ID | Question | Why not silently change it |
| --- | --- | --- |
| D01 | Should state require valid director content and passing QC, rather than existence? | Changes current recovery/completion semantics and existing tests |
| D02 | Should approval markers include input hashes or require freshness? | Invalidates previously approved work; needs migration rules |
| D03 | Should export freshness be checked against every finished page? | Changes meaning of `complete` and may require artifact manifests |
| D04 | Are webtoon, fixed-budget and other declared preference modes production-supported? | Config accepts them but current story validators enforce story-first pages |
| D05 | How should re-ingestion publish multiple files and remove obsolete chapters? | Existing projects need version/rollback and explicit cleanup policy; initial-ingest fix is not a transaction |
| D06 | How should source chapter IDs map to adapted comic chapter IDs? | Current source uses `ch001` while production examples use `ch01`; meaning differs |
| D07 | Should true automated Agent dispatch replace the documented editorial workflow? | Requires scheduling, failure recovery, model/tool and cost decisions |
| D08 | How should sibling novel workspaces receive generic-tool updates? | Separate repositories and local production assets need an explicit rollout plan |
| D09 | Should optional critical-information entries (`required=false`) require coverage? | Existing validator requires all listed entries; relaxing it changes editorial acceptance |
| D10 | Should over-capacity fixed layouts reject rather than truncate panels? | Existing fallback layout behavior is preserved; needs a defined repair/error contract |
| D11 | Should binding follow supplied directory order instead of global path order? | Changes established page ordering and exported books |

## Separately scoped quality work

| ID | Topic | Necessary scope before implementation |
| --- | --- | --- |
| Q01 | Portable CJK fallback lettering | Choose distributable fonts, license/provisioning and visual acceptance fixtures; current search is macOS-oriented |
| Q02 | Lettering overflow and scaling on custom canvases | Define bubble/text scaling and minimum readable size; current fallback uses fixed-pixel typography |
| Q03 | PDF/CBZ pair publication under failure | Define complete-export manifest or version semantics; two files currently publish independently |
| Q04 | Director-brief heuristic precision | Define accepted markup/case/text-negation semantics before changing substring checks |

No unresolved implementation blocker remains in the completed governance batches.
These items are not claims that the current tools implement stronger guarantees.

## Deliberately unnecessary

No UI framework, authentication service, database, cache, network retry engine,
new directory hierarchy or generic service/container abstraction is introduced.
The audit found no core dependency cycles and no competing remote service clients.
