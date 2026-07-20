#!/usr/bin/env python3
"""Construye un grafo de codigo hibrido: subsistema + su blast-radius.

Estructura (nodos, edges, impacto) = AST via graphify. Ground truth, regenerable.
Significado (grupo, que hace, por que) = curation.yaml. Escrito a mano leyendo.

Uso:
    python3 build.py --extract   # extrae el AST y construye
    python3 build.py             # reconstruye con el AST cacheado (~1s)

Configuracion: el bloque CONFIG de abajo. Nada mas se toca por proyecto.

═══════════════════════════════════════════════════════════════════════════════
POR QUE ESTE SCRIPT HACE LO QUE HACE
Cada decision salio de un error real construyendo el primer grafo con el.
═══════════════════════════════════════════════════════════════════════════════

1. AGRUPAR NO ES LO MISMO QUE DEPENDER. Son dos ejes independientes.
   Atomic Design agrupa por composicion (un atomo no "usa" moleculas). REST /
   GraphQL / microservicios son categorias paralelas. Codificador / decodificador
   son pares simetricos. En todos esos casos NO hay direccion que violar, y por
   eso CHECK_LAYER_VIOLATIONS existe: solo se activa si el proyecto declaro una
   regla direccional real (hexagonal, capas de dependencia).

2. EL GRUPO 0 (TRANSVERSAL) NO ES "SIN CLASIFICAR".
   Es la infraestructura que usa todo el mundo (logging, config, auth, helpers) y
   que no pertenece a ningun grupo. Marcarla como un grupo mas produjo 112
   violaciones falsas de 112. Con la exencion quedaron 12 reales. Un grafo que
   grita 112 alarmas falsas entrena al usuario a ignorar el rojo.
   Y si un archivo es transversal, SUS SIMBOLOS TAMBIEN: los edges apuntan al
   simbolo, no al archivo. Olvidarlo devolvio las violaciones de 12 a 40.

3. EL AVISO DE CURACION HUERFANA NO ES DECORATIVO.
   Es lo que impide que el grafo mienta. Caza claves inventadas: rutas que no
   existen (Boton/Boton.js cuando el real es Boton/index.js), helpers curados en
   el archivo equivocado, simbolos que el AST no extrae. Sin el, el grafo tendria
   descripciones apuntando a nada y nadie se enteraria.

4. EL AST NO VE TODO. Comprobado:
   - Re-exports (export const x = otroModulo.y).
   - Propiedades computadas (var foo: Bool { ... } en Swift).
   - Algunos exports sueltos, sin patron claro.
   Es el limite del parser, no un fallo. Por eso la curacion se escribe LEYENDO
   el archivo, nunca fiandose de la lista de nodos.

5. EL AST TAMBIEN METE RUIDO. Se filtra:
   - Tipos del sistema extraidos como codigo propio (Bool, UIView...): salen sin
     source_file.
   - Artefactos del parser: comentarios que quedan como nodo, desestructuraciones
     de import.

6. NUNCA DERIVAR DESCRIPCIONES DEL NOMBRE.
   Se intento y se descarto: "setIsNavigating -> escribe is navigating en el
   estado global" es una tautologia disfrazada de documentacion. Ensucia el grafo
   con ruido que aparenta conocimiento. Si un nodo no se ha leido, se queda sin
   describir.

7. HERENCIA != DESCRIPCION PROPIA.
   Un simbolo puede mostrar el contexto de su archivo, pero eso no es describirlo.
   Contarlas juntas reporto 100% de cobertura con 547 nodos sin descripcion real.
═══════════════════════════════════════════════════════════════════════════════
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent

# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  CONFIG — lo unico que se toca por proyecto. Sale del Paso 1 (planning).  ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

# 1. RAIZ DEL CODIGO. Lo que se extrae. EXTRA_ROOTS es para codigo fuera de la
#    raiz principal (ej: el SDK nativo iOS junto a un src/ de JavaScript).
#    Cada extra: (ruta, prefijo con el que aparece en el grafo).
SRC_ROOT = Path('/ruta/absoluta/a/tu/proyecto/src')
EXTRA_ROOTS = [
    # (Path('/ruta/al/proyecto/ios/App'), 'ios/App'),
]

# 2. SEMILLAS. Un archivo ES del subsistema si su ruta (relativa a SRC_ROOT)
#    matchea alguno de estos patrones. Los VECINOS no se declaran: el script los
#    saca siguiendo los edges. Eso es el blast-radius.
#    Test: ¿este archivo existiria si el subsistema no existiera? Si -> vecino.
SEEDS = [
    r'^ruta/de/tu/subsistema/',
    r'^otra/ruta/relevante',
]

# 3. RUIDO. Lo que nunca entra.
#    Los tests se excluyen porque inflan el impacto (30 tests hacen que un simbolo
#    parezca muy usado), pero son buena fuente para CURAR.
EXCLUDE_RE = re.compile(r'__tests__|\.test\.|/package\.json$|\.styles\.js$|/node_modules/'
                        r'|\.stories\.|/__mocks__/|\.snap$')

# 4. REGLA DE DEPENDENCIA (opcional). Solo ponlo en True si el proyecto TIENE
#    una regla direccional declarada del tipo "el grupo 4 puede usar el 3, nunca
#    al reves". Entonces un edge que sube se marca como violacion.
#
#    Dejalo en False si agrupas por composicion (Atomic Design: un atomo no "usa"
#    una molecula), por feature, o por tipo de artefacto. En esos casos no hay
#    direccion que violar, y activarlo produce alarmas que no significan nada.
#    El grafo sigue sirviendo para blast-radius y comprension.
CHECK_LAYER_VIOLATIONS = False

# 5. AVISO DE TAMANO. Si el grafo supera esto, el alcance esta mal: para y
#    reduce las semillas. Un grafo que no se puede curar entero no sirve.
MAX_NODES_WARN = 1500

# ── Ejemplo real (el caso que origino este skill) ──────────────────────────────
# SRC_ROOT = Path('/Users/x/proyecto/src')
# EXTRA_ROOTS = [(Path('/Users/x/proyecto/ios/NextPlay'), 'ios/NextPlay')]
# SEEDS = [r'^core/atoms/navbar/', r'^core/TVEventService/',
#          r'^components/content/NavBarTV/', r'^ios/NextPlay/TVRemoteInterceptor']
# -> 934 nodos (667 del subsistema + 267 vecinos), 3197 edges
# ══════════════════════════════════════════════════════════════════════════════

# 6. MODO DE EXTRACCION. 'code' usa graphify/tree-sitter (AST de codigo fuente).
#    'docs' usa un extractor propio para corpus SIN codigo: Markdown, JSON de
#    citas/registros, y PDFs. No hay AST de un PDF - el "nodo" es el documento
#    completo (metadata como source_file), y las "aristas" salen de referencias
#    EXPLICITAS ya escritas (wikilinks [[id]] en Markdown, o el campo que el
#    propio JSON declare como relacion, ej. relevancia_hueco). Es el mismo
#    principio (estructura automatizable + significado leido a mano), con una
#    capa de extraccion distinta porque no hay tree-sitter para PDFs.
#    Ver 'que NO cubre este skill' en SKILL.md antes de usar 'docs': la fiabilidad
#    de las aristas depende de que el corpus YA tenga referencias cruzadas
#    explicitas (no se infieren por similitud semantica - eso alucinaria, H-01).
EXTRACT_MODE = 'code'  # 'code' | 'docs'

# Solo si EXTRACT_MODE = 'docs': raiz del corpus de documentos.
DOCS_ROOT = Path('/ruta/absoluta/a/tu/corpus')

# graphify: extractor de AST (25 lenguajes, local, sin API key).
# Por defecto usa el python del entorno; si lo tienes en un venv, apunta aqui.
GRAPHIFY_PY = Path(sys.executable)

AST_RAW = HERE / 'ast-raw.json'
CURATION = HERE / 'curation.yaml'
OUT = HERE / 'code-graph.json'
TEMPLATE = HERE / 'viewer-template.html'
VIEWER = HERE / 'index.html'

NAV_RE = re.compile('|'.join(SEEDS))

# Simbolos que son ruido estructural: styled-components, constantes, envoltorios
# de presentacion. No son logica del subsistema.
NOISE_SYMBOL_RE = re.compile(
    r'^(styles?|Styled\w*|[A-Z_]{3,}|.*Container|.*Wrapper|.*Text|.*Icon|.*Image)$'
)

# Artefactos del parser: comentarios que quedaron como nodo y desestructuraciones
# de import ("{ handleTestIDChange }"). No son simbolos, no hay nada que curar.
PARSER_ARTIFACT_RE = re.compile(r'^\{|\s{2,}|^(NOTE|TODO|FIXME|HACK|XXX)[: ]')

IMPACT_TIERS = [(50, 'CRITICO'), (20, 'ALTO'), (8, 'MEDIO'), (2, 'BAJO')]

# Relaciones que cuentan como USO y por tanto suman grado (= impacto).
# Las cinco primeras son del modo 'code'; 'references' y 'sustains' son del modo
# 'docs'. 'contains' queda fuera a proposito: es contencion estructural
# (archivo -> heading), igual que archivo -> simbolo tampoco cuenta en 'code'.
# Sin las de docs, TODOS los nodos de un corpus salian con grado 0 e impacto
# HOJA, y el eje de blast-radius quedaba mudo sin avisar. Ver H-29.
DEGREE_RELATIONS = ('calls', 'imports', 'imports_from', 'method', 'indirect_call',
                    'references', 'sustains')

# Sufijos que identifican un nodo-ARCHIVO (frente a un nodo-simbolo interno).
FILE_SUFFIXES = ('.js', '.swift', '.md', '.pdf')


def impact_of(in_degree):
    for threshold, name in IMPACT_TIERS:
        if in_degree >= threshold:
            return name
    return 'HOJA'


def load_curation():
    """Lee curation.yaml sin dependencias externas (subset YAML acotado)."""
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
        # Clave de nodo: "  path/to/file.js::symbol:" (2 espacios de indent)
        m = re.match(r'^  ([^\s:][^:]*(?:::[^\s:]+)?):\s*$', raw)
        if m and not raw.startswith('    '):
            current_key = m.group(1).strip()
            entries.setdefault(current_key, {})
            current_field = None
            continue
        # Campo escalar: "    field: value"
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
        # Item de lista: "      - texto"
        m = re.match(r'^      -\s*(.+)$', raw)
        if m and current_key and current_field:
            entries[current_key][current_field].append(m.group(1).strip().strip('"\''))
    entries.pop('__meta__', None)
    return entries, meta


def curation_key(node):
    """Clave estable: source_file::symbol. No depende del id que genere graphify.

    Normaliza el label: los metodos Swift vienen como '.setX()' y los hooks JS
    como 'useX()'. La curacion se escribe con el nombre limpio: 'setX', 'useX'.
    """
    sf = node.get('source_file', '')
    label = node.get('label', '')
    # Modo docs, nodo de registro JSON: source_file ya ES la clave
    # ('registro.json::N2-047', el formato que documenta SKILL.md). Concatenar
    # ademas el label produce una clave con dos '::', espacios y ':' del titulo,
    # que el parser de curation.yaml no puede leer - la curacion seria imposible
    # o quedaria huerfana en silencio. Ver H-30.
    if '::' in sf:
        return sf
    # Modo docs, documento suelto (.md/.pdf): el archivo ES el nodo.
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

    # 1. Semilla: nodos cuyo archivo pertenece al subsistema.
    seed_ids = {
        nid for nid, n in all_nodes.items()
        if NAV_RE.search(n.get('source_file', '') or '')
        and not EXCLUDE_RE.search(n.get('source_file', '') or '')
    }

    # 2. Blast-radius: vecinos directos (quien los usa / de quien dependen).
    #    Los nodos ref_* son externos (react, react-native): no son codigo nuestro.
    neighbor_ids = set()
    for e in all_edges:
        s, t = e.get('source'), e.get('target')
        if s in seed_ids and t not in seed_ids and not str(t).startswith('ref_'):
            neighbor_ids.add(t)
        if t in seed_ids and s not in seed_ids and not str(s).startswith('ref_'):
            neighbor_ids.add(s)
    def is_signal(nid):
        """Un vecino entra si es codigo real y no un simbolo decorativo."""
        n = all_nodes.get(nid)
        if not n or EXCLUDE_RE.search(n.get('source_file', '') or ''):
            return False
        # Tipos del sistema que el AST de Swift extrae como nodos (Bool, UIView,
        # UIFocusEnvironment...): no son codigo nuestro y no hay nada que curar.
        if not n.get('source_file'):
            return False
        label = (n.get('label') or '').rstrip('()')
        # Los archivos vecinos siempre entran: dan el contexto de donde vive el consumidor.
        if label.endswith(('.js', '.swift')):
            return True
        if PARSER_ARTIFACT_RE.search(label):
            return False
        return not NOISE_SYMBOL_RE.match(label)

    neighbor_ids = {nid for nid in neighbor_ids if is_signal(nid)}
    seed_ids = {nid for nid in seed_ids if is_signal(nid)}

    keep = seed_ids | neighbor_ids

    # 3. Grados sobre el grafo COMPLETO (el impacto real, no el del subgrafo).
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

    # 4. Curacion.
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
            # Es un ARCHIVO si su label lo es, o si su source_file apunta a un
            # archivo entero (sin '::algo' detras). Mirar solo el label dejaba
            # los PDFs como simbolo, porque el extractor guarda su stem. H-29.
            'kind': ('file' if (str(n.get('label', '')).endswith(FILE_SUFFIXES)
                                or (str(n.get('source_file', '')).endswith(FILE_SUFFIXES)
                                    and '::' not in str(n.get('source_file', ''))))
                     else 'symbol'),
            'consumers': sorted(set(consumers[nid]))[:12],
            'dependencies': sorted(set(dependencies[nid]))[:12],
            # Curado
            'layer': cur.get('layer', 0),
            'what': cur.get('what', ''),
            # issue: marca de falla, puesta a mano nodo por nodo en curation.yaml.
            # NO se deduce del texto de los gotchas: si dependiera de encontrar una
            # palabra clave, un gotcha escrito de otra forma dejaria de salir en el
            # filtro y nadie se enteraria. Valores: 'bug' | 'duplicado' | 'muerto'.
            'issue': cur.get('issue', ''),
            'module_what': '',                   # que hace el archivo donde vive
            'module_file': '',
            'why': cur.get('why', ''),           # que problema resuelve
            'ux': cur.get('ux', ''),             # que ve/siente el usuario en la TV
            'when': cur.get('when', ''),         # cuando se ejecuta / quien lo dispara
            'if_broken': cur.get('if_broken', ''),  # que se rompe si falla
            'protected': cur.get('protected', ''),
            'flows': cur.get('flows', []),
            'cases': cur.get('cases', []),
            'gotchas': cur.get('gotchas', []),
        }
        nodes_out.append(node)

    # Curacion huerfana: el nodo ya no existe en el AST -> la curacion mintio.
    orphans = sorted(set(curation) - used_keys)

    # Candidatos a issue:muerto por alcanzabilidad (Malavolta et al. 2023,
    # "Lacuna", TSE — F-score 87.9% deteccion de codigo inalcanzable via
    # componentes desconectados del nodo raiz). NO decide: solo reduce el
    # espacio de busqueda del Paso 6. in_degree=0 sobre el GRAFO COMPLETO
    # (no solo el subsistema) es la misma señal que Lacuna usa como muerto;
    # 17.5% de falsos positivos en el paper (exports publicos, entry points)
    # es demasiado para marcar solo, el humano sigue confirmando cada uno.
    dead_candidates = sorted(
        (n['label'] or n['id'] for n in nodes_out
         if n['kind'] == 'symbol' and n['in_degree'] == 0 and not n['issue']),
    )

    # 5. Herencia archivo -> simbolo. El simbolo principal de un archivo curado
    #    (useFocusPressable() en useFocusPressable.js) hereda su significado:
    #    curar el archivo Y el hook por separado seria duplicar la misma verdad.
    by_file = {n['source_file']: n for n in nodes_out if n['kind'] == 'file'}
    for n in nodes_out:
        parent = by_file.get(n['source_file'])
        if not parent or parent is n:
            continue
        if not n['layer']:
            n['layer'] = parent['layer']
        # Solo el simbolo homonimo del archivo hereda el texto (el "main export").
        stem = Path(n['source_file']).name.split('.')[0].lower()
        if (n['label'] or '').rstrip('()').lower() == stem:
            for field in ('what', 'why', 'ux', 'when', 'if_broken', 'protected', 'issue'):
                if not n[field]:
                    n[field] = parent[field]
            for field in ('flows', 'cases', 'gotchas'):
                if not n[field]:
                    n[field] = list(parent[field])

    # 5b. Un simbolo sin descripcion propia muestra la de su archivo como contexto:
    #     no inventa nada, solo dice donde vive. La descripcion propia se escribe
    #     a mano en curation.yaml leyendo el codigo — nunca se deriva del nombre.
    for n in nodes_out:
        if n['what']:
            continue
        parent = by_file.get(n['source_file'])
        if parent and parent.get('what'):
            n['module_what'] = parent['what']
            n['module_file'] = parent['label']

    layer_of = {n['id']: n['layer'] for n in nodes_out}

    # 6. Edges. layer_violation: la dependencia sube de capa (4 -> 1).
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
        # Violacion: solo tiene sentido si el proyecto declaro una regla
        # direccional (CHECK_LAYER_VIOLATIONS). Agrupar NO implica direccion:
        #   - Atomic Design agrupa por composicion (un atomo no "usa" moleculas)
        #   - REST / GraphQL / microservicios son categorias PARALELAS
        #   - codificador / decodificador son pares simetricos
        # En esos casos no hay nada que violar, y marcar violaciones produce
        # alarmas sin significado. Con regla (hexagonal, capas), la sana baja:
        # grupo 4 usa el 3, el 3 usa el 2. Lo que sube es la violacion.
        #
        # El grupo 0 (transversal: logging, config, auth) queda exento: no
        # pertenece a ningun grupo, cualquiera puede usarlo. Sin esta exencion,
        # el 89% de las violaciones del caso original eran falsas (112 de 112).
        #
        # 'contains' es estructura del archivo, no una dependencia.
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

    # 7. Edges curados (lo que el AST no puede ver).
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
            # El bloque meta: del curation.yaml. De aqui salen el titulo, las
            # capas y la introduccion del visor. Nada del dominio vive en el
            # HTML: asi la misma plantilla sirve para cualquier proyecto.
            'layers': {k: v for k, v in meta.items() if k.startswith('layer_')},
            'intro': {k: v for k, v in meta.items() if not k.startswith('layer_')},
        },
        'nodes': sorted(nodes_out, key=lambda n: (-n['in_degree'], n['label'] or '')),
        'edges': edges_out,
    }
    OUT.write_text(json.dumps(graph, ensure_ascii=False, indent=1), encoding='utf-8')

    build_viewer(graph)

    print(f"{OUT.name} -> {len(nodes_out)} nodos "
          f"({len(seed_ids)} del subsistema + {len(neighbor_ids)} vecinos), {len(edges_out)} edges")
    if len(nodes_out) > MAX_NODES_WARN:
        print(f"\n  AVISO: {len(nodes_out)} nodos supera el limite recomendado ({MAX_NODES_WARN}).")
        print("  El alcance es demasiado amplio y la curacion se hara inviable.")
        print("  Reduce SEEDS antes de seguir - un grafo sin curar puede consumir")
        print("  mas contexto que no tener grafo.")
    viol = sum(1 for e in edges_out if e['layer_violation'])
    print(f"curados: {len(used_keys)}/{len(curation)}" +
          (f" | violaciones: {viol}" if CHECK_LAYER_VIOLATIONS else
           " | violaciones: desactivadas (sin regla de dependencia)"))
    print(f"index.html -> {VIEWER.stat().st_size // 1024} KB (autocontenido)")
    if orphans:
        print(f"\n  AVISO: {len(orphans)} entradas de curation.yaml sin nodo en el AST.")
        print("  El codigo cambio o la clave esta mal escrita:")
        for o in orphans:
            print(f"    - {o}")
    if dead_candidates:
        print(f"\n  {len(dead_candidates)} candidatos a 'issue: muerto' por alcanzabilidad "
              "(0 consumidores en todo el grafo, sin issue marcado aun):")
        for d in dead_candidates[:20]:
            print(f"    - {d}")
        if len(dead_candidates) > 20:
            print(f"    ... y {len(dead_candidates) - 20} mas.")
        print("  NO son 'muerto' confirmado: revisalos en el Paso 6 antes de marcar.")
        print("  Un export publico o entry point tambien da 0 consumidores.")


# Los nodos ya construidos tienen la misma forma que los del AST para la clave,
# asi que reutilizamos curation_key en vez de duplicar la normalizacion.
curation_key_of = curation_key


def build_viewer(graph):
    """Embebe el grafo en la plantilla -> index.html autocontenido.

    Un solo archivo, sin CDN ni fetch: se abre con doble click y funciona
    aunque se mueva de carpeta o se mande por correo.
    """
    if not TEMPLATE.exists():
        print(f'  aviso: falta {TEMPLATE.name}, no se genera el visor')
        return
    html = TEMPLATE.read_text(encoding='utf-8')
    payload = json.dumps(graph, ensure_ascii=False, separators=(',', ':'))
    # </script> dentro del JSON cerraria el bloque antes de tiempo.
    # El titulo se inyecta en el <head> al construir, no solo por JS: asi no hay
    # parpadeo del generico ni dependencia de que el JS corra. Ver H-33.
    titulo = (graph.get('meta', {}).get('intro') or {}).get('titulo')
    if titulo:
        html = re.sub(r'<title>.*?</title>',
                      '<title>' + titulo.replace('<', '') + '</title>', html, count=1)

    payload = payload.replace('</', '<\\/')
    marker = '/*__GRAPH__*/{"nodes":[],"edges":[],"meta":{}}'
    if marker not in html:
        print('  aviso: marcador __GRAPH__ no encontrado en la plantilla')
        return
    VIEWER.write_text(html.replace(marker, payload), encoding='utf-8')


def extract_ast():
    """Extrae el AST de SRC_ROOT y de cada EXTRA_ROOT, y los fusiona.

    Las raices extra existen para el codigo que vive fuera de la principal - el
    caso tipico es un SDK nativo junto a un src/ de JavaScript. Se extraen aparte
    porque cache_root fija el prefijo de source_file: cada una necesita el suyo
    para que la curacion las referencie con la misma ruta que se ve en el repo.
    """
    import subprocess
    extras = [(str(p), pref) for p, pref in EXTRA_ROOTS if p.exists()]
    print(f'extrayendo AST de {SRC_ROOT}' + (f' + {len(extras)} raiz(ces) extra' if extras else ''))
    code = f'''
import json
from pathlib import Path
from graphify.extract import collect_files, extract

SRC = Path(r"{SRC_ROOT}")
EXTRAS = {extras!r}

# La raiz principal: todo lo que graphify sepa parsear (25 lenguajes).
files = collect_files(SRC)
res = extract(files, cache_root=SRC)
print(f"  {{SRC.name}}: {{len(res['nodes'])}} nodos")

# Raices extra: cache_root se pone de forma que el source_file salga prefijado.
for path, prefix in EXTRAS:
    p = Path(path)
    extra_files = collect_files(p)
    if not extra_files:
        continue
    # Subir tantos niveles como segmentos tenga el prefijo -> source_file = prefijo/archivo
    root = p
    for _ in range(len(Path(prefix).parts)):
        root = root.parent
    ex = extract(extra_files, cache_root=root)
    res["nodes"] += ex["nodes"]
    res["edges"] += ex["edges"]
    print(f"  {{prefix}}: {{len(ex['nodes'])}} nodos")

Path(r"{AST_RAW}").write_text(json.dumps(res, ensure_ascii=False))
print(f"AST total: {{len(res['nodes'])}} nodos, {{len(res['edges'])}} edges")
'''
    subprocess.run([str(GRAPHIFY_PY), '-c', code], check=True)


def extract_docs():
    """Extrae 'AST' de un corpus SIN codigo fuente: Markdown, JSON de citas/
    registros, PDFs. Produce la misma forma {'nodes': [...], 'edges': [...]}
    que extract_ast(), asi el resto del pipeline (blast-radius, curacion,
    huerfanos, visor) no cambia una linea.

    Que cuenta como nodo:
      - Cada archivo .md: un nodo por archivo, mas un nodo por heading de
        nivel 2 (##) si el archivo es largo (>1 heading) - igual que un
        archivo de codigo puede dar un nodo de archivo + nodos de simbolo.
      - Cada entrada de un JSON de registro (lista de objetos con 'id'): un
        nodo por entrada. Pensado para el propio formato de
        clasificacion_fuentes.json (id, titulo, relevancia_hueco...).
      - Cada .pdf: un nodo (documento completo). No hay AST interno de un
        PDF sin OCR/NLP - queda como nodo hoja, para curar a mano (what/why).

    Que cuenta como arista (SOLO referencias EXPLICITAS ya escritas, nunca
    inferidas por similitud - inferir seria alucinar relaciones, H-01):
      - Wikilinks [[id]] en Markdown -> edge hacia el nodo con ese id/archivo.
      - Markdown links relativos [texto](otro.md) -> edge hacia ese archivo.
      - Campo de lista declarado como relacion en el JSON (por defecto
        'relevancia_hueco', 'relacionado_con', 'cita_a' - el primero que
        exista) -> edge desde la entrada hacia cada valor de esa lista.
    """
    import re as _re

    nodes, edges = [], []
    id_to_node_id = {}  # id declarado (frontmatter, campo 'id') -> node id interno
    path_to_node_id = {}  # ruta relativa -> node id interno (para links por archivo)
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

    # 1. Markdown: un nodo por archivo, mas nodos por heading ## si hay varios.
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
                pass  # el link sale de DOCS_ROOT, no es referencia interna

    # 2. JSON de registro: cada entrada de una lista con 'id' es un nodo.
    #    Pensado para clasificacion_fuentes.json (o cualquier {"fuentes": [...]}).
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

    # 3. PDFs: un nodo por archivo, sin estructura interna. Se cura como nodo hoja.
    for f in pdf_files:
        node_id = new_id()
        nodes.append({'id': node_id, 'label': f.stem[:80],
                       'source_file': rel(f), 'source_location': None})
        path_to_node_id[rel(f)] = node_id
        path_to_node_id[f.stem] = node_id

    # 4. Resolver targets de edges que se guardaron como id/ruta en vez de node_id.
    #    Los que no resuelven a ningun nodo conocido se descartan (referencia
    #    rota o a algo fuera del corpus) en vez de crear un nodo fantasma.
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
            # Campo de relacion declarado en un JSON (relevancia_hueco y
            # similares). El referente EXISTE y esta escrito - lo que no existe
            # es un documento suyo. Materializarlo como nodo no infiere nada:
            # dibuja la relacion tal y como el corpus la declara. Descartarlo
            # (lo que hacia antes, en silencio) perdia el 100% de estas
            # aristas y dejaba el grafo sin blast-radius. Ver H-29.
            if tgt not in conceptos:
                nid = new_id()
                conceptos[tgt] = nid
                nodes.append({'id': nid, 'label': tgt,
                              'source_file': f'(referente declarado)::{tgt}',
                              'source_location': None})
            e['target'] = conceptos[tgt]
            resolved_edges.append(e)
        else:
            # Wikilink o link relativo a algo que no existe: eso SI es una
            # referencia rota, y se descarta en vez de inventar el destino.
            descartadas.append(tgt)

    res = {'nodes': nodes, 'edges': resolved_edges}
    AST_RAW.write_text(json.dumps(res, ensure_ascii=False), encoding='utf-8')
    print(f"extraidos de {DOCS_ROOT}: {len(nodes)} nodos "
          f"({len(md_files)} .md, {len(json_files)} .json, {len(pdf_files)} .pdf, "
          f"{len(conceptos)} referentes declarados), "
          f"{len(resolved_edges)} referencias resueltas")
    if descartadas:
        # Nunca en silencio: un descarte mudo hace que el grafo parezca completo.
        muestra = ', '.join(sorted(set(descartadas))[:5])
        print(f"  AVISO: {len(descartadas)} referencias descartadas (destino inexistente): {muestra}")
    if not resolved_edges:
        print("  AVISO: 0 aristas. Si el corpus no tiene wikilinks/campos de relacion")
        print("  explicitos, el grafo sera solo nodos sueltos - sigue sirviendo para")
        print("  curar (what/why por documento) pero no para blast-radius.")
    if not resolved_edges:
        print("  AVISO: 0 aristas. Si el corpus no tiene wikilinks/campos de relacion")
        print("  explicitos, el grafo sera solo nodos sueltos - sigue sirviendo para")
        print("  curar (what/why por documento) pero no para blast-radius.")


if __name__ == '__main__':
    main()
