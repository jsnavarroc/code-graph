# Step 8 — Maintain: re-verify before closing (if time passed or code changed)

## Contents

- [Why this step exists](#why-this-step-exists)
- [When to run it](#when-to-run-it)
- [The checklist](#the-checklist)
- [Step 8 is not Step 7](#step-8-is-not-step-7)
- [Platform / scope drift](#platform--scope-drift)

---

## Why this step exists

<IMPORTANT>
The graph doesn't decay with age — it decays because the code underneath keeps
moving while you curate. A study of 1000 GitHub repositories found more than a
quarter (28.9%) had documentation with at least one reference to code that no
longer existed, and the confirmed pattern is that the same commit that changes
the code is the one that leaves the documentation lying — with no warning until
something explicitly reviews it (Tan, Wagner & Treude, 2023, "Wait, wasn't that
code here before?").

Step 7 verifies the graph you just built (see step-7-verify.md). This step
verifies the SAME graph after real time has passed — several curation
iterations, or any parallel code change.
</IMPORTANT>

---

## When to run it

BEFORE closing the curation session -> not after each file, but at the end of
the work batch, once, as the last thing before you sign off.

```bash
python3 build.py --extract
```

`--extract` re-reads the real code from disk, not the cache. That's the whole
point: you're asking whether the ground the curation stands on has moved since
you last looked.

---

## The checklist

- [ ] **Orphaned curation is still 0.** If it went up since the last Step 7,
      something in the code changed under an already-curated node. That is NOT a
      new build bug — it's the signal those nodes need review. Fixing the count
      by deleting the orphaned key silences the warning without answering it;
      re-read the node instead.

- [ ] **THE HARD ONE — a file that still EXISTS may have changed underneath a
      correct curation.** The orphan check only catches a key pointing at a
      MISSING file. It does NOT catch a file that still exists but was rewritten.
      Record the commit or hash each node was curated against (in Step 5, see
      step-5-curation.md), and here re-verify that files whose hash/mtime changed
      since curation still match their `what`/`why`.

      Real lesson: mid-session a checkout swapped the working tree, and a storage
      module was still curated as "the fix that routes X to secure storage" while
      the file on disk had reverted to the old behavior. The curation was lying
      with confidence and the orphan check stayed GREEN — because the file still
      existed. In a repo with frequent checkouts this re-check is not optional.

- [ ] **Same session where you touched graphed code -> run this BEFORE calling
      the curation done.** Not next session. It's the cheapest intervention
      point — the same logic as a warning that arrives in the pull request
      itself, not after merging. The cost of catching a stale node grows the
      further you get from the change that caused it.

- [ ] **Human isn't coming back soon -> leave it noted.** In the curation file or
      the closing summary, record which subsystem was curated and against which
      commit. So the next session knows whether it must repeat this step before
      trusting the graph, instead of assuming a green board it never re-earned.

---

## Step 8 is not Step 7

<CRITICAL>
This step does NOT replace Step 7 (see step-7-verify.md).

- Step 7 verifies the NEW graph is correct — the one you just built.
- Step 8 verifies that a graph you ALREADY signed off on STILL is.

Different question, different moment. A clean Step 7 says nothing about whether
the tree moved afterward; only Step 8 asks that. Running one is not running the
other.
</CRITICAL>

---

## Platform / scope drift

If the graph was scoped to one platform or environment (see step-1-planning.md
and step-4-grouping.md), a later extraction may pull in newly-added files from
the OTHER platform that didn't exist when you first scoped the seeds.

Re-check that the other platform's nodes haven't crept back into the graph. Scope
is a decision made once at planning time; extraction re-applies it against
today's file tree, and today's tree can contain files the original scope never
saw. Confirm the boundary still holds.
