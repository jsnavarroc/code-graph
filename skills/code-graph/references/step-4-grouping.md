# Step 4 — Curate the groups (fast, first)

## Contents

- [Groups before meaning](#groups-before-meaning)
- [Additive only](#additive-only)
- [Declare the groups in meta](#declare-the-groups-in-meta)
- [Cross-cutting symbols](#cross-cutting-symbols)
- [Disambiguate colliding labels](#disambiguate-colliding-labels)
- [Multiple namespaces](#multiple-namespaces)
- [Empty lanes](#empty-lanes)
- [Violations check](#violations-check)

---

## Groups before meaning

Before you write a single description, assign a `layer` (the group number from
Step 1's grouping decision, see step-1-planning.md) to every node. It's cheap —
no reading, just placement — and it gives each node its lane in the viewer so
you can see the shape of the subsystem before you invest in meaning.

<IMPORTANT>
Do groups BEFORE meaning, not after. Grouping after curating produced 112 false
positives in the case that originated this skill: nodes end up in the wrong lane,
the dependency rule reads them as violations, and red stops meaning anything.
Placement first, description second.
</IMPORTANT>

Grouping is mechanical: a node's layer follows from its path/folder against the
grouping criterion the human confirmed. A helper in `atoms/` -> `layer_1`, a
section in `organisms/` -> `layer_3`. You are applying a decision already made,
not making one here.

---

## Additive only

<CRITICAL>
Any tool or script that assigns layers must be ADDITIVE: it may ADD a `layer`
key to a node that doesn't have one, and it must NEVER rewrite the file or touch
a key that already holds hand-written content.

A grouping script that regenerated the whole file erased three already-written
descriptions with no warning. Structure is cheap and recoverable; meaning is
expensive and unrecoverable. The cheap thing must never be allowed to destroy the
expensive thing. If your only safe option is to regenerate the file, stop and add
keys in place instead.
</CRITICAL>

The same additive rule governs curation content (see step-5-curation.md) — layers
are structure, descriptions are meaning, and the write path for structure must be
incapable of overwriting meaning.

---

## Declare the groups in meta

The lanes only get drawn if the `meta` block declares them. Give each group its
number and a one-line name so the viewer knows what each lane is:

```yaml
meta:
  layer_1: Atoms - dependency-free building blocks
  layer_2: Molecules - composition of atoms
  layer_3: Organisms - complete sections
```

The order of the numbers is the top-to-bottom order in the viewer, and — if there's
a dependency rule (step-1-planning.md) — the direction healthy dependencies flow.

---

## Cross-cutting symbols

<IMPORTANT>
If a file is cross-cutting (group 0), its symbols are cross-cutting too.

Curating the file as group 0 but leaving its exported symbols in some other group
breaks the exemption through the back door: edges point to the SYMBOL, not the
file. A logging helper's file may be exempt, but if `log()` still lives in
`layer_2`, every consumer of `log()` reads as an upward edge into `layer_2` and the
violation detector fires anyway. Move the file AND its symbols to group 0 together.
</IMPORTANT>

---

## Disambiguate colliding labels

Run a count over node labels. If two or more nodes share the same label, they are
indistinguishable in the viewer — the human sees two identical dots and cannot tell
which is which. Colliding labels MUST be disambiguated.

The skill requires disambiguating; it does NOT prescribe how, because what tells two
nodes apart depends on the corpus. Use whatever separates them IN THIS corpus:

| Corpus | What collides | Disambiguate with |
|---|---|---|
| code | `index.js` everywhere | the parent folder -> `auth/index.js` vs `forms/index.js` |
| docs (papers) | two papers, same short title | the year or the author |
| docs (citations) | repeated citation titles | the record id |

<IMPORTANT>
This is a guaranteed presentation defect, not an edge case. The `package.json`
`main: index.js` convention alone produces dozens of `index.js` in any modern JS
project. A real graph had ~20 nodes all labeled `index.js` — unreadable until each
was prefixed with its parent folder. And it is NOT specific to code: any corpus with
repeated titles (two papers sharing a name, a citation JSON with recurring headers)
hits the same wall. Count labels, find the collisions, prefix them with the corpus's
own distinguishing signal.
</IMPORTANT>

---

## Multiple namespaces

<CRITICAL>
If the corpus mixes distinct NAMESPACES under one grouping criterion — some lanes
are literature categories, others are your own findings, others are open questions,
any case where "number 6" means a different thing depending on which lane it's in —
do NOT number the lanes in a single sequence `layer_1..layer_N`.

A loose number can't say which namespace it belongs to: `6` is ambiguous the moment
two different kinds of "6" exist. Put an explicit, readable prefix per namespace in
the lane NAME, not in the number — e.g. `lit_6` vs `finding_6` vs `question_6`. The
human decides the prefixes back in Step 1 (step-1-planning.md); you apply them here.
</CRITICAL>

---

## Empty lanes

<IMPORTANT>
A declared lane with no nodes is NOT an error to clean up.

If a group ends up empty — its only node was removed as noise, say — leave it
declared in `meta` with a short note on why it's empty and since when:

```yaml
meta:
  layer_4: Templates - EMPTY since extraction: sole node was a generated file, excluded as noise
```

An empty lane with a note is honest information about an open gap in the subsystem.
Deleting it hides the gap and makes the graph claim a completeness it doesn't have.
</IMPORTANT>

---

## Violations check

If `CHECK_LAYER_VIOLATIONS` is enabled, run the build and look at the violations it
reports.

- A handful -> read each one; they may be real architecture problems worth surfacing.
- Dozens -> almost certainly infrastructure that wasn't marked cross-cutting. A
  logging or config helper left in a numbered layer generates one violation per
  consumer, and there are hundreds of consumers. Go back to Step 1's cross-cutting
  question (step-1-planning.md, group 0) before you touch anything else — the fix is
  in the grouping, not in the edges.
