# Step 7 — Verify and ship

Verify is not "the build didn't crash." A green build with an empty graph, a
viewer that throws no error while showing another project's story, a graph
with no edges drawn — all of these PASS every automated check and are still
broken. This step has three passes, in this order: the data, what's seen, the
human. None of them substitutes for the next.

## Contents

- [Regenerate clean first](#regenerate-clean-first)
- [7a — The data](#7a--the-data)
- [7b — What's seen](#7b--whats-seen)
- [7c — The human](#7c--the-human)

---

## Regenerate clean first

Before verifying anything, regenerate from the current source of truth. Don't
inspect a stale artifact.

```bash
python3 build.py --extract
```

If the viewer was hand-assembled instead of generated, re-assemble it from the
current JSON — not from an older copy someone edited by hand. What you verify
must be exactly what shipping would produce, or the verification is about a
different file than the one that ships.

<IMPORTANT>
Every fix you make in this step goes in the SOURCE — the JSON, the curation,
the TEMPLATE — never in the generated HTML. The next `--extract` overwrites the
generated file. A fix in the output is a fix that disappears.
</IMPORTANT>

---

## 7a — The data

The data pass checks that the graph is internally complete and honest. Run it
against the freshly regenerated build.

- [ ] Orphaned curation: 0 (curation pointing at a node that no longer exists)
- [ ] Nodes with no description of their own: **0 by the time Step 7 closes**
- [ ] Violations (if enabled): each one is real signal, or an unmarked cross-cutting node? (see step-1-planning.md, group 0)
- [ ] Dropped edges: if the build warns it dropped any, why?

<CRITICAL>
"Nodes without description: N, just report the number" is NOT an acceptable
outcome — it's a half-checked box. An uncurated node is pending work, and
"decide later" means it stays invisible forever. Curating it is the default.

YOU don't unilaterally decide a node is "uncurable" and drop it from the graph
— that's a SCOPE decision, and scope belongs to the human (see
step-1-planning.md). If you're unsure whether nodes are curable, or there are
many of the same type, ask the human in closed format:
  a) curate them one by one
  b) exclude with a stated reason
  c) merge, if it's the same concept as another node already curated
Never a fourth silent option where they just stay blank.
</CRITICAL>

**Dropped edges are worse than they look.** A silent drop makes an incomplete
graph look complete: the reader trusts that every relation is drawn, so a
missing edge reads as "these don't connect" rather than "the build gave up on
this one." If the build warns, find out why before shipping — a parse failure,
an unresolved import, a node filtered out from under a live edge. Don't ship a
graph that quietly forgot relations.

**Phantom nodes.** A node pointing at a file that no longer exists on disk must
be **removed, not curated**. The graph must not carry nodes for files that
aren't there — curating a phantom writes a description for something that
doesn't exist, which is worse than leaving it blank.

> Real lesson: two phantom test-file nodes pointed at files that were absent
> from the branch. They passed every count (they had tags, they had positions)
> and had to be dropped, not described.

---

## 7b — What's seen

<CRITICAL>
"The viewer opens and the JS throws no error" PASSES even when the viewer is
broken. Confirmed: it passed clean while the side panel showed ANOTHER
project's narrative, while 10 of 18 lanes were missing, and while the legend
icons stretched until they covered their own text. No data check catches a
presentation failure — a graph can be complete and correct in JSON and still
render as something unusable or wrong.

So: actually open the viewer and go through EVERY surface below with your own
eyes. Don't infer from the data that the render is fine.
</CRITICAL>

- [ ] **THE EDGES ARE DRAWN.** A graph whose relations only appear as side-panel text ("uses / used-by") is a TABLE, not a graph. The lines between nodes are the whole point. If the render can't draw edges, it isn't done.
- [ ] **SEARCH BOX** if there are more than ~30 nodes. Without it the viewer is unusable at scale (the reference case has ~900 nodes; at 67 it was already impossible to find a node by scrolling).
- [ ] **PER-LAYER and PER-EDGE-TYPE FILTERS** when the graph has several layers or relation types — so the reader can isolate one lane (hide the UI layer to see only the core) or one edge kind (only calls, without the imports noise).
- [ ] **GENERIC/COLLIDING LABELS disambiguated** in the display (e.g. `index.js` shown as `parent-folder/index.js`) — see step-4-grouping.md.
- [ ] **Nothing domain-specific hardcoded in the template.** Every visible label comes from the meta block. Fossilized text from another project must move to meta.
- [ ] **The vocabulary is THIS project's.** If grouped by domain, the viewer can't say "layer" — see step-4-grouping.md.
- [ ] **Declared lanes == drawn lanes.** Count them. 18 declared and 8 drawn is a failure, even if nothing threw.
- [ ] **Only what this graph actually uses is shown** — no "violation" legend without a dependency rule; no defect filter without flagged defects.
- [ ] **No loose element-level CSS selector** (`svg{}`, `div{}`, `circle{}`). A global rule for the canvas also hits inline icons and deforms them — CSS wins over `width`/`height` attributes. Scope every rule with an id or class.
- [ ] **Nothing overflows its box** with the project's REAL (longer) text, not the short placeholder text.

**Real lessons behind these boxes:**

> The generated viewer showed cards in lanes with no lines between them. The
> human opened it and said immediately: "it has no edges showing how it
> connects." Every relation was there in the JSON and in the side panel — none
> of it was drawn on the canvas.

> A single unscoped `svg { width: 100% }` in the template stretched the inline
> legend icons until each one covered its own label text. It threw no error;
> the data was perfect; the legend was unreadable.

<IMPORTANT>
Fix every one of these in the TEMPLATE, not in the generated HTML. The build
overwrites the generated file on the next `--extract`, and a template that
still has the bug will re-emit it. If you fixed the output and it "looks right,"
you haven't fixed anything that survives a rebuild.
</IMPORTANT>

---

## 7c — The human

Open the viewer and pass the ball. The human validates the result — not the
numbers, the result on the screen.

Ask about what they SEE, not about counts:
- "Open it. Do the edges show how things connect, or does it look like loose cards?"
- "Is anything on screen worded in a way that isn't how your team talks about this?"
- "Can you find a specific node fast, or do you have to scroll?"
- "Does any label spill out of its box, or overlap something?"

<CRITICAL>
In the case that originated this section, ALL THREE visual failures — the
missing edges, the missing lanes, the stretched legend icons — were found by
the human looking at the screen AFTER every automated check came back green.
The data pass and the "it opens without error" check both passed. The human's
eyes were the only thing that caught them.

Automated green is necessary and not sufficient. The graph ships when the human
who asked for it looks at it and confirms it shows THEIR subsystem, correctly,
legibly — not when the checklist is complete.
</CRITICAL>

Once the human signs off, the graph is done. From here it's upkeep as the code
changes — see step-8-maintain.md.
