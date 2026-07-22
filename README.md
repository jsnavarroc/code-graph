# code-graph

A Claude skill for building a **hybrid code graph**: structure
(who calls whom, how many depend on what) comes from the AST automatically and
reliably; meaning (why something exists, what breaks if it fails, what race
condition it hides) is read and written by a human. The skill does both halves
and keeps them separate — it never lets one pass for the other.

## Why

A structure-only graph can consume **more** context than having no
graph at all: a node with 60 edges and no description forces opening 60 files
to understand it. Measured on real code, a curated graph uses ~1,000
tokens/query versus ~10,000 uncurated — 10x. What saves context isn't
the graph itself, it's the semantic density of its nodes.

Hence the rule that governs the whole skill: **never derive a description
from the symbol's name**. If the file hasn't been read, the node stays
undescribed. No exceptions.

## What it does

| The script does it | The agent does it by reading | The human decides it |
|---|---|---|
| Extract AST | Read each file | Scope: what's in |
| Compute impact | Write `what`/`why`/`ux` | What criterion groups things |
| Detect orphans | Detect duplication | Whether there's a dependency rule |
| Generate the viewer | Flag defects | Validate it isn't lying |

The result is a self-contained HTML viewer: node cards with
`character`/`what`/`why`/`ux`/`when`/`if_broken`, grouped into lanes according to
the project's real organization criterion (it doesn't assume dependency layers
— it can be Atomic Design, feature-sliced, by domain, whatever fits),
with blast-radius computed over the full graph.

## The 8 steps

1. **Plan** with the human — scope, grouping, dependency rule
   (optional), cross-cutting, noise to exclude, and subsystem introduction.
2. **Confirm the mode** — `code` (there's an AST via tree-sitter) or `docs` (corpus
   without code: Markdown, registry JSON, PDF).
3. **Configure and extract** — run `build.py --extract`.
4. **Curate the groups** — assign `layer` to each file, fast, before the
   meaning.
5. **Curate the meaning** — the bulk of it: read every file whole and write
   its fields. Validated in batches of 15-20 files.
6. **Flag defects** — `bug` / `dead` / `duplicate`, by hand, never by
   keyword.
7. **Verify** — the data (orphaned curation, coverage, violations) and what's
   SEEN (nothing hardcoded, complete lanes, scoped CSS).
8. **Maintain** — when closing the session, re-verify the code didn't move
   under already-curated nodes.

Each step exists because a real error motivated it — the full list is in
`SKILL.md`, "Errors this skill exists to prevent" section.

## `docs` mode

The principle (automatable structure + hand-read meaning) is
agnostic to the product type. For corpora without source code (a
research folder, a citation registry), `build.py` extracts nodes from Markdown,
registry JSON, or PDFs, and edges only from already explicitly
written references — never inferred by semantic similarity.

## What it does NOT cover

- Entire repos (proven on subsystems of up to ~900 nodes out of 3,500).
- Automatically keeping the graph alive: structure regenerates, but
  curation has to be reviewed by hand when the code changes.
- Dynamic imports (`require(variable)`, runtime `import()`).
- Relations inferred by meaning, in any mode — if the relation
  isn't written, it isn't drawn.

## Structure

```
SKILL.md                    # the complete instructions, step by step
references/
  planning.md                # detail for Step 1 (planning)
  curation.md                 # detail for Step 5 (meaning curation)
scripts/
  build.py                    # extraction + graph build
  viewer-template.html        # self-contained HTML viewer template
```

## Usage

This directory is a [Claude Code skill](https://docs.claude.com/claude-code/skills).
Place it in `~/.claude/skills/code-graph/` (or the project's skills
directory) and it activates when the task matches its description — understanding
a subsystem you didn't write, mapping before refactoring, or asking for it
explicitly ("code graph", "map the subsystem").

## Research paper

The methodology behind the 8 steps — each one derived from a real failure
observed while building this skill, and corroborated against 160 literature
sources — is written up as a paper: *"Curación Verificable de Grafos de
Código Híbridos: una Metodología de Ocho Pasos Derivada de un Caso Real y
Corroborada por Literatura"* (DOI: [10.5281/zenodo.21498564](https://doi.org/10.5281/zenodo.21498564)).
