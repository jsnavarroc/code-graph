#!/usr/bin/env python3
"""Builds a hybrid code graph: subsystem + its blast-radius.

Structure (nodes, edges, impact) = AST via graphify. Ground truth, regenerable.
Meaning (group, what it does, why) = curation.yaml. Hand-written by reading.

Usage:
    python3 build.py --extract   # extracts the AST and builds
    python3 build.py             # rebuilds with the cached AST (~1s)

Configuration: the CONFIG block below. Nothing else is touched per project.

═══════════════════════════════════════════════════════════════════════════════
WHY THIS SCRIPT DOES WHAT IT DOES
Every decision came from a real error building the first graph with it.
═══════════════════════════════════════════════════════════════════════════════

1. GROUPING IS NOT THE SAME AS DEPENDING. They're two independent axes.
   Atomic Design groups by composition (an atom doesn't "use" molecules). REST /
   GraphQL / microservices are parallel categories. Encoder / decoder
   are symmetric pairs. In all those cases there's NO direction to violate, and
   that's why CHECK_LAYER_VIOLATIONS exists: it only activates if the project declared a
   real directional rule (hexagonal, dependency layers).

2. GROUP 0 (CROSS-CUTTING) IS NOT "UNCLASSIFIED".
   It's the infrastructure everyone uses (logging, config, auth, helpers) and
   that belongs to no group. Marking it as one more group produced 112
   false violations out of 112. With the exemption, 12 remained real. A graph that
   screams 112 false alarms trains the user to ignore red.
   And if a file is cross-cutting, SO ARE ITS SYMBOLS: edges point to the
   symbol, not the file. Forgetting that took the violations back up from 12 to 40.

3. THE ORPHANED CURATION WARNING ISN'T DECORATIVE.
   It's what keeps the graph from lying. It catches invented keys: paths that don't
   exist (Button/Button.js when the real one is Button/index.js), helpers curated in
   the wrong file, symbols the AST doesn't extract. Without it, the graph would
   have descriptions pointing at nothing and nobody would know.

4. THE AST DOESN'T SEE EVERYTHING. Confirmed:
   - Re-exports (export const x = otherModule.y).
   - Computed properties (var foo: Bool { ... } in Swift).
   - Some loose exports, with no clear pattern.
   It's the parser's limit, not a bug. That's why curation is written by READING
   the file, never trusting the node list.

5. THE AST ALSO ADDS NOISE. Filtered out:
   - System types extracted as if they were your own code (Bool, UIView...): they come out
     with no source_file.
   - Parser artifacts: comments left as a node, import
     destructurings.

6. NEVER DERIVE DESCRIPTIONS FROM THE NAME.
   Tried and discarded: "setIsNavigating -> writes is navigating to
   global state" is a tautology disguised as documentation. It pollutes the graph
   with noise that looks like knowledge. If a node hasn't been read, it stays
   undescribed.

7. INHERITANCE != OWN DESCRIPTION.
   A symbol may show its file's context, but that isn't describing it.
   Counting them together reported 100% coverage with 547 nodes with no real description.
═══════════════════════════════════════════════════════════════════════════════
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent

# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  CONFIG — the only thing touched per project. Comes out of Step 1 (planning). ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

# 1. CODE ROOT. What gets extracted. EXTRA_ROOTS is for code outside the
#    main root (e.g.: a native iOS SDK next to a JavaScript src/).
#    Each extra: (path, prefix it appears under in the graph).
SRC_ROOT = Path('/absolute/path/to/your/project/src')
EXTRA_ROOTS = [
    # (Path('/path/to/project/ios/App'), 'ios/App'),
]

# 2. SEEDS. A file IS part of the subsystem if its path (relative to SRC_ROOT)
#    matches one of these patterns. NEIGHBORS are not declared: the script pulls
#    them following the edges. That's the blast-radius.
#    Test: would this file exist if the subsystem didn't? If not -> neighbor.
SEEDS = [
    r'^path/to/your/subsystem/',
    r'^another/relevant/path',
]

# 3. NOISE. What never gets in.
#    Tests are excluded because they inflate impact (30 tests make a symbol
#    look heavily used), but they're a good source for CURATION.
EXCLUDE_RE = re.compile(r'__tests__|\.test\.|/package\.json$|\.styles\.js$|/node_modules/'
                        r'|\.stories\.|/__mocks__/|\.snap$')

# 4. DEPENDENCY RULE (optional). Only set this to True if the project HAS
#    a declared directional rule like "group 4 can use group 3, never
#    the other way around." Then an edge that goes up is flagged as a
#    violation.
#
#    Leave it False if you group by composition (Atomic Design: an atom doesn't "use"
#    a molecule), by feature, or by artifact type. In those cases there's no
#    direction to violate, and enabling it produces alarms that mean nothing.
#    The graph still works for blast-radius and comprehension.
CHECK_LAYER_VIOLATIONS = False

# 5. SIZE WARNING. If the graph exceeds this, the scope is wrong: stop and
#    reduce the seeds. A graph that can't be fully curated is useless.
MAX_NODES_WARN = 1500

# ── Real example (the case that originated this skill) ────────────────────────
# SRC_ROOT = Path('/Users/x/project/src')
# EXTRA_ROOTS = [(Path('/Users/x/project/ios/NextPlay'), 'ios/NextPlay')]
# SEEDS = [r'^core/atoms/navbar/', r'^core/TVEventService/',
#          r'^components/content/NavBarTV/', r'^ios/NextPlay/TVRemoteInterceptor']
# -> 934 nodes (667 from the subsystem + 267 neighbors), 3197 edges
# ══════════════════════════════════════════════════════════════════════════════

# 6. EXTRACTION MODE. 'code' uses graphify/tree-sitter (source code AST).
#    'docs' uses a custom extractor for a corpus WITHOUT code: Markdown, citation/
#    registry JSON, and PDFs. There's no AST for a PDF - the "node" is the whole
#    document (metadata as source_file), and "edges" come from EXPLICIT
#    references already written (wikilinks [[id]] in Markdown, or whichever field the
#    JSON itself declares as a relation, e.g. relevancia_hueco). It's the same
#    principle (automatable structure + hand-read meaning), with a
#    different extraction layer because there's no tree-sitter for PDFs.
#    See 'what this skill does NOT cover' in SKILL.md before using 'docs': the
#    reliability of the edges depends on the corpus ALREADY having explicit
#    cross-references (they're not inferred by semantic similarity - that would hallucinate, H-01).
EXTRACT_MODE = 'code'  # 'code' | 'docs'

# Only if EXTRACT_MODE = 'docs': root of the document corpus.
DOCS_ROOT = Path('/absolute/path/to/your/corpus')

# graphify: AST extractor (25 languages, local, no API key).
# Uses the environment's python by default; if you have it in a venv, point here.
GRAPHIFY_PY = Path(sys.executable)

AST_RAW = HERE / 'ast-raw.json'
CURATION = HERE / 'curation.yaml'
OUT = HERE / 'code-graph.json'
TEMPLATE = HERE / 'viewer-template.html'
VIEWER = HERE / 'index.html'

NAV_RE = re.compile('|'.join(SEEDS))

# Symbols that are structural noise: styled-components, constants, presentation
# wrappers. They aren't subsystem logic.
NOISE_SYMBOL_RE = re.compile(
    r'^(styles?|Styled\w*|[A-Z_]{3,}|.*Container|.*Wrapper|.*Text|.*Icon|.*Image)$'
)

# Parser artifacts: comments left as a node and import destructurings
# ("{ handleTestIDChange }"). They aren't symbols, there's nothing to curate.
PARSER_ARTIFACT_RE = re.compile(r'^\{|\s{2,}|^(NOTE|TODO|FIXME|HACK|XXX)[: ]')

IMPACT_TIERS = [(50, 'CRITICAL'), (20, 'HIGH'), (8, 'MEDIUM'), (2, 'LOW')]

# Relations that count as USE and therefore add to degree (= impact).
# The first five are from 'code' mode; 'references' and 'sustains' are from
# 'docs' mode. 'contains' is deliberately left out: it's structural
# containment (file -> heading), same as file -> symbol also doesn't count in 'code'.
# Without the docs ones, ALL nodes in a corpus came out with degree 0 and impact
# LEAF, and the blast-radius axis went mute with no warning. See H-29.
DEGREE_RELATIONS = ('calls', 'imports', 'imports_from', 'method', 'indirect_call',
                    'references', 'sustains')

# Suffixes that identify a FILE node (versus an internal symbol node).
FILE_SUFFIXES = ('.js', '.swift', '.md', '.pdf')


def impact_of(in_degree):
    for threshold, name in IMPACT_TIERS:
        if in_degree >= threshold:
            return name
    return 'LEAF'


def load_curation():
    """Reads curation.yaml with no external dependencies (bounded YAML subset)."""
    if not CURATION.exists():
        return {}, {}
    text = CURATION.read_text(encoding='utf-8')
    entries, meta = {}, {}
    current_key, current_field = None, None
    for raw in text.split('\n'):
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        if raw.startswith('meta:'):
            current_key = '__meta__'
            continue
        # Node key: "  path/to/file.js::symbol:" (2-space indent)
        m = re.match(r'^  ([^\s:][^:]*(?:::[^\s:]+)?):\s*$', raw)
        if m and not raw.startswith('    '):
            current_key = m.group(1).strip()
            entries.setdefault(current_key, {})
            current_field = None
            continue
        # Scalar field: "    field: value"
        m = re.match(r'^    (\w+):\s*(.*)$', raw)
        if m and current_key:
            field, value = m.group(1), m.group(2).strip()
            if value:
                if value.lower() in ('true', 'false'):
                    value = value.lower() == 'true'
                elif value.isdigit():
                    value = int(value)
                else:
                    value = value.strip('"\'')
                target = meta if current_key == '__meta__' else entries[current_key]
                target[field] = value
                current_field = None
            else:
                entries[current_key][field] = []
                current_field = field
            continue
        # List item: "      - text"
        m = re.match(r'^      -\s*(.+)$', raw)
        if m and current_key and current_field:
            entries[current_key][current_field].append(m.group(1).strip().strip('"\''))
    entries.pop('__meta__', None)
    return entries, meta


def curation_key(node):
    """Stable key: source_file::symbol. Doesn't depend on the id graphify generates.

    Normalizes the label: Swift methods come in as '.setX()' and JS hooks
    as 'useX()'. Curation is written with the clean name: 'setX', 'useX'.
    """
    sf = node.get('source_file', '')
    label = node.get('label', '')
    # docs mode, registry JSON node: source_file already IS the key
    # ('registry.json::N2-047', the format SKILL.md documents). Also
    # concatenating the label would produce a key with two '::', spaces and ':' from the title,
    # which curation.yaml's parser can't read - curation would be impossible
    # or would silently end up orphaned. See H-30.
    if '::' in sf:
        return sf
    # docs mode, standalone document (.md/.pdf): the file IS the node.
    if label.endswith(('.md', '.pdf')):
        return sf
    if label.endswith('.js') or label.endswith('.swift'):
        return sf
    return f"{sf}::{label.strip().lstrip('.').rstrip('()')}"


def main():
    if '--extract' in sys.argv or not AST_RAW.exists():
        if EXTRACT_MODE == 'docs':
            extract_docs()
        else:
            extract_ast()

    ast = json.loads(AST_RAW.read_text(encoding='utf-8'))
    all_nodes = {n['id']: n for n in ast['nodes']}
    all_edges = ast['edges']

    # 1. Seed: nodes whose file belongs to the subsystem.
    seed_ids = {
        nid for nid, n in all_nodes.items()
        if NAV_RE.search(n.get('source_file', '') or '')
        and not EXCLUDE_RE.search(n.get('source_file', '') or '')
    }

    # 2. Blast-radius: direct neighbors (who uses them / what they depend on).
    #    ref_* nodes are external (react, react-native): not our code.
    neighbor_ids = set()
    for e in all_edges:
        s, t = e.get('source'), e.get('target')
        if s in seed_ids and t not in seed_ids and not str(t).startswith('ref_'):
            neighbor_ids.add(t)
        if t in seed_ids and s not in seed_ids and not str(s).startswith('ref_'):
            neighbor_ids.add(s)
    def is_signal(nid):
        """A neighbor gets in if it's real code and not a decorative symbol."""
        n = all_nodes.get(nid)
        if not n or EXCLUDE_RE.search(n.get('source_file', '') or ''):
            return False
        # System types the Swift AST extracts as nodes (Bool, UIView,
        # UIFocusEnvironment...): not our code, nothing to curate.
        if not n.get('source_file'):
            return False
        label = (n.get('label') or '').rstrip('()')
        # Neighbor files always get in: they give the context of where the consumer lives.
        if label.endswith(('.js', '.swift')):
            return True
        if PARSER_ARTIFACT_RE.search(label):
            return False
        return not NOISE_SYMBOL_RE.match(label)

    neighbor_ids = {nid for nid in neighbor_ids if is_signal(nid)}
    seed_ids = {nid for nid in seed_ids if is_signal(nid)}

    keep = seed_ids | neighbor_ids

    # 3. Degrees over the FULL graph (the real impact, not the subgraph's).
    in_deg, out_deg = Counter(), Counter()
    consumers, dependencies = defaultdict(list), defaultdict(list)
    for e in all_edges:
        s, t, rel = e.get('source'), e.get('target'), e.get('relation')
        if rel in DEGREE_RELATIONS:
            in_deg[t] += 1
            out_deg[s] += 1
            if t in keep and s in all_nodes:
                consumers[t].append(all_nodes[s].get('label', '?'))
            if s in keep and t in all_nodes:
                dependencies[s].append(all_nodes[t].get('label', '?'))

    # 4. Curation.
    curation, meta = load_curation()
    used_keys = set()

    nodes_out = []
    for nid in keep:
        n = all_nodes[nid]
        key = curation_key(n)
        cur = curation.get(key, {})
        if cur:
            used_keys.add(key)
        node = {
            'id': nid,
            'label': n.get('label'),
            'source_file': n.get('source_file'),
            'source_location': n.get('source_location'),
            'in_degree': in_deg[nid],
            'out_degree': out_deg[nid],
            'impact': impact_of(in_deg[nid]),
            'is_core': nid in seed_ids,
            # It's a FILE if its label is one, or if its source_file points to a
            # whole file (with no trailing '::something'). Only looking at the label left
            # PDFs marked as a symbol, because the extractor stores its stem. H-29.
            'kind': ('file' if (str(n.get('label', '')).endswith(FILE_SUFFIXES)
                                or (str(n.get('source_file', '')).endswith(FILE_SUFFIXES)
                                    and '::' not in str(n.get('source_file', ''))))
                     else 'symbol'),
            'consumers': sorted(set(consumers[nid]))[:12],
            'dependencies': sorted(set(dependencies[nid]))[:12],
            # Curated
            'layer': cur.get('layer', 0),
            'what': cur.get('what', ''),
            # issue: defect flag, set by hand node by node in curation.yaml.
            # NOT deduced from the gotchas text: if it depended on finding a
            # keyword, a gotcha written differently would stop showing up in the
            # filter and nobody would know. Values: 'bug' | 'duplicate' | 'dead'.
            'issue': cur.get('issue', ''),
            'module_what': '',                   # what the file it lives in does
            'module_file': '',
            'why': cur.get('why', ''),           # what problem it solves
            'ux': cur.get('ux', ''),             # what the user sees/feels on TV
            'when': cur.get('when', ''),         # when it runs / who triggers it
            'if_broken': cur.get('if_broken', ''),  # what breaks if it fails
            'protected': cur.get('protected', ''),
            'flows': cur.get('flows', []),
            'cases': cur.get('cases', []),
            'gotchas': cur.get('gotchas', []),
        }
        nodes_out.append(node)

    # Orphaned curation: the node no longer exists in the AST -> the curation lied.
    orphans = sorted(set(curation) - used_keys)

    # Candidates for issue:dead by reachability (Malavolta et al. 2023,
    # "Lacuna", TSE — 87.9% F-score detecting unreachable code via
    # components disconnected from the root node). Doesn't decide: it only reduces
    # the search space for Step 6. in_degree=0 over the WHOLE GRAPH
    # (not just the subsystem) is the same signal Lacuna uses as dead;
    # 17.5% false positives in the paper (public exports, entry points)
    # is too many to flag alone, the human still confirms each one.
    dead_candidates = sorted(
        (n['label'] or n['id'] for n in nodes_out
         if n['kind'] == 'symbol' and n['in_degree'] == 0 and not n['issue']),
    )

    # 5. File -> symbol inheritance. A curated file's main symbol
    #    (useFocusPressable() in useFocusPressable.js) inherits its meaning:
    #    curating both the file AND the hook separately would duplicate the same truth.
    by_file = {n['source_file']: n for n in nodes_out if n['kind'] == 'file'}
    for n in nodes_out:
        parent = by_file.get(n['source_file'])
        if not parent or parent is n:
            continue
        if not n['layer']:
            n['layer'] = parent['layer']
        # Only the symbol homonymous with the file inherits the text (the "main export").
        stem = Path(n['source_file']).name.split('.')[0].lower()
        if (n['label'] or '').rstrip('()').lower() == stem:
            for field in ('what', 'why', 'ux', 'when', 'if_broken', 'protected', 'issue'):
                if not n[field]:
                    n[field] = parent[field]
            for field in ('flows', 'cases', 'gotchas'):
                if not n[field]:
                    n[field] = list(parent[field])

    # 5b. A symbol with no description of its own shows its file's as context:
    #     it doesn't invent anything, it just says where it lives. Its own description
    #     is written by hand in curation.yaml by reading the code — never derived from the name.
    for n in nodes_out:
        if n['what']:
            continue
        parent = by_file.get(n['source_file'])
        if parent and parent.get('what'):
            n['module_what'] = parent['what']
            n['module_file'] = parent['label']

    layer_of = {n['id']: n['layer'] for n in nodes_out}

    # 6. Edges. layer_violation: the dependency goes up a layer (4 -> 1).
    edges_out = []
    seen = set()
    for e in all_edges:
        s, t = e.get('source'), e.get('target')
        if s not in keep or t not in keep or s == t:
            continue
        sig = (s, t, e.get('relation'))
        if sig in seen:
            continue
        seen.add(sig)
        ls, lt = layer_of.get(s, 0), layer_of.get(t, 0)
        # Violation: only makes sense if the project declared a
        # directional rule (CHECK_LAYER_VIOLATIONS). Grouping does NOT imply direction:
        #   - Atomic Design groups by composition (an atom doesn't "use" molecules)
        #   - REST / GraphQL / microservices are PARALLEL categories
        #   - encoder / decoder are symmetric pairs
        # In those cases there's nothing to violate, and flagging violations produces
        # meaningless alarms. With a rule (hexagonal, layers), healthy goes down:
        # group 4 uses 3, 3 uses 2. What goes up is the violation.
        #
        # Group 0 (cross-cutting: logging, config, auth) is exempt: it
        # belongs to no group, anyone can use it. Without this exemption,
        # 89% of the original case's violations were false (112 of 112).
        #
        # 'contains' is file structure, not a dependency.
        violation = bool(
            CHECK_LAYER_VIOLATIONS
            and ls and lt and ls < lt
            and e.get('relation') != 'contains'
        )
        edges_out.append({
            'source': s,
            'target': t,
            'relation': e.get('relation'),
            'confidence': e.get('confidence', 'EXTRACTED'),
            'source_location': e.get('source_location'),
            'layer_violation': violation,
        })

    # 7. Curated edges (what the AST can't see).
    for key, cur in curation.items():
        for target_key in cur.get('curated_edges', []):
            src = next((n['id'] for n in nodes_out if curation_key_of(n) == key), None)
            tgt = next((n['id'] for n in nodes_out if curation_key_of(n) == target_key), None)
            if src and tgt:
                edges_out.append({
                    'source': src, 'target': tgt, 'relation': 'related',
                    'confidence': 'CURATED', 'source_location': None,
                    'layer_violation': False,
                })

    graph = {
        'meta': {
            'generated_from': str(SRC_ROOT),
            'core_nodes': len(seed_ids),
            'neighbor_nodes': len(neighbor_ids),
            'total_nodes': len(nodes_out),
            'total_edges': len(edges_out),
            'curated_nodes': len(used_keys),
            'orphan_curation': orphans,
            'dead_candidates': dead_candidates,
            # curation.yaml's meta: block. The title, layers,
            # and viewer introduction all come from here. Nothing domain-specific lives in
            # the HTML: that way the same template serves any project.
            'layers': {k: v for k, v in meta.items() if k.startswith('layer_')},
            'intro': {k: v for k, v in meta.items() if not k.startswith('layer_')},
        },
        'nodes': sorted(nodes_out, key=lambda n: (-n['in_degree'], n['label'] or '')),
        'edges': edges_out,
    }
    OUT.write_text(json.dumps(graph, ensure_ascii=False, indent=1), encoding='utf-8')

    build_viewer(graph)

    print(f"{OUT.name} -> {len(nodes_out)} nodes "
          f"({len(seed_ids)} from the subsystem + {len(neighbor_ids)} neighbors), {len(edges_out)} edges")
    if len(nodes_out) > MAX_NODES_WARN:
        print(f"\n  WARNING: {len(nodes_out)} nodes exceeds the recommended limit ({MAX_NODES_WARN}).")
        print("  The scope is too broad and curation will become unviable.")
        print("  Reduce SEEDS before continuing - an uncurated graph can consume")
        print("  more context than having no graph at all.")
    viol = sum(1 for e in edges_out if e['layer_violation'])
    print(f"curated: {len(used_keys)}/{len(curation)}" +
          (f" | violations: {viol}" if CHECK_LAYER_VIOLATIONS else
           " | violations: disabled (no dependency rule)"))
    print(f"index.html -> {VIEWER.stat().st_size // 1024} KB (self-contained)")
    if orphans:
        print(f"\n  WARNING: {len(orphans)} curation.yaml entries with no node in the AST.")
        print("  The code changed or the key is misspelled:")
        for o in orphans:
            print(f"    - {o}")
    if dead_candidates:
        print(f"\n  {len(dead_candidates)} candidates for 'issue: dead' by reachability "
              "(0 consumers across the whole graph, no issue flagged yet):")
        for d in dead_candidates[:20]:
            print(f"    - {d}")
        if len(dead_candidates) > 20:
            print(f"    ... and {len(dead_candidates) - 20} more.")
        print("  These are NOT confirmed 'dead': review them in Step 6 before flagging.")
        print("  A public export or entry point also gives 0 consumers.")


# The nodes already built have the same shape as the AST's for the key,
# so we reuse curation_key instead of duplicating the normalization.
curation_key_of = curation_key


def build_viewer(graph):
    """Embeds the graph in the template -> self-contained index.html.

    A single file, no CDN or fetch: it opens with a double click and works
    even if moved to a different folder or sent by email.
    """
    if not TEMPLATE.exists():
        print(f'  warning: {TEMPLATE.name} missing, viewer not generated')
        return
    html = TEMPLATE.read_text(encoding='utf-8')
    payload = json.dumps(graph, ensure_ascii=False, separators=(',', ':'))
    # </script> inside the JSON would close the block early.
    # The title is injected into the <head> at build time, not only via JS: that way there's no
    # generic-title flash or dependency on the JS actually running. See H-33.
    titulo = (graph.get('meta', {}).get('intro') or {}).get('titulo')
    if titulo:
        html = re.sub(r'<title>.*?</title>',
                      '<title>' + titulo.replace('<', '') + '</title>', html, count=1)

    payload = payload.replace('</', '<\\/')
    marker = '/*__GRAPH__*/{"nodes":[],"edges":[],"meta":{}}'
    if marker not in html:
        print('  warning: __GRAPH__ marker not found in the template')
        return
    VIEWER.write_text(html.replace(marker, payload), encoding='utf-8')


def extract_ast():
    """Extracts the AST from SRC_ROOT and each EXTRA_ROOT, and merges them.

    Extra roots exist for code that lives outside the main one - the
    typical case is a native SDK next to a JavaScript src/. They're extracted separately
    because cache_root sets source_file's prefix: each one needs its own
    so curation references them with the same path seen in the repo.
    """
    import subprocess
    extras = [(str(p), pref) for p, pref in EXTRA_ROOTS if p.exists()]
    print(f'extracting AST from {SRC_ROOT}' + (f' + {len(extras)} extra root(s)' if extras else ''))
    code = f'''
import json
from pathlib import Path
from graphify.extract import collect_files, extract

SRC = Path(r"{SRC_ROOT}")
EXTRAS = {extras!r}

# The main root: everything graphify knows how to parse (25 languages).
files = collect_files(SRC)
res = extract(files, cache_root=SRC)
print(f"  {{SRC.name}}: {{len(res['nodes'])}} nodes")

# Extra roots: cache_root is set so source_file comes out prefixed.
for path, prefix in EXTRAS:
    p = Path(path)
    extra_files = collect_files(p)
    if not extra_files:
        continue
    # Go up as many levels as the prefix has segments -> source_file = prefix/file
    root = p
    for _ in range(len(Path(prefix).parts)):
        root = root.parent
    ex = extract(extra_files, cache_root=root)
    res["nodes"] += ex["nodes"]
    res["edges"] += ex["edges"]
    print(f"  {{prefix}}: {{len(ex['nodes'])}} nodes")

Path(r"{AST_RAW}").write_text(json.dumps(res, ensure_ascii=False))
print(f"total AST: {{len(res['nodes'])}} nodes, {{len(res['edges'])}} edges")
'''
    subprocess.run([str(GRAPHIFY_PY), '-c', code], check=True)


def extract_docs():
    """Extracts an 'AST' from a corpus WITHOUT source code: Markdown, citation/
    registry JSON, PDFs. Produces the same shape {'nodes': [...], 'edges': [...]}
    as extract_ast(), so the rest of the pipeline (blast-radius, curation,
    orphans, viewer) doesn't change a single line.

    What counts as a node:
      - Each .md file: one node per file, plus one node per level-2
        heading (##) if the file is long (>1 heading) - same as a
        code file can give a file node + symbol nodes.
      - Each entry in a registry JSON (a list of objects with 'id'): one
        node per entry. Designed for the same format as
        clasificacion_fuentes.json (id, titulo, relevancia_hueco...).
      - Each .pdf: one node (the whole document). There's no internal AST for a
        PDF without OCR/NLP - it stays as a leaf node, to be curated by hand (what/why).

    What counts as an edge (ONLY EXPLICIT references already written, never
    inferred by similarity - inferring would mean hallucinating relations, H-01):
      - Wikilinks [[id]] in Markdown -> edge to the node with that id/file.
      - Relative Markdown links [text](other.md) -> edge to that file.
      - List field declared as a relation in the JSON (by default
        'relevancia_hueco', 'relacionado_con', 'cita_a' - whichever
        exists first) -> edge from the entry to each value in that list.
    """
    import re as _re

    nodes, edges = [], []
    id_to_node_id = {}  # declared id (frontmatter, 'id' field) -> internal node id
    path_to_node_id = {}  # relative path -> internal node id (for file-based links)
    next_id = [0]

    def new_id():
        next_id[0] += 1
        return f"doc_{next_id[0]}"

    def rel(p):
        return str(p.relative_to(DOCS_ROOT))

    files = sorted(DOCS_ROOT.rglob('*'))
    md_files = [f for f in files if f.suffix == '.md']
    json_files = [f for f in files if f.suffix == '.json']
    pdf_files = [f for f in files if f.suffix == '.pdf']

    # 1. Markdown: one node per file, plus nodes per ## heading if there are several.
    heading_re = _re.compile(r'^##\s+(.+)$', _re.MULTILINE)
    wikilink_re = _re.compile(r'\[\[([^\]]+)\]\]')
    mdlink_re = _re.compile(r'\[[^\]]*\]\(([^)]+\.md)\)')

    for f in md_files:
        text = f.read_text(encoding='utf-8', errors='ignore')
        file_node_id = new_id()
        file_label = f.name
        nodes.append({'id': file_node_id, 'label': file_label,
                       'source_file': rel(f), 'source_location': None})
        path_to_node_id[rel(f)] = file_node_id
        path_to_node_id[f.stem] = file_node_id

        headings = heading_re.findall(text)
        if len(headings) > 1:
            for h in headings:
                sym_id = new_id()
                nodes.append({'id': sym_id, 'label': h.strip()[:80],
                               'source_file': rel(f), 'source_location': None})
                edges.append({'source': file_node_id, 'target': sym_id,
                               'relation': 'contains', 'confidence': 'EXTRACTED'})

        for m in wikilink_re.finditer(text):
            edges.append({'source': file_node_id, 'target': m.group(1).strip(),
                           'relation': 'references', 'confidence': 'EXTRACTED',
                           '_unresolved_target': True})
        for m in mdlink_re.finditer(text):
            target_path = (f.parent / m.group(1)).resolve()
            try:
                edges.append({'source': file_node_id,
                               'target': rel(target_path), 'relation': 'references',
                               'confidence': 'EXTRACTED', '_unresolved_target': True})
            except ValueError:
                pass  # the link goes outside DOCS_ROOT, not an internal reference

    # 2. Registry JSON: each entry in a list with 'id' is a node.
    #    Designed for clasificacion_fuentes.json (or any {"fuentes": [...]}).
    relation_field_candidates = ('relevancia_hueco', 'relacionado_con', 'cita_a', 'refs')
    for f in json_files:
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        entries = data.get('fuentes', data) if isinstance(data, dict) else data
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict) or 'id' not in entry:
                continue
            node_id = new_id()
            id_to_node_id[entry['id']] = node_id
            nodes.append({'id': node_id, 'label': entry.get('titulo', entry['id'])[:80],
                           'source_file': f"{rel(f)}::{entry['id']}",
                           'source_location': None})
            rel_field = next((rf for rf in relation_field_candidates if entry.get(rf)), None)
            if rel_field:
                for target in entry[rel_field]:
                    edges.append({'source': node_id, 'target': str(target),
                                   'relation': 'sustains', 'confidence': 'EXTRACTED',
                                   '_unresolved_target': True})

    # 3. PDFs: one node per file, no internal structure. Curated as a leaf node.
    for f in pdf_files:
        node_id = new_id()
        nodes.append({'id': node_id, 'label': f.stem[:80],
                       'source_file': rel(f), 'source_location': None})
        path_to_node_id[rel(f)] = node_id
        path_to_node_id[f.stem] = node_id

    # 4. Resolve edge targets that were stored as an id/path instead of node_id.
    #    Ones that don't resolve to any known node are dropped (broken
    #    reference or something outside the corpus) instead of creating a phantom node.
    resolved_edges, conceptos, descartadas = [], {}, []
    for e in edges:
        if not e.pop('_unresolved_target', False):
            resolved_edges.append(e)
            continue
        tgt = e['target']
        node_id = id_to_node_id.get(tgt) or path_to_node_id.get(tgt) or path_to_node_id.get(Path(tgt).stem)
        if node_id:
            e['target'] = node_id
            resolved_edges.append(e)
        elif e['relation'] == 'sustains':
            # Relation field declared in a JSON (relevancia_hueco and
            # similar). The referent EXISTS and is written - what doesn't exist
            # is a document of its own. Materializing it as a node doesn't infer anything:
            # it draws the relation exactly as the corpus declares it. Dropping it
            # (what it used to do, silently) lost 100% of these
            # edges and left the graph with no blast-radius. See H-29.
            if tgt not in conceptos:
                nid = new_id()
                conceptos[tgt] = nid
                nodes.append({'id': nid, 'label': tgt,
                              'source_file': f'(declared referent)::{tgt}',
                              'source_location': None})
            e['target'] = conceptos[tgt]
            resolved_edges.append(e)
        else:
            # Wikilink or relative link to something that doesn't exist: that IS a
            # broken reference, and it's dropped instead of inventing the destination.
            descartadas.append(tgt)

    res = {'nodes': nodes, 'edges': resolved_edges}
    AST_RAW.write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
    print(f"extracted from {DOCS_ROOT}: {len(nodes)} nodes "
          f"({len(md_files)} .md, {len(json_files)} .json, {len(pdf_files)} .pdf, "
          f"{len(conceptos)} declared referents), "
          f"{len(resolved_edges)} resolved references")
    if descartadas:
        # Never silently: a silent drop makes the graph look complete.
        muestra = ', '.join(sorted(set(descartadas))[:5])
        print(f"  WARNING: {len(descartadas)} dropped references (destination doesn't exist): {muestra}")
    if not resolved_edges:
        print("  WARNING: 0 edges. If the corpus has no explicit wikilinks/relation")
        print("  fields, the graph will be disconnected nodes only - still useful for")
        print("  curation (what/why per document) but not for blast-radius.")


if __name__ == '__main__':
    main()
