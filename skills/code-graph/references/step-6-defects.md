# Step 6 — Flag defects (by hand, node by node)

The `issue` flag marks a node that has a defect. YOU set it, by reading the node —
not by pattern-matching, not by keyword. It's the same discipline as curation:
if you haven't read the unit, you don't flag it.

## Contents

- [The rule that governs the flag](#the-rule-that-governs-the-flag)
- [The three defect types](#the-three-defect-types)
- [`dead` — start from the build's candidates](#dead--start-from-the-builds-candidates)
- [`duplicate` — search before flagging](#duplicate--search-before-flagging)
- [The flag is not enough: also write it in prose](#the-flag-is-not-enough-also-write-it-in-prose)
- [The viewer only shows the filter when there are defects](#the-viewer-only-shows-the-filter-when-there-are-defects)

---

## The rule that governs the flag

<CRITICAL>
NEVER deduce the `issue` flag by searching for a keyword in the node's text
(`TODO`, `FIXME`, `HACK`, `broken`, `deprecated`). The day someone writes a gotcha
with different words —or fixes the wording without fixing the code— the node
silently drops out of the filter and nobody notices.

The flag is set BY HAND, from reading the node and deciding it has a defect.
A keyword search is a hint about where to look, never the thing that sets the flag.
</CRITICAL>

---

## The three defect types

`issue` takes one of three values. Read the node and decide which applies:

| Type | Meaning |
|---|---|
| `bug` | It's wrong and it's noticeable. The logic produces the wrong result, races another effect, mishandles an edge case — something a user or caller can observe. |
| `dead` | Written but never runs. Commented out, a stub that returns nothing, an export nobody imports, a branch that can't be reached. |
| `duplicate` | The same logic repeated in several places. A fix in one copy does not reach the others. |

One flag per node. If a node is both wrong AND duplicated, pick the one that
matters most for whoever reads the graph and spell out the rest in prose
(see below).

---

## `dead` — start from the build's candidates

Don't scan every node blindly for dead code. The build already computed a
starting list: symbols with **0 consumers across the ENTIRE graph** (not just the
subsystem). That's the same reachability signal automatic dead-code detection uses
— combining static and dynamic analysis reaches ~87.9% accuracy (Malavolta et al.,
2023, "Lacuna", IEEE TSE).

<IMPORTANT>
The candidate list narrows WHERE to look first. It does NOT decide for you.
About ~17.5% of those candidates are real false positives — public exports meant
to be consumed from outside the graph, entry points called by the framework,
symbols reached only through dynamic dispatch. You confirm each one by reading it;
the list only saves you from checking every node.
</IMPORTANT>

Confirm before flagging: is this genuinely unreachable, or is it reached by a path
the AST can't see (a public API, an entry point, a reflective call)? If the latter,
it's not `dead` — leave it unflagged.

---

## `duplicate` — search before flagging

You cannot flag a duplicate you haven't confirmed exists elsewhere. Actually search
for the pattern first:

```bash
grep -rn "<the suspicious pattern>" src/ --include="*.js" | grep -v test
```

If the search returns the same logic in two or more places -> flag `duplicate`.
If it's the only occurrence, it isn't a duplicate, whatever it looked like. Tests
are excluded from the search (`grep -v test`) because the same call appearing in a
test file is expected, not a duplicated implementation.

---

## The flag is not enough: also write it in prose

A colored node tells the viewer "something is wrong here" and nothing more. The
person reading has to open the unit to learn WHAT. Record the defect in the node's
`gotchas` (or `why`) in plain words, so the graph explains the defect instead of
just marking it.

<IMPORTANT>
A node can be curated correctly AND carry a bug — the two are not exclusive.
Example: an async cleanup fired without awaiting it, so it races another effect
that runs on the next interaction. The curation is right about what the node does;
the `why`/`gotchas` names the bug in prose ("the cleanup is not awaited, so on a
fast second interaction it can run after the effect that depends on it"), and the
`issue: bug` flag makes it filterable. Prose explains, flag filters. You need both.
</IMPORTANT>

---

## The viewer only shows the filter when there are defects

The issue filter is offered ONLY when at least one node is actually flagged. Don't
render a "defects" filter on a graph with zero issues — an empty filter reads as
"nothing was checked" or clutters the view with a control that does nothing.

This ties directly into verification: a defects filter that lights up on a graph
you believe is clean is a signal to re-read, and a graph with real flags must carry
the prose to back each one (see step-7-verify.md).
