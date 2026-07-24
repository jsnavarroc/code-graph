# Updating an existing graph

The 8 steps BUILD a graph from scratch. This file is the other job: a graph
already exists and the code (or the curation) needs to catch up. It's shorter,
and it has one hard rule that the build steps only imply.

## Contents

- [The one rule](#the-one-rule)
- [What NOT to do](#what-not-to-do)
- [The files you touch](#the-files-you-touch)
- [The update flow](#the-update-flow)
- [Verify](#verify)

---

## The one rule

<CRITICAL>
The AST mapped the skeleton ONCE, when the graph was first built. Updating is NOT
re-running a build tool. It is three by-hand edits: adjust the data JSON, adjust
the curation JSON (additively), re-assemble the viewer by string-replacing the
template markers. Nothing regenerates the whole thing.

Why by hand: the curation is the expensive half — read and written one file at a
time. A build tool that regenerates from a source-of-truth file will silently
overwrite it. That is exactly the failure this skill exists to prevent (structure
is cheap and regenerates in seconds; meaning is expensive and unrecoverable if
lost).
</CRITICAL>

---

## What NOT to do

An existing graph folder often still carries the scaffolding from when it was
first built — a `build.py`, a `curation.yaml`, an `index.html`, an AST cache
directory. Do NOT be misled by their presence:

- **Do NOT run `build.py`** (or any `--extract` / regenerate command). It rebuilds
  from the wrong source (`curation.yaml`, which is the old parser's input) and
  produces a viewer with none of the hand-written meaning.
- **Do NOT edit `curation.yaml`.** The real curation lives in the curation JSON
  (`what`/`why`/`gotcha` per file). `curation.yaml` is leftover from the old
  build path.
- **Do NOT re-extract the AST just to update curation.** Only re-extract if the
  CODE's structure changed (files added/removed/renamed) — and even then, only to
  refresh nodes/edges by hand, never the curation.
- **Do NOT regenerate the data or curation JSON wholesale.** Edit in place.

If the folder's stale scaffolding keeps causing this confusion, the honest fix is
to delete it (the `build.py`, `curation.yaml`, `index.html`, old template, AST
cache) so only the real files remain. Ask the human before deleting.

---

## The files you touch

Three, and only three:

| File | Holds | How you edit it |
|---|---|---|
| `data.json` | the skeleton: `nodes` + `edges` (see step-3-arrange.md for the shape) | add/remove nodes and edges by hand; recompute `in`/`out` from the edges |
| `curation.json` | the meaning: `{what, why, gotcha, issue}` keyed by `file` | ADDITIVE only — add or update a key, never rewrite the file |
| `<graph>.html` | the assembled viewer | never edited directly — produced by the re-assemble step |

The template (`viewer-template.html`) is not edited per-update; it's the fixed
shell whose markers get filled.

---

## The update flow

**1. Code changed structurally?** (files added, removed, renamed)
   - If NO: skip to step 2, the skeleton is still valid.
   - If YES: re-run the AST extractor (graphify) directly — see step-2-extract.md
     — and reconcile the fresh node/edge set into `data.json` by hand: add the new
     nodes/edges, drop the gone ones, recompute `in`/`out` from the edges. A node
     whose file no longer exists is removed, not kept (a phantom node — see
     step-7-verify.md).

**2. Curate the new or changed units.** Read each one entirely and write
   `what`/`why`/`gotcha` into `curation.json`, additively (step-5-curation.md).
   Never derive from the name.

**3. Re-assemble the viewer** by string-replacing the markers with the current
   JSON (step-3-arrange.md):

```python
import json
tpl = open("viewer-template.html").read()
data = open("data.json").read()
cur  = open("curation.json").read()
# plus __TITLE__, __SUBTITLE__, __LAYERS__ from meta
html = tpl.replace("__DATA__", data).replace("__CURATION__", cur)
open("graph.html", "w").write(html)
```

No build tool. A plain marker replace — that's the whole assembly.

---

## Verify

Same as step-7-verify.md, on the re-assembled viewer:

- [ ] **0 uncurated nodes** — every node in `data.json` has a `what` in
      `curation.json`.
- [ ] **0 orphaned curation** — every `file` key in `curation.json` still exists
      on disk.
- [ ] **0 phantom nodes** — every node's `file` still exists on disk.
- [ ] **Scope still holds** — e.g. if the graph is one platform only, the other
      platform's files have not crept back in (step-1-planning.md,
      step-4-grouping.md).
- [ ] **The edges still draw, search and filters still work** — open it and look
      (step-7-verify.md, 7b).

This step doesn't replace step-8-maintain.md's deeper check (a file that still
EXISTS but was rewritten underneath a correct curation) — run that too when time
has passed.
