# Corpus without code (PDFs, Markdown, research JSON)

Reference for `docs` mode — see [step-2-extract.md](step-2-extract.md) for when to choose it.


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

