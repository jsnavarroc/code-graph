# Step 5 — Curating the meaning

Curating = reading the whole unit and writing what it means. It's the half of the
graph the AST can't provide, and the one that determines whether the graph saves context
or wastes it.

---

## The rule that governs everything

<CRITICAL>
If you haven't read the whole unit, the node stays undescribed.

Deriving from the name produces text that LOOKS like documentation and says nothing:
  `setIsLoading` -> "Writes is loading to state"   ← useless
That's repeating the name with more words. It pollutes the graph and gives a false
sense of coverage.
</CRITICAL>

---

## The fields

| Field | Answers | Does it come from the AST? |
|---|---|---|
| `character` | What TYPE of thing it is | No |
| `what` | What it does, concretely | No |
| `why` | What problem it solves ← **the most valuable** | Never |
| `ux` | What whoever uses it sees or feels | Never |
| `when` | When it runs, who triggers it | Partial |
| `if_broken` | What breaks if it fails | No |

Also: `protected`, `gotchas`, `issue`, `cases` (see "The other fields" below) —
they aren't part of the main set but are curated with the same rule.

<CRITICAL>
This table is the DEFAULT set, not a closed catalog. `what`/`why` cover
most cases, but not every project needs the same thing — a
subsystem with regulatory compliance requirements may need a field
that records which rule each piece exists under; one with physical constraints
(hardware, memory, real-time) may need one that records the exact
limit the decision imposes. Before curating the first node, ask the
human whether the default set is enough or something's missing — don't decide it alone
or assume what/why is always enough.
</CRITICAL>

**Question (closed format, before the first node — same pattern as the
`why` question):**
> "I'm going to curate each node with `character`, `what`, `why`, `ux`, `when`,
> `if_broken` (plus `protected`/`gotchas`/`issue`/`cases` when applicable).
> Does this set cover what this subsystem needs, or is something specific to
> your domain missing? Examples of why something might be missing:
>   a) **Compliance/regulation** — the node exists because of an auditable
>      external standard or requirement (e.g.: 'under which article or policy this exists')
>   b) **Physical or platform constraint** — a numeric or
>      environment limit that `why` doesn't capture well as prose (e.g.: 'the exact
>      memory/latency/hardware limit this respects')
>   c) **Ownership** — who's responsible for this node when it changes,
>      if it isn't obvious from the repository (e.g.: 'which team maintains it')
>   d) **None, the default set is enough** — the most common case
> If you pick (a), (b), or (c), tell me the new field's name and I'll add it to
> this document's table for the rest of the curation — don't define it node by
> node, decide it once at the start."

If the human has no preference, go with the default set — **(d)** is
the most common option and the only one with no added cost. Don't force new
fields without the human asking for them.

---

## `character` — what type of thing it is

<IMPORTANT>
Character determines the artifact's usage RULES. It's not decoration: each type
of thing (a singleton, an immutable object, a component with a lifecycle,
a stateless process...) carries its own constraints on how it's
instantiated, called, or combined with others.

If the graph doesn't say so, whoever consults it has to open the unit to know
how to use the thing — exactly what the graph should be saving them from.
</IMPORTANT>

**The vocabulary comes from the project, not a catalog.** The name THIS
project/domain uses for an artifact type may not match the generic
name you know. Read the unit (file, function, section, whatever the node is
in this product) and say what it IS in the vocabulary the product itself
uses; if you don't recognize the term, look it up; if it's still unclear,
ask the human.

<IMPORTANT>
Search the web BEFORE asking the human, not instead of reading the whole
unit. Same principle as Step 1.2 (grouping): your prior knowledge
of the domain has gaps, and a quick search against the ecosystem's authoritative
source (the framework, the standard, the field's convention) avoids
guessing `character` wrong or forcing a generic `why`. Useful when:
- You half-recognize a pattern but can't place the exact name its
  ecosystem uses for it — search for the official terminology before inventing your
  own approximate term.
- The unit belongs to an ecosystem with its own technical vocabulary —
  confirm the EXACT term that community uses, not a synonym.
- A number, constant, or "storied" threshold (see "What to look for
  while reading" section below) might match a known, documented limit of the
  environment where this unit runs/lives — searching confirms whether it's a
  decision of the project's own or an inherited external limit, which changes
  the `why` that should be written completely.

The search query is built from what you ALREADY saw in the real node you're
curating (the exact term, the name of the framework/standard the project itself
declares, the exact number) — never from an example from another project.

**The search informs, it doesn't replace reading.** If the search contradicts what
the unit actually does (the project uses the pattern "its own way"), what's
there wins — same as in Step 1.2, what's local overrides what's published. And if
after searching it's still unclear, ask the human instead of guessing: a
closed question with what you found ("I see this uses <detected pattern>,
according to <source> it means <X> — is that the case here, or is it used differently?") costs less
than a badly curated description that has to be undone later.
</IMPORTANT>

---

## `why` has no fixed format — ask the human WHAT the criterion is before curating the first node

<CRITICAL>
"What problem it solves" doesn't mean the same thing in every project or for
every team. A generic `why` ("manages state", "processes the
request") is as useless as deriving it from the name — it's the same tautology
of the rule that governs everything, just longer. Before writing the first
`why` in the subsystem, ask the human under what criterion they want it
defined, with concrete options and an example for each — don't ask them
to define it from scratch.
</CRITICAL>

**Question (closed format, with examples — never an open "how do you want
the why?"):**
> "For each node's `why`, which of these criteria do you prefer? I can
> combine more than one if applicable:
>   a) **Design decision** — why it was built this way and not another
>      (e.g.: 'uses X instead of Y because Z fails under this condition')
>   b) **External constraint** — an environment/platform limit that forced
>      this solution (e.g.: '<the environment>'s limit forces this workaround')
>   c) **History/incident** — born from a real problem that happened before
>      (e.g.: 'added after the case where <what failed>')
>   d) **Consequence if it fails** — what breaks in practice if this stops
>      working (e.g.: 'without this, <the observable effect for whoever uses it>')
> Which one(s) do you want me to prioritize, or is there another criterion your team uses?"

If the human has no clear preference, offer **(d) consequence if it
fails** as the most obvious default — it's the easiest to verify (you can
test it by breaking the unit and observing what happens) and yields the most
for someone arriving at the subsystem with no context.

Once the human sets the criterion, every `why` you write must be
verifiable against THAT criterion — not an ambiguous mix of the four with no
clarity on which is being applied to each node.

**Example format (the names are illustrative, replace them with the
real ones from the project you're curating):**
```yaml
module/SingletonClass.ext:
  character: singleton
module/utils/reactiveFunction.ext:
  character: <real type per the project's ecosystem>
module/state/derivedValue.ext:
  character: <real type per the project's ecosystem>
platform/NativeComponent.ext:
  character: <real type per the project's ecosystem>
```

**Write it specifically.** "function" adds nothing — it's visible in the label. "pure
stateless, reusable function" does: it says how it can be used.

<CRITICAL>
Character is NEVER inherited. Each symbol declares its own or goes without.

A helper logging function living inside a file that exports a singleton
class does NOT inherit "singleton" just from living there — that would be a lie. If it's
a function, it's a function.

The difference with the other fields: inherited `what` gives CONTEXT ("this lives
in the module that does X"), which is a fact. Inherited character ASSERTS
the thing is something it isn't. One situates, the other lies.

Only exception: when file and symbol are collapsed. There it's not
inheritance but fusion — they're the same thing, they share character by definition.
</CRITICAL>

**Watch for redundancy:** if the project groups BY artifact type (one
folder per component type), `character` and the group say almost the
same thing. There, character must add the nuance the group doesn't give: it's not
enough to repeat the type, you have to state the specific usage constraint (e.g. "only
valid within X context").

**And character decides the collapse:** a file with ONE character (a single
exported entity) collapses with its homonymous symbol. A file with TWO APIs
of different character (e.g. a class AND an independent function, with
different consumers) are separate nodes.

`why` and `ux` are what justify the work. `what` without `why` is a
glorified comment.

**`ux` decides whether a change is worth it.** Write it in terms of what
whoever uses the final product experiences, not code/implementation. If the
node has no directly observable effect, say so: "Invisible: it's
internal infrastructure. If it fails, <the indirect effect that IS noticed>."

---

## What a good description looks like

**Bad** (deduced, without reading):
> "Validation and flow-advance logic."

**Good** (after reading the whole unit):
> **what**: Governs advancing a multi-step form. Distributes focus
> across fields, opens the corresponding input exactly once per visit,
> validates on confirm.
>
> **why**: This flow has TWO layers of state that must coordinate: the
> container receives the interaction first, and only then is the internal
> field enabled. This function coordinates those two layers, and that's where its two
> guards come from. One of them prevents the field from re-activating more than once per
> visit: without it, every time focus returned to the container —for example
> when coming back from a go-back action— the field would activate again on top
> of the user without them asking for it.
>
> **ux**: The user reaches the field and it activates on its own, once. Coming back
> from another screen, it doesn't activate again without them asking for it.

The difference: the second one explains **why it's this way and not another**.
That isn't found anywhere except in the unit itself.

---

## What to look for while reading

What makes a node valuable is almost always one of these five:

1. **Numbers with a story.** A timeout, a retry limit, a specific
   threshold. They're never arbitrary: someone tuned them fighting a
   real problem. Find out against what.
   > "60 retries versus the default 10: the system's longest
   > flow chains four consecutive waits, and with 10 the limit ran out
   > before the operation finished."

2. **Guards that look defensive and aren't.**
   > "The three conditions are MANDATORY, not redundant: the event that
   > triggers this is a general broadcast (it reaches every listener),
   > so without the condition that filters by identity, any listener
   > would process the event even if it didn't apply to it."

3. **Commented-out or emptied code.** It's a finding, not junk. Someone turned it
   off for a reason and that reason usually explains a weird behavior seen today.

4. **Author comments.** When the code explains its own why, that's
   the best source there is. Quote it.

5. **Platform/environment differences.** They almost always hide a
   real limit of the environment it runs in, not an oversight.

---

## The other fields

**`protected`** — the node isn't touched without coordinating (e.g.: reference to a
ticket/PR explaining why it's frozen).

**`gotchas`** — what breaks if you touch it wrong. One per line, concrete.
If you detect duplicated logic, say so here with the places it's found:
> "DUPLICATED: the same state check is implemented in three
> different places, each with a different wait time (100ms, 250ms,
> immediate). A fix in one does NOT reach the other two."

**`issue`** — `bug` | `dead` | `duplicate`. By hand, reading the node. See Step 6.

**`cases`** — documented cases that touch this node.

---

## File -> symbol inheritance

The symbol homonymous with its file (the main function/class the file
exports as `export default` or equivalent) inherits its curation: curating both
would duplicate.

The file's other symbols do NOT inherit their own `what` — they show the module's
context, which is a verified fact, not an invention.

<IMPORTANT>
When counting coverage, inheritance != own description. Counting them together reports
100% when half the work is missing. Real case: a counter reported 100%
coverage while 547 nodes (more than half the subsystem) only had
the file's inherited context, with no `what` of their own.
</IMPORTANT>

---

## The pace

Unit by unit, starting with the highest-impact ones (highest `in_degree`, or highest
centrality if the graph computes it).

<IMPORTANT>
Centrality is the starting point, not the final ranking. A very
central file with no recent development activity may weigh less than one
with medium centrality that was touched last week — a real industry study
(3 products, 10 practitioners) found that professionals ALWAYS
combined the structural signal with context (recent activity,
architectural role) before deciding; they never treated centrality as an
automatic answer. If you have access to the repo's history (`git log
--since` on the subsystem's files), use it to adjust the order `in_degree`
proposes — and it remains a PROPOSAL to confirm with the human,
not a decision you make alone.
</IMPORTANT>

**Before curating the first node of each 15-20 batch, review the whole
batch's list once** (what each one does, in one sentence) before
starting to write the first one's curation. This isn't redundant: processing a
long list in sequential order biases toward curating the first items on the
list better and the last ones worse — the same effect is documented in
language models processing long lists, and it's mitigated (not fully
eliminated) by explicitly asking to consider all options before deciding. This
prior review is that mitigation.

Every 15-20 units:

1. `python3 build.py`
2. Fix orphaned curation if there is any
3. Show the human 2-3 descriptions and ask if the level is right

That last step is what saves the work. Detecting late that the curation
criterion has gotten loose (halfway through a large subsystem) costs hours of
retroactive correction; detecting it in the first 20-50 units costs
minutes.
