# Step 3 — Arrange the extracted JSON (the agent builds, not build.py)

## Contents

- [Where this step sits](#where-this-step-sits)
- [The split: compute, arrange, curate, assemble, show](#the-split-compute-arrange-curate-assemble-show)
- [build.py is not the mandatory renderer](#buildpy-is-not-the-mandatory-renderer)
- [Where the cache and artifacts go](#where-the-cache-and-artifacts-go)
- [The shape of the arranged JSON](#the-shape-of-the-arranged-json)
- [Assembling the viewer from the template](#assembling-the-viewer-from-the-template)
  - [`__LAYERS__` — real example](#__layers__--real-example)
  - [What it looks like rendered](#what-it-looks-like-rendered)
- [The additive-only rule](#the-additive-only-rule)

---

## Where this step sits

Step 2 produced raw JSON from the AST: nodes and edges, extracted mechanically
from the parser. That JSON is a skeleton — accurate about structure, silent about
meaning. This step is where the **agent** takes over: arranging that JSON into
something a human reads.

The reframe that matters here: historically `build.py` did two jobs at once — it
**computed** the structure AND **rendered** the viewer. Those two jobs split at this
step. Computing is cheap and mechanical. Assembling the viewer is where the agent's
judgment starts, and it doesn't have to go through `build.py` to do it.

---

## The split: compute, arrange, curate, assemble, show

| Task | Who | Note |
|---|---|---|
| Compute degrees / detect orphans | `build.py` or a simple script | Pure math over the AST JSON — no judgment |
| Assign layers to nodes | the agent | grouping decision, see step-4-grouping.md |
| Curate meaning | the agent | the expensive half, see step-5-curation.md |
| Assemble the final HTML viewer | the agent | built by hand from a reusable template |
| Show | the resulting HTML | the deliverable the human reads |

The point of the table: `build.py` stops being the mandatory renderer. It can still
do the cheap mechanical half (degrees, orphan detection) — that's fine. What it no
longer owns is the last mile. The agent assembles the viewer.

---

## build.py is not the mandatory renderer

<CRITICAL>
`build.py` is NOT required to be the renderer. When its parser, its template, or its
cache location fight harder than they help, stop using it as the renderer — the AST
already did its job (extracting the skeleton), and that half is done.

All three failures happened in real use:
- a custom parser that didn't read the meta block it was supposed to,
- a cache directory generated INSIDE the target repo being graphed,
- a viewer template hardcoded to a different project's vocabulary.

None of those touch the value of the extraction. Extract nodes + edges to a compact
JSON and let the agent assemble the HTML by hand from a reusable template. The
curation — the expensive half — is IDENTICAL either way.

The division of labor:
  the AST      -> extracts and verifies the skeleton
  the agent    -> arranges, curates, and builds
  the HTML     -> shows
</CRITICAL>

The default is by hand: the agent produces the viewer from the JSON with a plain
marker replace. A `build.py` renderer is at most an optional convenience for the
one-time initial render — its parser, template, and cache path are the three
parts that fought hardest in real use, which is why the skeleton, once extracted
to JSON, is all you actually need. For any UPDATE to an existing graph, do not use
it at all (see updating-an-existing-graph.md).

---

## Where the cache and artifacts go

<IMPORTANT>
NEVER write the AST cache or generated artifacts INSIDE the target repository being
graphed. It pollutes the very code you're mapping and can end up committed by
accident — the graph's byproducts leaking into the mapped source.

Point the extractor's output to an absolute path OUTSIDE the target: a `docs/` or
scratch directory that is NOT the graphed source tree.

Learned in real use: the cache dir was generated inside the source repo and had to
be removed and relocated after the fact.
</IMPORTANT>

Rule of thumb: the source tree you're graphing is read-only from the graph's point of
view. Inputs come out of it; nothing the graph produces goes back into it.

---

## The shape of the arranged JSON

This is the concrete structure the agent produces for a hand-built viewer,
shown with REAL example values (generic, not tied to any project):

```json
{
  "nodes": [
    { "id": "core_auth",        "label": "auth.js",       "file": "core/auth.js",        "layer": 2, "in": 20, "out": 26 },
    { "id": "core_session_wch", "label": "sessionWatcher", "file": "core/sessionWatcher.js", "layer": 3, "in": 7,  "out": 25 },
    { "id": "ui_login_index",   "label": "index.js",       "file": "ui/login/index.js",   "layer": 4, "in": 1,  "out": 2 }
  ],
  "edges": [
    { "s": "core_session_wch", "t": "core_auth", "r": "imports_from" },
    { "s": "ui_login_index",   "t": "core_auth", "r": "calls" }
  ]
}
```

Each field:

| Field | Meaning |
|---|---|
| `id` | stable identifier for the node — never changes across rebuilds |
| `label` | display name shown in the viewer |
| `file` | path or source id the node came from |
| `layer` | group number from Step 4 — vertical position in the viewer |
| `in` | in-degree: how many edges point AT this node |
| `out` | out-degree: how many edges leave this node |

For edges:

| Field | Meaning |
|---|---|
| `s` | source node id |
| `t` | target node id |
| `r` | relation type — e.g. `imports`, `calls`, `imports_from` |

---

## Assembling the viewer from the template

`scripts/viewer-template.html` is the canonical viewer. It already carries the
whole style — SVG edges, search box, per-layer and per-edge-type filters,
disambiguated labels, the curation side-panel, the curated/uncurated dot. Do NOT
rewrite the HTML from scratch each time; fill the template's markers. This is what
keeps every graph looking the same, whether the corpus is code or docs.

<CRITICAL>
Nothing project-specific is baked into the template — it has five markers the
agent fills at assembly time. This is the mechanism behind Step 7b's "nothing
domain-specific hardcoded" rule:

| Marker | Filled with |
|---|---|
| `__TITLE__` | the subsystem title (from `meta.titulo`) |
| `__SUBTITLE__` | the one-line description (from `meta.contexto`) |
| `__LAYERS__` | a JSON array of `{id, name, sub}`, one per group from Step 4 (the meta `layer_N` lines). Colors are assigned by index from the palette — do NOT hardcode a color per layer, so any number of layers works. |
| `__DATA__` | the arranged JSON (nodes + edges) from the shape above |
| `__CURATION__` | the per-node `what`/`why`/`gotcha`/`issue` map (Step 5), keyed by `file` |
</CRITICAL>

Assembly is a plain string replace of the five markers — no build step, no custom
parser (that's exactly the fragile machinery Step 3 replaces). The example lanes,
the panel's "start with the highest-out nodes" hint, and the search placeholder
are all generated FROM the data at runtime, never written into the template — so
the viewer never tells one project's story while showing another's (a real Step 7b
failure).

### `__LAYERS__` — real example

One entry per group from Step 4. `id` matches the node's `layer`; `name` and `sub`
come from the `meta` `layer_N` lines. NO color here — the template assigns it by
index from the palette:

```json
[
  { "id": 0, "name": "Cross-cutting", "sub": "infra everything uses" },
  { "id": 2, "name": "Cold start",    "sub": "resolves state on launch" },
  { "id": 3, "name": "Watch",         "sub": "listens and decides expiry" },
  { "id": 4, "name": "UI",            "sub": "screens, forms, inputs" }
]
```

### What it looks like rendered

The template lays out one horizontal **lane** per layer, top to bottom by `id`,
each lane holding its nodes as cards. A node card shows the label, its in/out
degrees, and a dot (green = curated, grey = not). Clicking a node lights its edges
(solid = out, dashed = in) and fills the side panel:

```
┌─ 3 · Watch ──────────────────────────────────────────────┐
│  listens and decides expiry                               │
│   ┌───────────────────┐   ┌───────────────────┐           │
│   │ sessionWatcher   ● │   │ expiryReducer    ○ │  ← ● curated
│   │ in 7 · out 25      │   │ in 3 · out 4       │    ○ not
│   └───────────────────┘   └───────────────────┘           │
└───────────────────────────────────────────────────────────┘
        │ solid = "uses"          ╎ dashed = "used by"
        ▼                         ╎
┌─ 2 · Cold start ─────────────────────────────────────────┐
│   ┌───────────────────┐                                   │
│   │ auth.js          ● │   ← highest out: appears first    │
│   │ in 20 · out 26     │                                   │
│   └───────────────────┘                                   │
└───────────────────────────────────────────────────────────┘
```

Side panel when a node is selected (built from `__CURATION__`):

```
2 · Cold start                              [badge, layer color]
core/auth.js
20 used by · 26 uses

What   Central token API: get/set/clear of the access token...
Why    The single door to credential storage...
⚠ gotcha   Keys here MUST match the secure-store set, or the
           value silently falls back to purgeable storage.

Uses (26)   → sessionStore   → jwtDecode   → ...
Used by (20) ← sessionWatcher ← loginForm   ← ...
```

Nodes with no curation show a "not curated yet" note instead of What/Why — that's
the Step 7b signal that the graph still has skeleton with no meaning on it.

<IMPORTANT>
`in` and `out` come from COUNTING the AST edges — never hand-set them. They're a
mechanical derivation of the edge list: `in` = edges where this node is `t`, `out` =
edges where this node is `s`. A hand-typed degree drifts out of sync with the edges
the moment either changes, and then the viewer lies about impact.
</IMPORTANT>

`layer` is the only node field that is a human decision (Step 4). Everything else in
`nodes` is either extracted (`file`, `label`) or counted (`in`, `out`).

---

## The additive-only rule

<CRITICAL>
Any script that writes the curation/arrangement file must be ADDITIVE. It can only:
- add keys that don't exist yet,

and must NEVER:
- rewrite the whole file, or
- overwrite a key that already has hand-written content.

Confirmed in real use: a grouping script that regenerated the whole file erased
already-written descriptions with no warning. Hours of curation gone in one run.

Structure is cheap — it regenerates in seconds from the AST. Meaning is expensive and
unrecoverable — it's a human reading whole units. The cheap thing must NEVER be able
to destroy the expensive thing. A structure-writing script that can touch a curated
key is a data-loss bug, not a convenience.
</CRITICAL>

Practical consequence: the arrangement pass (layers, degrees) and the curation pass
(meaning, see step-5-curation.md) write to the same file, but the arrangement pass
writes only into slots the curation pass hasn't filled. When in doubt, the script
reads the existing file first and merges key by key — it never opens the file for a
full overwrite.
