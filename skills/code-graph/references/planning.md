# Step 1 — Planning the graph (with the human)

This step prevents redoing work. The answers come from the human; you explore the
code and **suggest**. Never decide for them: a badly grouped graph lies on every
query, and the 112 false violations from the original case came from right here.

Five written answers come out of this that feed into build.py's CONFIG.

---

## 1. What is the subsystem and what are its seeds?

A graph of everything is useless: it's the hairball nobody reads. A graph of a
subsystem with its blast-radius is.

**Question:**
> "What subsystem do you want to understand? What folders or paths make it up?"

**Criterion:** a seed is code that IS the subsystem, not something that uses it.
If unsure: *would this file exist if the subsystem didn't?* If not -> neighbor.

Neighbors are NOT declared: the script pulls them following the edges. That's
the blast-radius, and it's half the value of the graph.

**Warning sign:** more than ~1500 nodes = scope set wrong. Reduce the seeds.

---

## 2. How are nodes grouped? ← EXPLORE AND SUGGEST

<CRITICAL>
DO NOT assume the project is organized in dependency layers. It's ONE form
among many. Explore the real structure and suggest what you see.
</CRITICAL>

It's three moves: **read the project → contrast with what's published →
suggest**. In that order.

### 2.1 Read the real structure

```bash
# Folder shape usually gives away how the team thinks
find <src> -maxdepth 3 -type d -not -path "*/node_modules/*" | head -40

# Imports tell the truth when folders lie:
# what gets imported most, and from where?
grep -rhoE "from ['\"][@.][^'\"]+" <src> --include="*.js" 2>/dev/null \
  | sed "s/from ['\"]//" | cut -d/ -f1-2 | sort | uniq -c | sort -rn | head -15
```

Also look at what the project itself declares: `README`, `CONTRIBUTING`, architecture
docs, a `CLAUDE.md`. Sometimes the grouping is already written down.

<IMPORTANT>
Folders can lie. A project may have `components/ hooks/ utils/`
out of generator inertia and actually be organized by feature. Contrast what
the folders say with what the imports say.
</IMPORTANT>

### 2.2 Contrast with what's published (web search)

<IMPORTANT>
Don't rely solely on your memory of architectures: there are conventions you don't know,
and others that changed. Search before suggesting.
</IMPORTANT>

Useful when:
- **You half-recognize the pattern** — search for its official naming and its
  canonical groups. That Atomic Design has `templates` and `pages` besides the first
  three isn't guessed: it's checked.
- **You recognize nothing** — search by the stack: *"<framework> project structure
  conventions"*, *"<framework> architecture layers"*. It might be a
  standard ecosystem pattern.
- **The pattern has declared dependency rules** — many architectures
  publish them (hexagonal, clean, feature-sliced). That feeds directly into step 3.
- **The project uses an opinionated framework** — Next.js, NestJS, Django,
  Rails come with their own structure. Confirm the version, they change.

Search examples:
```
"feature-sliced design" layers segments        <- if you see app/ pages/ widgets/
"hexagonal architecture" dependency rule       <- if you see domain/ application/
"nestjs" module structure conventions          <- if the framework has an opinion
"atomic design" pages templates organisms      <- to confirm the canonical groups
```

**Correlate the two sources.** What's local overrides: if the project says it uses
Atomic Design but has no `templates/`, the graph groups what's THERE, not what
the canonical pattern says should be there. The search is for naming things well and
not missing groups, not for imposing a mold.

### 2.3 Suggest, with what you found

**Question:**
> "I see <local structure>. It resembles <pattern>, which according to <source>
> organizes into <groups>. Should we group it this way, another way, or not
> group at all?"

Frequent patterns, as a starting point —**not as a closed catalog**:

| If you see... | It might be | Does it have direction? |
|---|---|---|
| `atoms/ molecules/ organisms/` | Atomic Design | No: composition |
| `domain/ application/ infrastructure/` | Hexagonal / Clean | Yes |
| `app/ pages/ widgets/ features/ entities/ shared/` | Feature-Sliced Design | Yes |
| `features/auth/ features/cart/` | Domain modular | Sometimes |
| `components/ hooks/ services/ utils/` | Artifact type | No |
| `controllers/ resolvers/ subscribers/` | Interface type (REST/GraphQL) | No: parallel |
| `encoders/ decoders/ codecs/` | Symmetric pairs | No |
| Native + state + UI | Dependency layers | Yes |
| Nothing clear | Maybe no grouping is worth it | — |

**Not grouping is legitimate.** If the project has no clear structure, putting all
nodes in one lane and using the graph only for blast-radius is better than
inventing a false grouping. Forcing layers where there are none is worse than not
having them.

**The grouping defines each node's vertical position in the viewer.** Number
the groups in the order you want them seen top to bottom.

---

## 3. Is there a dependency rule to watch? (OPTIONAL)

<IMPORTANT>
Grouping and watching dependencies are TWO DIFFERENT THINGS. Don't mix them.

Atomic Design groups by composition, not by dependency: an atom doesn't "use" a
molecule, the molecule is composed of atoms. Applying a violation detector to it
produces alarms that mean nothing.
</IMPORTANT>

**Question:**
> "Is there a rule of what can use what that you'd want to watch?"

Examples of real rules:
- *"The UI doesn't import from infrastructure directly"* (hexagonal)
- *"Organisms don't import from other organisms"* (atomic)
- *"No feature imports from another feature"* (modular)
- *"The navigation component doesn't depend on content"* (common UI rule)

**If there's a rule:** number the groups so that HEALTHY dependencies go down
(4 uses 3, 3 uses 2). That way what goes up is a detectable violation.

**If there's no rule:** leave `CHECK_LAYER_VIOLATIONS = False` in the CONFIG. The graph
is still useful for blast-radius and comprehension; it just doesn't flag anything in
red. That's normal in groupings by composition or by feature.

**If the human doesn't know:** don't invent one. No rule is better than a
false rule — an invented rule generates alarms that train the team to ignore
red.

---

## 4. What's cross-cutting? (group 0) ← THE MOST IMPORTANT ONE

Only applies if there's a dependency rule (step 3). Skipping it produced **112
violations, all 112 false**.

**Question:**
> "What utilities does everyone use that belong to no group?"

**The test:** would the highest-level group using this be an architecture
problem? If the answer is no, it's cross-cutting.

Almost always: logging, config, authentication, formatting helpers, contexts that
only share refs, constants.

**Typical examples:** a logging helper (with hundreds of consumers — it's not a
layer, it's plumbing), global configuration, authentication, formatting utilities,
contexts that only share references.

**Why it matters so much:** a graph screaming 112 false alarms trains the
user to ignore red. With 12 real ones, red means something again.

---

## 4b. How are edges connected when there's ambiguity? (`docs` mode ONLY)

<IMPORTANT>
In `code` mode this isn't asked: the edge comes from the AST (calls/imports), there's no
ambiguity to decide. This question applies ONLY when `EXTRACT_MODE = 'docs'`
(corpus without source code — see SKILL.md, "Corpus without code" section).
</IMPORTANT>

A corpus of documents has no AST that says "this calls that." The
connection comes from what the corpus ALREADY declares in writing (wikilinks, relation
fields in JSON). When that signal isn't there, or there's more than one reasonable way to
read it, don't decide alone — **suggest the most obvious reading and ask**.

<IMPORTANT>
Before formulating the proposal, search the web — same as in step 2.2
(code grouping). If the corpus is from a domain with its own linking/citation
conventions (e.g. Zettelkasten, PRISMA, an academic citation format,
a metadata schema known as Dublin Core or schema.org), those
conventions already resolve "which field is the relation" better than guessing it just
by looking at field names. Search examples:
```
"<field name seen>" metadata schema standard   <- if a field has an odd name
"zettelkasten" linking convention                       <- if you see linked-note-style ids
"PRISMA" systematic review citation graph                <- if the corpus is academic literature
"<citation format seen>" citation graph field           <- if there's a doi/cita_a-type field
```
Same as in 2.2: what's local overrides. If the search suggests a field the corpus
does NOT have, don't invent it — use it only to better name the relation that IS
there, or to not miss an equivalent field with a different name (e.g. "refs"
vs "bibliography" vs "see_also"). The search improves the proposal you
present to the human; it doesn't replace the human's confirmation.
</IMPORTANT>

<IMPORTANT>
Phrase the question as ACCEPT/REJECT a concrete proposal with real
examples from the corpus — never as an open "how do you want us to connect
this?" An open question forces the human to design the solution; a closed
question with the suggestion already written only asks for a verdict. This is
validated: in a real study (2 industry scenarios, Watkiss-Leek et al. 2026,
"IDEA2"), separating "who proposes" (the agent) from "who validates" (the human)
with a binary decision + optional comment achieved 92-95% first-pass
acceptance, at a cost of ~1 minute per decision when the proposal
was already anchored in the corpus's real structure (not free-form invented text).
</IMPORTANT>

**Question format (three effort levels, in this order — never skip to 3):**

1. **Binary decision with a concrete example** (mandatory, the only one the human
   MUST answer):
   > "I propose connecting by <field/signal found>. Real example: `<node A>`
   > would connect to `<node B>` because both <reason with the exact value seen,
   > e.g. 'share relevancia_hueco: H6'>. Do you accept this rule for the whole
   > corpus? (yes / no)"

2. **Choosing among already-generated alternatives** (only if there's more than one
   candidate signal — never draft the alternative, offer it already formulated):
   > "If not: the corpus also has these fields that could be the connection.
   > Which do you prefer?
   >   a) `cita_a` — connects who cites whom (directional)
   >   b) `relevancia_hueco` — connects who holds the same argument (non-directional)
   >   c) none — leave the nodes disconnected, the corpus has no reliable signal"

3. **Free comment** (optional, only if I rejected the proposal and no
   alternative on the list works): ask for a short sentence, never a long
   write-up — "in one sentence, what WOULD connect these nodes for you?"

**Typical cases and the concrete proposal to offer at level 1 (never apply without the human's "yes"):**

| What you see in the corpus | Proposal to put in the level-1 question |
|---|---|
| Wikilinks `[[id]]` or relative links `[text](other.md)` | "Connect each wikilink/link with the document it references" — this usually gets accepted directly, it's the least ambiguous signal |
| A list-type field like `relevancia_hueco: [H1, H6]`, `cita_a: [...]`, `refs: [...]` | "Connect entries that share the same value in `<field>`" — with a real example of two entries that meet it, taken from the corpus itself |
| Only free prose, no fields or links | There's no level-1 proposal to honestly offer. Skip straight to saying so: "I find no written connection signal — the graph will come out with disconnected nodes, it's useful for curation but not for navigation. Would you rather add a relation field to the corpus before continuing, or do we proceed with no edges?" (this is also a closed question, not an open one) |
| Several candidate fields at once | Use level 2 directly: offer each field as an already-formulated option with its own example, don't ask "which would you use?" in the abstract |

**Nodes left with no edge at all after extraction:** don't hide them or force-
connect them. Show them to the human as a separate list ("N documents with no
connection detected") — it's the same logic as a code node with 0 consumers
(a candidate to review, not an error to silently fix, see Step 6 and N1-039).

<CRITICAL>
**Special case: real but external relations (e.g. bibliographic citations via
an API like OpenAlex/Semantic Scholar).** This is NOT the same as "inferring by
semantic similarity" (already forbidden throughout the skill) — the API returns a
relation that really exists: paper A really does cite paper B. But bringing it
in automatically all the same is forbidden, for a different reason: that a citation exists
bibliographically doesn't say whether that citation **matters to the argument**
the corpus is building. A research corpus can cite a source to
agree with it, to contradict it, or in passing in a footnote — the API doesn't
distinguish those three cases, and only the human knows which one serves the goal
of the document being written.

That's why, if you're going to use a bibliographic API as an input:
1. Permitted use: the API feeds the PROPOSAL you bring to the human, it never
   writes the edge directly. There's no shortcut by volume — if the API returns 40
   cross-citations, that's 40 decisions, not one generic rule applied to all 40.
2. The level-1 question (above) changes shape for this case — it's not
   "do you accept this rule for the whole corpus?" (a rule doesn't decide
   argumentative relevance case by case), it's per relation found:
   > "The API says `<source A>` cites `<source B>` (real, verifiable). In
   > the argument you're building, does that citation matter? (yes, I use it as
   > an edge / no, it's bibliographic noise / I use it but with a different meaning: <which>)"
3. Never write the citations file (e.g. `citas_intra_corpus.json` or
   equivalent) entirely from the API's raw output. That file gets
   filled with the relations the human already confirmed, one by one — it's
   curation content, not structure, and follows the same additive rule as
   `curation.yaml` (see SKILL.md, "Why this can't be fully automated"
   section).
</CRITICAL>

---

## 5. What's noise?

**Question:**
> "What files add nothing to understanding the subsystem?"

**By default:** tests, styles, mocks, generated files, snapshots.

**Watch out with tests:** out of the graph because they inflate impact (30 tests make
a symbol look heavily used), but they're a good source for CURATION: a well-
written test tells you what's expected of the function.

**Noise from the AST itself** (confirmed): system types extracted as if they were
your own code (`Bool`, `UIView`), comments left as a node, import
destructurings. The script filters out nodes with no `source_file`, which catches most of it.

---

## Output of this step

Show this to the human and ask for confirmation BEFORE extracting anything:

```
Subsystem   : <name>
Seeds       : <paths>
Grouping    : <what criterion, and why that one>
  group 1   : <name> - <description>
  group 2   : <name> - <description>
  ...
Dep. rule   : <the rule | NONE - violations disabled>
Group 0     : <cross-cutting, if applicable>
Excluded    : <noise>
Edges       : <ONLY docs mode: what field/signal is used to connect, confirmed by the human>
```
