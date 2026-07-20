# Paso 1 — Planificar el grafo (con el humano)

Este paso evita rehacer trabajo. Las respuestas las da el humano; tu exploras el
codigo y **sugieres**. Nunca decidas por el: un grafo agrupado mal miente en cada
consulta, y las 112 violaciones falsas del caso original salieron justo de aqui.

Salen cinco respuestas escritas que alimentan el CONFIG de build.py.

---

## 1. ¿Cual es el subsistema y cuales son sus semillas?

Un grafo de todo no sirve: es la bola de pelo que nadie lee. Un grafo de un
subsistema con su blast-radius si.

**Pregunta:**
> "¿Que subsistema quieres entender? ¿Que carpetas o rutas lo forman?"

**Criterio:** una semilla es codigo que ES el subsistema, no algo que lo usa.
Si dudas: *¿este archivo existiria si el subsistema no existiera?* Si -> vecino.

Los vecinos NO se declaran: el script los saca siguiendo los edges. Eso es el
blast-radius, y es la mitad del valor del grafo.

**Alarma:** mas de ~1500 nodos = alcance mal puesto. Reduce las semillas.

---

## 2. ¿Como se agrupan los nodos? ← EXPLORA Y SUGIERE

<CRITICAL>
NO asumas que el proyecto se organiza en capas de dependencia. Es UNA forma
entre muchas. Explora la estructura real y sugiere lo que veas.
</CRITICAL>

Son tres movimientos: **leer el proyecto → contrastar con lo publicado →
sugerir**. En ese orden.

### 2.1 Lee la estructura real

```bash
# La forma de las carpetas suele delatar como piensa el equipo
find <src> -maxdepth 3 -type d -not -path "*/node_modules/*" | head -40

# Los imports dicen la verdad cuando las carpetas mienten:
# ¿que se importa mas y desde donde?
grep -rhoE "from ['\"][@.][^'\"]+" <src> --include="*.js" 2>/dev/null \
  | sed "s/from ['\"]//" | cut -d/ -f1-2 | sort | uniq -c | sort -rn | head -15
```

Mira tambien qué declara el propio proyecto: `README`, `CONTRIBUTING`, docs de
arquitectura, un `CLAUDE.md`. A veces la agrupacion ya está escrita.

<IMPORTANT>
Las carpetas pueden mentir. Un proyecto puede tener `components/ hooks/ utils/`
por inercia del generador y estar organizado de verdad por feature. Contrasta lo
que dicen las carpetas con lo que dicen los imports.
</IMPORTANT>

### 2.2 Contrasta con lo publicado (busqueda web)

<IMPORTANT>
No te fies solo de tu memoria de arquitecturas: hay convenciones que no conoces,
y otras que cambiaron. Busca antes de sugerir.
</IMPORTANT>

Util cuando:
- **Reconoces el patron a medias** — busca su nomenclatura oficial y sus grupos
  canonicos. Que Atomic Design tenga `templates` y `pages` ademas de los tres
  primeros no se adivina: se comprueba.
- **No reconoces nada** — busca por el stack: *"<framework> project structure
  conventions"*, *"<framework> architecture layers"*. Puede que sea un patron
  estandar del ecosistema.
- **El patron tiene reglas de dependencia declaradas** — muchas arquitecturas las
  publican (hexagonal, clean, feature-sliced). Eso alimenta directo el paso 3.
- **El proyecto usa un framework con opinion propia** — Next.js, NestJS, Django,
  Rails traen su estructura. Confirma la version, que cambian.

Ejemplos de busqueda:
```
"feature-sliced design" layers segments        <- si ves app/ pages/ widgets/
"hexagonal architecture" dependency rule       <- si ves domain/ application/
"nestjs" module structure conventions          <- si el framework tiene opinion
"atomic design" pages templates organisms      <- confirmar los grupos canonicos
```

**Correlaciona las dos fuentes.** Lo local manda: si el proyecto dice que usa
Atomic Design pero no tiene `templates/`, el grafo agrupa lo que HAY, no lo que
el patron canonico dice que deberia haber. La busqueda sirve para nombrar bien y
para no perderte grupos, no para imponer un molde.

### 2.3 Sugiere, con lo que encontraste

**Pregunta:**
> "Veo <estructura local>. Se parece a <patron>, que segun <fuente> se organiza
> en <grupos>. ¿Agrupamos asi, de otra forma, o no agrupamos?"

Patrones frecuentes, como punto de partida —**no como catalogo cerrado**:

| Si ves... | Puede ser | ¿Tiene direccion? |
|---|---|---|
| `atoms/ molecules/ organisms/` | Atomic Design | No: composicion |
| `domain/ application/ infrastructure/` | Hexagonal / Clean | Si |
| `app/ pages/ widgets/ features/ entities/ shared/` | Feature-Sliced Design | Si |
| `features/auth/ features/cart/` | Modular por dominio | A veces |
| `components/ hooks/ services/ utils/` | Tipo de artefacto | No |
| `controllers/ resolvers/ subscribers/` | Tipo de interfaz (REST/GraphQL) | No: paralelos |
| `encoders/ decoders/ codecs/` | Pares simetricos | No |
| Nativo + estado + UI | Capas de dependencia | Si |
| Nada claro | Quiza no hay agrupacion que valga | — |

**Es legitimo no agrupar.** Si el proyecto no tiene estructura clara, meter todos
los nodos en un carril y usar el grafo solo para blast-radius es mejor que
inventar una agrupacion falsa. Forzar capas donde no las hay es peor que no
tenerlas.

**La agrupacion define la posicion vertical de cada nodo en el visor.** Numera
los grupos en el orden en que quieras verlos de arriba abajo.

---

## 3. ¿Hay una regla de dependencia que vigilar? (OPCIONAL)

<IMPORTANT>
Agrupar y vigilar dependencias son DOS COSAS DISTINTAS. No las mezcles.

Atomic Design agrupa por composicion, no por dependencia: un atomo no "usa" una
molecula, la molecula se compone de atomos. Aplicarle un detector de violaciones
produce alarmas que no significan nada.
</IMPORTANT>

**Pregunta:**
> "¿Hay una regla de que puede usar que, que te interese vigilar?"

Ejemplos de reglas reales:
- *"La UI no importa de infraestructura directamente"* (hexagonal)
- *"Los organismos no importan de otros organismos"* (atomic)
- *"Ninguna feature importa de otra feature"* (modular)
- *"El componente de navegacion no depende del contenido"* (regla de UI comun)

**Si hay regla:** numera los grupos de forma que las dependencias SANAS bajen
(4 usa 3, 3 usa 2). Asi lo que sube es una violacion detectable.

**Si no hay regla:** deja `CHECK_LAYER_VIOLATIONS = False` en el CONFIG. El grafo
sigue siendo util para blast-radius y comprension; simplemente no marca nada en
rojo. Es lo normal en agrupaciones por composicion o por feature.

**Si el humano no sabe:** no la inventes. Sin regla es mejor que con una regla
falsa — una regla inventada genera alarmas que entrenan al equipo a ignorar el
rojo.

---

## 4. ¿Que es transversal? (grupo 0) ← EL MAS IMPORTANTE

Solo aplica si hay regla de dependencia (paso 3). Saltarselo produjo **112
violaciones de las cuales 112 eran falsas**.

**Pregunta:**
> "¿Que utilidades usa todo el mundo y no pertenecen a ningun grupo?"

**El test:** ¿que un nodo del grupo mas alto use esto seria un problema de
arquitectura? Si la respuesta es no, es transversal.

Casi siempre: logging, config, autenticacion, helpers de formato, contextos que
solo comparten refs, constantes.

**Ejemplos tipicos:** un helper de logging (con cientos de consumidores — no es
capa, es plomeria), configuracion global, autenticacion, utilidades de formato,
contextos que solo comparten referencias.

**Por que importa tanto:** un grafo que grita 112 alarmas falsas entrena al
usuario a ignorar el rojo. Con 12 reales, el rojo vuelve a significar algo.

---

## 4b. ¿Como se conectan las aristas cuando hay ambiguedad? (SOLO modo `docs`)

<IMPORTANT>
En modo `code` esto no se pregunta: la arista sale del AST (calls/imports), no hay
ambiguedad que decidir. Esta pregunta aplica SOLO cuando `EXTRACT_MODE = 'docs'`
(corpus sin codigo fuente — ver SKILL.md, seccion "Corpus sin codigo").
</IMPORTANT>

Un corpus de documentos no tiene un AST que diga "esto llama a aquello". La
conexion sale de lo que el corpus YA declara por escrito (wikilinks, campos de
relacion en JSON). Cuando esa señal no esta, o hay mas de una forma razonable de
leerla, no decidas tu solo — **sugiere la lectura mas obvia y pregunta**.

<IMPORTANT>
Antes de formular la propuesta, busca en la web — igual que en el paso 2.2
(agrupacion de codigo). Si el corpus es de un dominio con convenciones propias
de linkeo/citacion (ej. Zettelkasten, PRISMA, un formato de citacion academico,
un esquema de metadatos conocido como Dublin Core o schema.org), esas
convenciones ya resuelven "cual campo es la relacion" mejor que adivinarlo solo
mirando los nombres de campo. Ejemplos de busqueda:
```
"<nombre del campo visto>" metadata schema standard   <- si un campo tiene nombre raro
"zettelkasten" linking convention                       <- si ves ids tipo notas enlazadas
"PRISMA" systematic review citation graph                <- si el corpus es literatura academica
"<formato de cita visto>" citation graph field           <- si hay un campo tipo doi/cita_a
```
Igual que en 2.2: lo local manda. Si la busqueda sugiere un campo que el corpus
NO tiene, no lo inventes — usala solo para nombrar mejor la relacion que SI
esta, o para no perderte un campo equivalente que llame distinto (ej. "refs"
vs "bibliography" vs "see_also"). La busqueda mejora la propuesta que le
presentas al humano; no sustituye la confirmacion del humano.
</IMPORTANT>

<IMPORTANT>
Formula la pregunta como ACEPTAR/RECHAZAR una propuesta concreta con ejemplos
reales del corpus — nunca como "¿como quieres que conectemos?" abierta. Una
pregunta abierta obliga al humano a diseñar la solucion; una pregunta cerrada
con la sugerencia ya escrita solo le exige un veredicto. Esto esta validado:
en un estudio real (2 escenarios industriales, Watkiss-Leek et al. 2026,
"IDEA2"), separar "quien propone" (el agente) de "quien valida" (el humano)
con una decision binaria + comentario opcional logro 92-95% de aceptacion en
la primera pasada, a un costo de ~1 minuto por decision cuando la propuesta
ya venia anclada en estructura real del corpus (no en texto libre inventado).
</IMPORTANT>

**Formato de pregunta (tres niveles de esfuerzo, en este orden — nunca saltar al 3):**

1. **Decision binaria con ejemplo concreto** (obligatoria, la unica que el humano
   DEBE responder):
   > "Propongo conectar por <campo/señal encontrada>. Ejemplo real: `<nodo A>`
   > se conectaria con `<nodo B>` porque ambos <razon con el valor exacto visto,
   > ej. 'comparten relevancia_hueco: H6'>. ¿Aceptas esta regla para todo el
   > corpus? (si / no)"

2. **Elegir entre alternativas ya generadas** (solo si hay mas de una señal
   candidata — nunca redactar la alternativa, ofrecerla ya formulada):
   > "Si no: el corpus tambien tiene estos campos que podrian ser la conexion.
   > ¿Cual prefieres?
   >   a) `cita_a` — conecta quien cita a quien (direccional)
   >   b) `relevancia_hueco` — conecta quien sostiene el mismo argumento (no direccional)
   >   c) ninguno — dejar los nodos sueltos, el corpus no tiene señal fiable"

3. **Comentario libre** (opcional, solo si rechazo la propuesta y ninguna
   alternativa de la lista sirve): pedir una frase corta, nunca una redaccion
   larga — "¿en una frase, que si conectaria estos nodos para ti?"

**Casos tipicos y la propuesta concreta a ofrecer en el nivel 1 (nunca aplicar sin el "si" del humano):**

| Lo que ves en el corpus | Propuesta a poner en la pregunta de nivel 1 |
|---|---|
| Wikilinks `[[id]]` o links relativos `[texto](otro.md)` | "Conectar cada wikilink/link con el documento que referencia" — esta suele aceptarse directo, es la señal mas inambigua |
| Un campo de lista tipo `relevancia_hueco: [H1, H6]`, `cita_a: [...]`, `refs: [...]` | "Conectar entradas que comparten el mismo valor en `<campo>`" — con un ejemplo real de dos entradas que lo cumplen, sacado del propio corpus |
| Solo prosa libre, sin campos ni links | No hay propuesta de nivel 1 que ofrecer honestamente. Salta directo a decirlo: "no encuentro señal escrita de conexion — el grafo saldra con nodos sueltos, sirve para curar pero no para navegar. ¿Prefieres anadir un campo de relacion al corpus antes de seguir, o continuamos sin aristas?" (esto tambien es una pregunta cerrada, no abierta) |
| Varios campos candidatos a la vez | Usa el nivel 2 directo: ofrece cada campo como opcion ya formulada con su propio ejemplo, no preguntes "¿cual usarias?" en abstracto |

**Nodos que quedan sin ninguna arista tras la extraccion:** no los ocultes ni los
conectes a la fuerza. Muestraselos al humano como lista aparte ("N documentos sin
conexion detectada") — es la misma logica que un nodo de codigo con 0 consumidores
(candidato a revisar, no un error a corregir en silencio, ver Paso 6 y N1-039).

---

## 5. ¿Que es ruido?

**Pregunta:**
> "¿Que archivos no aportan nada al entendimiento del subsistema?"

**Por defecto:** tests, estilos, mocks, generados, snapshots.

**Ojo con los tests:** fuera del grafo porque inflan el impacto (30 tests hacen
que un simbolo parezca muy usado), pero son buena fuente para CURAR: un test bien
escrito dice que se espera de la funcion.

**Ruido del propio AST** (comprobado): tipos del sistema extraidos como codigo
propio (`Bool`, `UIView`), comentarios que quedan como nodo, desestructuraciones
de import. El script filtra los nodos sin `source_file`, que caza la mayoria.

---

## Salida de este paso

Ensena esto al humano y pide confirmacion ANTES de extraer nada:

```
Subsistema  : <nombre>
Semillas    : <rutas>
Agrupacion  : <por que criterio, y por que ese>
  grupo 1   : <nombre> - <descripcion>
  grupo 2   : <nombre> - <descripcion>
  ...
Regla dep.  : <la regla | NO HAY - violaciones desactivadas>
Grupo 0     : <transversal, si aplica>
Excluido    : <ruido>
Aristas     : <SOLO modo docs: que campo/señal se usa para conectar, confirmado por el humano>
```
