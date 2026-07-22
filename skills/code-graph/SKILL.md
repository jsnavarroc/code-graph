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

## Division of labor

| The script does it | YOU do it by reading | The HUMAN decides it |
|---|---|---|
| Extract AST | Read each file | Scope: what's in |
| Compute impact | Write what/why/ux | What criterion groups things |
| Detect orphans | Detect duplication | Whether there's a dependency rule |
| Generate the viewer | Flag defects | Validate it isn't lying |

## The steps

Follow the order. It isn't arbitrary: every late decision forces redoing work.
In the case that originated this skill, grouping AFTER curating produced 112 false
positives that had to be undone.

Create a todo for each step.

### Step 1 - PLAN (with the human, before touching anything)

<IMPORTANT>
This step is what prevents redoing work. Don't skip it or decide it alone.
Read `references/planning.md` and ask the human the questions (five always,
plus a sixth if the mode is `docs` - see "Corpus without code" below).
</IMPORTANT>

<CRITICAL>
DO NOT assume the project is organized in dependency layers. That's ONE form among
many: Atomic Design, hexagonal, feature-sliced, by domain, by artifact
type, REST/GraphQL/microservices, encoders/decoders...

Read the structure, CONTRAST it with what's published (search the web for the
pattern you think you see), SUGGEST, and let the human decide. A graph grouped with
an invented criterion lies on every query.
</CRITICAL>

You leave this step with six written answers:
1. **Subsystem and seeds** - which paths form the core
2. **Grouping** - what criterion groups the nodes (you read, search, suggest)
3. **Dependency rule** - OPTIONAL: only if there's a direction to watch
4. **Cross-cutting (group 0)** - what everyone uses and belongs to no group
5. **Noise** - what gets excluded (tests, styles, generated files)
6. **Subsystem introduction** - the context paragraph without which no
   node can be understood (see 1.6 below)

About (2): **use web search**. Your memory of architectures has gaps and there are
conventions that have changed. If you see `app/ pages/ widgets/ entities/`, search whether it's
Feature-Sliced Design before inventing the groups yourself. What's local overrides what's
published: group what's THERE, not what the canonical pattern says should be there.

About (3): grouping and depending are different axes. Atomic Design groups by
composition; REST/GraphQL are parallel categories. There's no direction to
violate there, and `CHECK_LAYER_VIOLATIONS` stays False. Without a rule, the graph still
serves blast-radius and comprehension purposes: it just doesn't flag anything in red.

**1.6 - Write the subsystem introduction (SYSTEM level, not node level).**

<IMPORTANT>
Everything above (1-5) curates NODES: what each piece does. None of that answers
why the whole subsystem exists or what breaks if it fails as a whole -
and that paragraph is, of the entire graph, the one with the highest semantic
density: it's what turns a list of cards into something understood at a glance. Without it,
the viewer has nothing to show before the human clicks on a
node (see `meta.contexto` in the block below).

Backing: production software architecture (Larsen & Moghaddam 2026,
"RAD-AI": the same system-level gap pattern appears in three
systems from unrelated organizations - Uber, Netflix, and the authors' own
systems - which indicates it's structural and not a
peculiarity of one project, not something only this case was missing).
</IMPORTANT>

Ask the human in closed format, never an open "write me the introduction":

> "Before curating the first node, I need the system context. Answer
> briefly, one sentence per point - I can draft the final paragraph myself with your
> answers:
>   a) **Why this subsystem exists** - what real-world problem it solves
>      (e.g.: 'without this, <who uses it> would have to do <the bad alternative>')
>   b) **The problem that led to this way of solving it** - if it came from a
>      constraint, an incident, or a design decision (e.g.: 'it was built
>      this way because <the constraint or the case that failed before>')
>   c) **How it's noticeable when it works / when it fails** - the observable
>      signal for whoever uses it, not for whoever codes it (e.g.: '<the visible symptom>
>      when this breaks')
> If any doesn't apply, say so and I'll leave it out - no need to force all three."

With those answers, write in the `meta:` block of `curation.yaml`:
```yaml
meta:
  titulo: <short subsystem name>
  contexto: <the answer to (a), in prose>
  problema: <the answer to (b), in prose - omit the key if not applicable>
  sintomas: <the answer to (c), in prose - omit the key if not applicable>
```
If the human doesn't have an answer yet, leave the step open and continue with the
rest of the planning - but don't close the subsystem without coming back to this:
a graph without `meta.contexto` forces the viewer to say so instead of making it up
(same principle as "don't derive the description from the name" in Step 5).

### Step 2 - Confirm the mode and prepare extraction

<CRITICAL>
Decide the mode BEFORE proceeding. Confirm with
`find <target> -type f | grep -viE '\.(md|txt|pdf|json|ya?ml|csv)$' | head`:

- If there's real source code -> `EXTRACT_MODE = 'code'` (Step 2a).
- If the target is a corpus without code (PDFs, Markdown, citation JSON) ->
  `EXTRACT_MODE = 'docs'` (Step 2b). See "Corpus without code" section below.

Running the wrong mode doesn't fail loudly: `code` on a corpus without
code gives an empty graph with no clear warning. Decide it with the human, don't assume it.
</CRITICAL>

**Step 2a - `code` mode:**
```bash
command -v python3 >/dev/null || { echo "python3 is not available on PATH. Install it before continuing."; exit 1; }
python3 -c "import graphify" 2>/dev/null || pip install graphifyy -q
python3 -c "import graphify" 2>/dev/null || { echo "graphify did not become available after install. Try 'pip install graphifyy --break-system-packages' or a venv, and confirm with 'python3 -c \"import graphify\"' before continuing."; exit 1; }
```
graphify extracts AST for 25 languages with tree-sitter, locally, no API key.

**Step 2b - `docs` mode:** doesn't need to install anything - the extractor in
`build.py` has no external dependencies. Just confirm the corpus has
explicit references between documents (wikilinks, relation fields in the
JSON); if it doesn't, the graph will come out with no edges (see below).

### Step 3 - Configure and extract

Copy `scripts/build.py` into the project (suggested: `docs/code-graph/`) and fill in its
CONFIG block with what came out of Step 1. Then:

```bash
python3 build.py --extract
```

Report to the human: how many core nodes, how many neighbors, how many edges.

If more than ~1500 nodes come out, stop and review the scope with the human: the graph
is capturing too much and curation will become unviable.

### Step 4 - Curate the groups (fast, first)

<CRITICAL>
Any tool or script that touches `curation.yaml` - including one that
YOU write yourself to assign `layer` to many files at once - must be
ADDITIVE: it can only add keys that don't exist yet, never rewrite the
whole file or touch a key that already has hand-written content.
Confirmed on a real corpus: a grouping script that regenerated the entire
`curation.yaml` erased three already-written `what`/`why` descriptions,
with no warning, when re-run after a re-extraction. They were recovered only
because they were still in that session's context - in another session, they would have been lost
without a trace. Structure (cheap, regenerates in seconds) must never be able to
destroy meaning (expensive, unrecoverable if lost).
</CRITICAL>

Before the meaning, assign `layer` to each FILE in `curation.yaml` - the
group number that came out of Step 1.2. It's fast and gives each node its place in
the viewer.

Also declare the groups in the `meta:` block, which is where the viewer draws
the lanes and their names from:

```yaml
meta:
  layer_1: Atoms - dependency-free building blocks
  layer_2: Molecules - composition of atoms
  layer_3: Organisms - complete sections
```

<IMPORTANT>
If a file is cross-cutting (group 0), its symbols are too. Curating the file
as cross-cutting and leaving its symbols in another group breaks the exemption through the
back door: edges point to the symbol, not the file.
</IMPORTANT>

<CRITICAL>
If the corpus mixes several distinct NAMESPACES under the same grouping
criterion (e.g.: some lanes are literature categories, others are
your own findings, others are unresolved questions - any case where
"the number 6" means something different depending on which lane it's in), DO NOT
number the lanes in a single sequence (`layer_1`...`layer_N`). A loose number
doesn't say which namespace it belongs to without memorizing an external table -
the same problem as using an internal finding ID (`H-6`) as if it were
self-explanatory outside its source document.

Use an explicit prefix per namespace in the lane's NAME
(not in the number): if a project has "literature gaps", "own
findings", and "open questions", the lanes are named with that
readable prefix (the project chooses the words - there's no fixed list),
never just a number. The human decides the prefixes in Step 1.2, along with the rest
of the grouping criterion.
</CRITICAL>

If you enabled `CHECK_LAYER_VIOLATIONS`, run `python3 build.py` and look at the
violations. If dozens come out, there's almost certainly infrastructure not marked as
cross-cutting: go back to Step 1.4.

<IMPORTANT>
A declared lane with no nodes is NOT an error to clean up. If a group ends up
empty because its only node was removed or stopped applying (e.g.: a source
discarded for not meeting a project quality criterion), leave it
declared in `meta:` with a short note on why it's empty and since when.
An empty lane with a note is honest information about an open gap;
deleting it hides it. Same principle as "the viewer says it has no
introduction written instead of making one up" (Step 1.6) applied to lanes.
</IMPORTANT>

### Step 5 - Curate the meaning (the bulk of the work)

Read `references/curation.md` before writing the first description.

<IMPORTANT>
Before the first node, ask the human whether the default field set
(`character`/`what`/`why`/`ux`/`when`/`if_broken`) is enough or whether this project
needs one of its own (compliance, physical constraint, node owner...).
See the closed question in `references/curation.md`, "The fields" section -
don't decide this alone or leave it to be discovered halfway through curation.
</IMPORTANT>

For each file in the subsystem:
1. **Read it entirely.** Not the name, not the signature: the file.

<IMPORTANT>
The high-entropy "why" is frequently not in the current file -
it's in the history of why it changed. Before writing `why`, if the file
has history available, review it (`git log -p` on that file, or the
commit message that introduced the suspicious line via `git blame` +
`git show`). If the project references a ticket, issue, or external
discussion (a Jira/GitHub ID in a commit or comment), follow that reference if it's
accessible. This is ONE MORE source that enriches reading the file - never
a substitute for reading it, and never something the human doesn't see: if the commit or the
ticket reveals the why, cite that source in `why` (e.g. "see commit abc123" or
"resolved in issue #42"), don't write it as if you had deduced it from the
code alone.

Backing: a case documented in the literature shows exactly this pattern
- a synchronization lock whose reason for being ("the legacy banking mainframe
crashes if requests arrive out of order") wasn't in any
code comment, but in an already-resolved Jira ticket (Peng & Wang,
2026, "Code Digital Twin", Figure 1). Tacit knowledge -responsibility,
intent, design reasons- lives scattered across the code, configuration,
discussions, and version history, not just in the file in front of
you.
</IMPORTANT>

2. Write `character`: what TYPE of thing it is (singleton, hook, DAO, reducer,
   native module...). The vocabulary comes from the project, not a catalog.
3. Write `what`, `why`, `ux`, `when`, `if_broken` (plus the project's own
   fields if the human defined any in the previous step).
4. Decide `collapse` (see below).
5. Flag `gotchas` when the code hides something non-obvious.
6. Flag `issue` when the node has a defect (see Step 6).

**On collapsing file + homonymous symbol:**

<CRITICAL>
DO NOT collapse just because the names match. Collapse when the file and the symbol are
the SAME CONCEPT - and that's decided by reading what the file exports:

  ONE character  -> collapse. A file exporting a single main entity
                  (a function, a class): the file IS that entity. Two
                  nodes would be the same concept duplicated.
  TWO or more    -> DO NOT collapse. A file that exports, for example, a singleton
                  class AND an independent function with almost disjoint consumers:
                  merging them joins two APIs used separately.

The reliable clue: is the homonym the file's `export default`? If it is,
collapse. If the file exports several things of equal standing, they're distinct nodes.
</CRITICAL>

When collapsing, the degrees get MERGED. In the original case the impact was
split in two -whoever imported the module counted on one node, whoever called the
function on another- and neither of the two numbers was the real one: 60 + 30 = 90.

**Validate in batches.** Every 15-20 files, run the build and show the human
2-3 descriptions. Ask if the level is right. It's cheap to correct the
criterion at file 20 and very expensive at file 200.

After each batch:
```bash
python3 build.py
```
If it warns about **orphaned curation**, a key points to code that doesn't exist:
fix it BEFORE continuing. That warning is what keeps the graph from lying.

### Step 6 - Flag defects (by hand, node by node)

<CRITICAL>
YOU set the `issue` flag by reading the node. NEVER deduce it by searching for a
keyword in the text: the day someone writes a gotcha with different
words, the node disappears from the filter and nobody notices.
</CRITICAL>

Three types:
- `bug` - it's wrong and it's noticeable
- `dead` - written but never runs (commented out, stub, never called)
- `duplicate` - the same logic repeated in several places

**For `dead`, start from the candidates the build already computed**, not
900 nodes blindly. `python3 build.py` reports symbols with 0
consumers across the ENTIRE graph (not just the subsystem) - it's the same
reachability signal automatic dead code detection uses in the
literature, with 87.9% accuracy combining static+dynamic analysis
(Malavolta et al., 2023, "Lacuna", IEEE TSE). It doesn't decide for you: 17.5% of those
candidates are real false positives (public exports, entry points) -
you confirm each one, the list just narrows down where to look first.

For duplicates, actually search for patterns before flagging:
```bash
grep -rn "<the suspicious pattern>" src/ --include="*.js" | grep -v test
```

### Step 7 - Verify and ship

```bash
python3 build.py --extract    # clean regeneration from scratch
```

**7a - The data.** Check and report:
- [ ] Orphaned curation: **0**
- [ ] Nodes with no description of their own: **0** by the time Step 7 closes (see the
      block below - never a loose number that gets reported and left as is)
- [ ] Violations (if enabled): real signal or unmarked cross-cutting?
- [ ] Dropped edges: if the build warns, why? A silent drop makes an
      incomplete graph look complete.

<CRITICAL>
"Nodes without description: N, just report the number" is NOT an acceptable
outcome of Step 7 - it's a half-checked box. An uncurated node isn't
neutral information: it's pending work that hasn't been decided, and "decide later"
in practice means it stays invisible in the viewer forever.

YOU don't decide a node is "uncurable" and exclude it on your own - that's
scope, and scope is decided by the human (Step 1), not a heuristic
on the fly. For each node without its own description:

1. **Curating it is the default path.** If the node has readable content
   (code, text, a structured document), read it and write `what`/`why`
   as Step 5 requires - there's no shortcut by volume: 20 uncurated nodes are
   20 files that need reading, not a figure to report and move on.
2. **If you're unsure whether a node is curable, or there are many nodes of the same type,
   ask the human - never decide alone.** Closed format, with what you
   already know about the node:
   > "I found N nodes of type <X> uncurated (e.g.: <2-3 real examples>).
   > Should we curate them one by one, exclude them with a reason (tell me which),
   > or are they the same concept as an already-curated node and need to be merged?"
   The human's answer -curate, exclude with a reason, or merge- is what
   gets applied. None of the three is assumed by default.

If you suspect many "uncurated" nodes are actually the SAME work
counted twice (e.g.: one node per source file AND one node per its metadata
record, both representing the same unit), say so in the question
above as one of the options - it's a Step 1 scoping problem, not
something solved by leaving both nodes uncurated until "deciding later."
</CRITICAL>

**7b - What's SEEN.** It's not enough that "the viewer opens and the JS throws no error."

<CRITICAL>
That check passes even if the viewer is broken. Confirmed: on a real corpus it
passed clean while the panel showed the narrative of ANOTHER project, was missing 10
of 18 lanes, and the legend icons stretched until they covered their own text.
No data verification catches a presentation failure.
</CRITICAL>

Actually open the viewer and go through EVERY surface that renders text or
icons - legend, introduction panel, lane labels, node card:

- [ ] **Nothing domain-specific is hardcoded in the template.** Every visible label
      comes from `meta:`. If you read a word that belongs to ANOTHER project (or to
      the case that originated the template), it's fossilized text: move it to `meta`.
- [ ] **The vocabulary is THIS project's.** If you grouped by domain, the
      viewer can't say "layer." It comes from `meta.grupo_label`.
- [ ] **Declared lanes == drawn lanes.** Count them. A filter
      that's too narrow silently drops them and their nodes are left with no place.
- [ ] **Only what this graph actually uses is shown.** Without a dependency rule, the
      legend must not offer "violation"; without flagged defects, it must not
      list them.
- [ ] **No loose element-level CSS selector** (`svg{}`, `div{}`, `circle{}`).
      A global rule meant for the canvas also reaches
      inline icons and deforms them - and CSS wins over `width`/`height` attributes.
      Scope them with an id or class.
- [ ] **Nothing overflows its box** with the project's real text, which is
      longer than the example's.

Fix it in the TEMPLATE, not in the generated `index.html`: the build overwrites it.

**7c - The human.** Open the viewer and pass the ball: **the human validates the result.**
Ask them about what they see, not about the numbers. In the case that originated this
section, all three visual failures were found by the human looking at the
screen, after all automated verification came back green.

### Step 8 - Maintain: re-verify before closing the session (if time passed or there were changes)

<IMPORTANT>
The graph doesn't decay with age: it decays because the code underneath
keeps moving while you curate. A study of 1000 GitHub repositories
found that more than a quarter (28.9%) had documentation with at least
one reference to code that no longer existed - and the confirmed pattern is that the
same commit that changes the code is the one that leaves the documentation lying,
with no warning until something explicitly reviews it (Tan, Wagner & Treude,
2023, "Wait, wasn't that code here before?"). Step 7 verifies the graph
just built; this step verifies the same graph after real time has
passed - several curation iterations, or any code change
in parallel.
</IMPORTANT>

**Before closing the curation session** (not after each file - at the end of the
work batch, same as Step 5 validates in batches of 15-20):

```bash
python3 build.py --extract    # re-reads the real code, not the cache
```

- [ ] **Orphaned curation is still 0.** If it went up since the last Step 7, something
      in the code changed under an already-curated node - it's not a new build bug,
      it's the signal that those nodes need review, not just silencing the warning.
- [ ] **If you worked in the SAME session where you touched code from the
      graphed subsystem**, run this BEFORE calling the curation done,
      not in the next session - it's the cheapest intervention point,
      same as the DOCER warning arrives in the pull request itself and not
      after merging it.
- [ ] **If the human isn't coming back soon**, leave it noted in
      `curation.yaml` itself or in the closing summary: which subsystem was curated and
      against which commit - so the next session knows whether it needs to repeat
      this step before trusting the graph.

This step doesn't replace Step 7: 7 verifies the new graph is correct;
8 verifies that a graph you already signed off on still is.

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

## Corpus without code (PDFs, Markdown, research JSON)

<IMPORTANT>
The skill's principle (automatable structure + hand-read meaning)
is agnostic to the product type. The extraction layer isn't - a PDF has no
AST. For corpora without source code, `build.py` has a second mode:
`EXTRACT_MODE = 'docs'` instead of `'code'`.
</IMPORTANT>

In `docs` mode, extraction comes from references ALREADY WRITTEN in the corpus,
never inferred by semantic similarity (inferring would mean hallucinating relations -
the same reason Step 5 forbids deriving from the name):

- **Markdown**: one node per file (+ one node per `##` heading if there are several).
  One edge per wikilink `[[id]]` or relative link `[text](other.md)`.
- **Registry JSON** (e.g. a list of sources/citations with `id`): one node per
  entry. One edge per the first list field that declares a relation
  (`relevancia_hueco`, `relacionado_con`, `cita_a`, `refs`).
- **PDF**: one node per file, no internal structure - it's a leaf node to
  curate (`what`/`why`) just like any symbol with no AST of its own.

If the corpus has no explicit references between documents, the graph comes out
with disconnected nodes and zero edges: it still works for CURATION (one card per
document) but doesn't give you blast-radius. That's correct, not a bug - there's nothing
to infer without hallucinating.

Steps 4-7 (curate, flag defects, verify) don't change: `curation.yaml`
still works the same way, just the key is `file.pdf` or
`record.json::N2-047` instead of `file.js::symbol`.

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
