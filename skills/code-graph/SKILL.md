---
name: code-graph
description: Use when someone needs to understand a complex subsystem they didn't write - "how does X work", "what breaks if I change Y", onboarding to unfamiliar code, or mapping a subsystem before refactoring it. Builds a hybrid code graph - AST extracts structure, you read the code and curate meaning - and renders it as a self-contained HTML viewer. Also triggers on "grafo de codigo", "code graph", "mapear el subsistema", "graficar el codigo".
---

# Building a hybrid code graph

A useful code graph is NOT generated: it's built. The AST gives you structure
(who calls whom, how many depend on what), and that's free and reliable. The meaning
-why something exists, what breaks if it fails, what race condition it hides- has to
be read and written. This skill does both halves and keeps them separate.

## Why this can't be fully automated

<CRITICAL>
A structure-only graph can consume MORE context than having no graph at all.
Measured on real code: a curated graph uses ~1,000 tokens/query versus
~10,000 uncurated (Codebase-Memory, 31 repos, Claude backend) - 10x. The reason
is that a node with 60 edges and no description forces opening 60 files.
A curated node answers in three lines.

What saves context isn't the graph. It's the semantic density of its nodes.
</CRITICAL>

Hence the rule that governs this skill:

**NEVER derive a description from the symbol's name.** `setIsNavigating` ->
"writes is navigating to global state" is a tautology disguised as
documentation: it pollutes the graph with noise that looks like knowledge. If you
haven't read the file, the node stays undescribed. No exceptions.

<CRITICAL>
The same rule applies to ANY shortcut, not just deriving from the name. If you
find yourself writing a script that generates `what`/`why`/`character` for
several nodes at once -a template, a heuristic, a separate LLM without reading
each file- it's the same tautology with extra steps. Curating 40 nodes takes the
time of reading 40 files. There's no shortcut by volume: if the number of
uncurated nodes tempts you to automate the content, that's a signal that
more curation time is needed, not a tool to replace it.

Python (`build.py`) ONLY touches structure: extracting, computing degrees, detecting
orphans, rendering. It must never write the CONTENT of `what`/`why`/
`character`/`gotchas` - that comes exclusively from a human (or the
agent, actually reading and with the human validating) writing each field.
</CRITICAL>

## The steps

Follow the order. It isn't arbitrary: every late decision forces redoing work.
In the case that originated this skill, grouping AFTER curating produced 112 false
positives that had to be undone.

Create a todo for each step. Each step below is a summary; the linked file has the
full procedure, the `<CRITICAL>` details, and the real-use lessons. Read the
step's file when you reach it — one level deep, so it loads complete.

### Step 1 — Plan (with the human, before touching anything)

Six written answers: subsystem + seeds, grouping criterion (explore, search the
web, suggest — never assume dependency layers), optional dependency rule,
cross-cutting group 0, noise (tests, styles, generated files, **and the OTHER
platform** — ask which `.ios`/`.android`, `dev`/`prod` target is in scope), and
the system-level introduction paragraph. Don't decide any of these alone.

→ **[step-1-planning.md](references/step-1-planning.md)**

### Step 2 — Confirm the mode and extract structure

The AST informs; the agent builds. Extraction produces the SKELETON (nodes +
edges) — the ONLY layer that must never be guessed. The agent NEVER invents an
edge; if the AST didn't extract it, it isn't drawn. Decide `code` vs `docs` mode
with the human (the wrong mode fails silently). Run the extractor, report node and
edge counts; stop at ~1500 nodes.

→ **[step-2-extract.md](references/step-2-extract.md)**

### Step 3 — Arrange the extracted JSON (the agent builds, not build.py)

`build.py` stops being the mandatory renderer. It computes degrees and detects
orphans over the AST JSON; the agent assigns layers, curates, and assembles the
viewer from a reusable template. Keep the AST cache and artifacts OUTSIDE the
graphed repo. Any script that writes the curation file must be additive-only —
structure must never destroy meaning.

→ **[step-3-arrange.md](references/step-3-arrange.md)**

### Step 4 — Curate the groups (fast, first)

Assign a `layer` to each node (additive-only) and declare the lanes in `meta`.
Cross-cutting files put their symbols in group 0 too. **Disambiguate colliding
labels** — if several nodes share a label (`index.js`) they're indistinguishable;
disambiguate with whatever tells them apart in this corpus (parent folder in code,
year/author in docs). Empty declared lanes stay, with a note.

→ **[step-4-grouping.md](references/step-4-grouping.md)**

### Step 5 — Curate the meaning (the bulk of the work)

Read each unit ENTIRELY, then write `character`/`what`/`why`/`ux`/`when`/
`if_broken`. Never derive from the name. The high-entropy `why` often lives in the
commit/ticket history, not the current file — follow it and cite the source.
Validate with the human in batches of 15-20. Record the commit each node was
curated against (Step 8 needs it).

→ **[step-5-curation.md](references/step-5-curation.md)**

### Step 6 — Flag defects (by hand, node by node)

Set the `issue` flag by READING the node — never by keyword search. Three types:
`bug`, `dead`, `duplicate`. For `dead`, start from the build's zero-consumer
candidates (confirm each — public exports are false positives). Record the defect
in the node's prose too, so the viewer explains it, not just colors it.

→ **[step-6-defects.md](references/step-6-defects.md)**

### Step 7 — Verify and ship

Three checks: **7a data** (orphans 0, uncurated 0, no phantom nodes pointing at
missing files); **7b what's SEEN** — actually open the viewer: the edges are
drawn (a graph whose relations are only side-panel text is a table), a search box
past ~30 nodes, per-layer and per-edge-type filters, disambiguated labels, nothing
from another project hardcoded; **7c the human** validates what they see.

→ **[step-7-verify.md](references/step-7-verify.md)**

### Step 8 — Maintain: re-verify before closing (if time passed or code changed)

The graph decays because the code moves while you curate. Before closing, re-extract
and check: orphans still 0, AND — the hard one — a file that still EXISTS may have
been rewritten underneath a correct curation (the orphan check stays green because
the file is there). Re-verify files whose hash changed since Step 5. Re-check that
the other platform's nodes haven't crept back in.

→ **[step-8-maintain.md](references/step-8-maintain.md)**

## Errors this skill exists to prevent

All of these actually happened while building the graph that originated it:

| Error | What it produced | The step that prevents it |
|---|---|---|
| Deriving descriptions from the name | Tautologies masquerading as docs | Step 5.1 |
| Infrastructure marked as a group | 112 false positives out of 112 | Step 1.4 |
| Invented curation keys | ~15 nodes pointing at nothing | The orphan warning |
| Counting inheritance as description | 100% reported with 547 gaps | Step 7 |
| Detecting defects by keyword | Nodes silently falling out of the filter | Step 6 |
| Curating before grouping | Redoing all the violations | The order of the steps |
| Assuming layers where there's composition | Alarms that mean nothing | Step 1.2 and 1.3 |
| Domain text baked into the template | One project's viewer telling another project's story | Step 7b |
| Verifying only data, never what's rendered | Three visual failures with all verification green | Step 7b |
| An unscoped element-level CSS selector | Legend icons covering their own text | Step 7b |
| Declaring the graph good and never looking again even as the code kept changing | Curation silently lying with no warning flagging it | Step 8 |
| A viewer that shows relations only as side-panel text | A table pretending to be a graph; "it has no edges" | Step 7b |
| No search / no filters past a few dozen nodes | Viewer unusable at scale | Step 7b |
| Repeated labels (`index.js`) left as-is | Nodes indistinguishable in the viewer | Step 4 |
| The other platform's files left in scope | One platform's nodes in a single-platform graph, removed after the fact | Step 1.5 |
| A curated file rewritten underneath, still existing | Curation lying while the orphan check stays green | Step 8 |
| Letting the agent invent edges instead of the AST | Hallucinated dependencies; skeleton no longer verifiable | Step 2 |


## What this skill does NOT cover

- **Entire repos.** This is proven on subsystems (~900 nodes out of 3,500). A
  full monorepo is a different problem and isn't solved yet.
- **Keeping the graph alive.** It regenerates the structure, but if the code (or the
  corpus) changes, the curation has to be reviewed by hand. The orphan warning
  helps, it doesn't solve it.
- **Dynamic imports.** `require(variable)` or runtime `import()` aren't seen
  by the AST. If you suspect dynamic dispatch, verify by hand.
- **Relations inferred by meaning, in any mode.** Neither in `code`
  (the AST doesn't guess a dynamic import) nor in `docs` (the extractor doesn't guess
  that two papers "are similar" without an explicit link). If the relation isn't
  written, it isn't drawn - it's curated by hand or left unconnected.

## Corpus without code

For non-code corpora (PDFs, Markdown, research JSON), the extraction layer
differs but the curate-by-reading principle is identical. See
**[docs-mode.md](references/docs-mode.md)**.
