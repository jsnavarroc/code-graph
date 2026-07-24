# Step 2 — Confirm the mode and extract structure

## Contents

- [The central principle: the AST informs, the agent builds](#the-central-principle-the-ast-informs-the-agent-builds)
- [Deciding the MODE before extracting](#deciding-the-mode-before-extracting)
- [`code` mode setup](#code-mode-setup)
- [`docs` mode setup](#docs-mode-setup)
- [Running extraction](#running-extraction)
- [build.py is not required to be the renderer](#buildpy-is-not-required-to-be-the-renderer)

Extraction produces the graph's SKELETON — the nodes and the edges. It's the ONLY
layer that must never be guessed.

---

## The central principle: the AST informs, the agent builds

<CRITICAL>
"The AST informs; the agent builds." There are three stages, not two:

1. **EXTRACT** (AST / graphify) -> raw JSON of nodes + edges. This is the ONLY
   source of truth for the skeleton. The agent NEVER invents an edge. Inferring
   "module A probably imports module B because it makes sense" hallucinates
   dependencies and makes the graph unreliable at exactly the layer that is
   supposed to be verifiable. If the AST didn't extract an edge, it isn't drawn.
   A dynamic `require(variable)` that the parser can't resolve stays uncurated by
   hand — never guessed.
2. **ARRANGE + CURATE** (agent) -> see step-3-arrange.md and step-5-curation.md.
3. **SHOW** -> the viewer.
</CRITICAL>

Real lesson: keeping the AST edges is what caught a phantom node. Its edge
(`module A imports_from module B`) was still in the JSON while `module B` had
already vanished from disk. That contradiction is only detectable because the edge
came from the AST, not from the agent's memory. If the agent had generated edges
from memory, it would have kept the stale edge and gone on lying with confidence —
the graph would look complete and be wrong.

---

## Deciding the MODE before extracting

<CRITICAL>
Decide the mode WITH the human before running anything. Running the wrong mode
fails silently: `code` on a corpus without code gives an empty graph with no clear
warning, and you won't know until you've wasted the extraction.
</CRITICAL>

Confirm what the target actually contains:

```bash
find <target> -type f | grep -viE '\.(md|txt|pdf|json|ya?ml|csv)$' | head
```

| What the command shows | Mode |
|---|---|
| Real source code (`.js`, `.py`, `.ext`, ...) | `EXTRACT_MODE = 'code'` |
| Only a corpus without code (PDFs, Markdown, citation JSON, notes) | `EXTRACT_MODE = 'docs'` |

If the list comes back empty, the target is a document corpus -> `docs`. If it's
full of source files -> `code`. When it's mixed, ask the human which subsystem the
graph is for and pick the mode that matches it.

---

## `code` mode setup

graphify extracts the AST for 25 languages using tree-sitter, locally, with no API
key. Confirm the toolchain before extracting — keep this block exactly:

```bash
command -v python3 >/dev/null || { echo "python3 is not available on PATH. Install it before continuing."; exit 1; }
python3 -c "import graphify" 2>/dev/null || pip install graphifyy -q
python3 -c "import graphify" 2>/dev/null || { echo "graphify did not become available after install. Try 'pip install graphifyy --break-system-packages' or a venv, and confirm with 'python3 -c \"import graphify\"' before continuing."; exit 1; }
```

<IMPORTANT>
Don't proceed past a failed import. An extraction that runs against a half-installed
parser produces a partial skeleton that looks complete — the same failure mode as
running the wrong mode.
</IMPORTANT>

---

## `docs` mode setup

No install needed — the `docs` extractor has no external dependencies.

Before extracting, confirm the corpus has explicit references between documents:
wikilinks (`[[id]]`), relative links, or relation fields in JSON (`refs`,
`cita_a`, `relates_to`). Those are the edges.

Without them, the graph comes out with no edges. That's correct, not a bug —
there's nothing to connect that wouldn't be hallucinated. A corpus of disconnected
nodes is still useful for curation; it just can't be navigated by edges. (Which
field becomes the edge, when there's more than one candidate, is decided with the
human — see step-1-planning.md.)

---

## Running extraction

```bash
python3 build.py --extract
```

Report to the human, in these terms:

| Count | What it means |
|---|---|
| core nodes | The seeds — the subsystem itself |
| neighbors | The blast-radius pulled in by following edges |
| edges | The relations the AST actually found |

<CRITICAL>
More than ~1500 nodes -> STOP and review scope with the human. The graph is
capturing too much: curation becomes unviable (nobody curates 1500 nodes by hand),
and the viewer turns into a hairball nobody reads. The fix is upstream — tighten
the seeds in step-1-planning.md, not down here.
</CRITICAL>

---

## build.py is not required to be the renderer

`build.py` extracts AND, by default, renders the HTML. But the renderer is not
load-bearing. When its parser, template, or cache location fight harder than they
help — a template that won't take the layout, a cache that keeps serving a stale
build — the AST has already done its job the moment the nodes and edges are in JSON.

At that point: extract nodes + edges to JSON and let the agent assemble the HTML by
hand. This is detailed in step-3-arrange.md. The curation is IDENTICAL either way —
the meaning layer doesn't care who wrote the HTML, only that the skeleton it hangs
on came from the AST and nothing was invented.
