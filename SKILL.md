---
name: code-graph
description: Use when someone needs to understand a complex subsystem they didn't write - "how does X work", "what breaks if I change Y", onboarding to unfamiliar code, or mapping a subsystem before refactoring it. Builds a hybrid code graph - AST extracts structure, you read the code and curate meaning - and renders it as a self-contained HTML viewer. Also triggers on "grafo de codigo", "code graph", "mapear el subsistema", "graficar el codigo".
---

# Construir un grafo de codigo hibrido

Un grafo de codigo util NO se genera: se construye. El AST da la estructura
(quien llama a quien, cuantos dependen), y eso es gratis y fiable. El significado
—por que existe algo, que se rompe si falla, que race condition esconde— hay que
leerlo y escribirlo. Este skill hace las dos mitades y las mantiene separadas.

## Por que esto NO se puede automatizar del todo

<CRITICAL>
Un grafo de solo-estructura puede consumir MAS contexto que no tener grafo.
Medido en codigo real: un grafo curado usa ~1.000 tokens/consulta contra
~10.000 sin curar (Codebase-Memory, 31 repos, backend Claude) — 10x. La razon
es que un nodo con 60 aristas y sin descripcion obliga a abrir 60 archivos.
Un nodo curado responde en tres lineas.

Lo que ahorra no es el grafo. Es la densidad semantica de sus nodos.
</CRITICAL>

De ahi la regla que gobierna este skill:

**NUNCA derives una descripcion del nombre del simbolo.** `setIsNavigating` ->
"escribe is navigating en el estado global" es una tautologia disfrazada de
documentacion: ensucia el grafo con ruido que aparenta conocimiento. Si no has
leido el archivo, el nodo se queda sin describir. Sin excepciones.

## Reparto del trabajo

| Lo hace el script | Lo haces TU leyendo | Lo decide el HUMANO |
|---|---|---|
| Extraer AST | Leer cada archivo | Alcance: que entra |
| Calcular impacto | Escribir what/why/ux | Por que criterio se agrupa |
| Detectar huerfanos | Detectar duplicacion | Si hay regla de dependencia |
| Generar el visor | Marcar fallas | Validar que no miente |

## Los pasos

Sigue el orden. No es arbitrario: cada decision tardia obliga a rehacer trabajo.
En el caso que origino este skill, agrupar DESPUES de curar produjo 112 falsos
positivos que hubo que deshacer.

Crea un todo por cada paso.

### Paso 1 - PLANIFICAR (con el humano, antes de tocar nada)

<IMPORTANT>
Este paso es el que evita rehacer. No lo saltes ni lo decidas tu solo.
Lee `references/planning.md` y haz las preguntas al humano (cinco siempre,
mas una sexta si el modo es `docs` — ver "Corpus sin codigo" mas abajo).
</IMPORTANT>

<CRITICAL>
NO asumas que el proyecto se organiza en capas de dependencia. Es UNA forma entre
muchas: Atomic Design, hexagonal, feature-sliced, por dominio, por tipo de
artefacto, REST/GraphQL/microservicios, codificadores/decodificadores...

Lee la estructura, CONTRASTA con lo publicado (busca en la web el patron que
creas ver), SUGIERE, y deja que el humano decida. Un grafo agrupado con un
criterio inventado miente en cada consulta.
</CRITICAL>

Sales de aqui con seis respuestas escritas:
1. **Subsistema y semillas** - que rutas forman el nucleo
2. **Agrupacion** - por que criterio se agrupan los nodos (lees, buscas, sugieres)
3. **Regla de dependencia** - OPCIONAL: solo si hay una direccion que vigilar
4. **Transversal (grupo 0)** - que usa todo el mundo y no es de ningun grupo
5. **Ruido** - que se excluye (tests, estilos, generados)
6. **Introduccion del subsistema** - el parrafo de contexto sin el cual ningun
   nodo se entiende (ver 1.6 abajo)

Sobre (2): **usa la busqueda web**. Tu memoria de arquitecturas tiene huecos y hay
convenciones que cambiaron. Si ves `app/ pages/ widgets/ entities/`, busca si es
Feature-Sliced Design antes de inventarte los grupos. Lo local manda sobre lo
publicado: agrupa lo que HAY, no lo que el patron canonico dice que deberia haber.

Sobre (3): agrupar y depender son ejes distintos. Atomic Design agrupa por
composicion; REST/GraphQL son categorias paralelas. Ahi no hay direccion que
violar, y `CHECK_LAYER_VIOLATIONS` se queda en False. Sin regla, el grafo sigue
sirviendo para blast-radius y comprension: simplemente no marca nada en rojo.

**1.6 - Escribe la introduccion del subsistema (nivel SISTEMA, no nodo).**

<IMPORTANT>
Todo lo anterior (1-5) cura NODOS: que hace cada pieza. Nada de eso responde
por que existe el subsistema completo ni que se rompe si falla como un todo —
y ese parrafo es, de todo el grafo, el de mayor densidad semantica: es lo que
convierte una lista de tarjetas en algo que se entiende de un vistazo. Sin el,
el visor no tiene nada que mostrar antes de que el humano haga click en un
nodo (ver `meta.contexto` en el bloque de abajo).

Respaldo: arquitectura de software en produccion (Larsen & Moghaddam 2026,
"RAD-AI": el mismo patron de hueco de nivel sistema aparece en tres sistemas
de organizaciones distintas sin relacion entre si — Uber, Netflix, y sistemas
propios de los autores — lo que indica que es estructural y no una
particularidad de un proyecto, no algo que solo le faltara a este caso).
</IMPORTANT>

Pregunta al humano con formato cerrado, nunca "escribeme la introduccion"
abierta:

> "Antes de curar el primer nodo, necesito el contexto de sistema. Responde
> corto, una frase por punto — puedo redactar el parrafo final yo con tus
> respuestas:
>   a) **Por que existe este subsistema** - que problema del mundo resuelve
>      (ej.: 'sin esto, <quien lo usa> tendria que hacer <la alternativa mala>')
>   b) **El problema que origino esta forma de resolverlo** - si vino de una
>      restriccion, un incidente o una decision de diseno (ej.: 'se construyo
>      asi porque <la restriccion o el caso que fallo antes>')
>   c) **Como se nota cuando funciona / cuando falla** - la señal observable
>      para quien lo usa, no para quien lo programa (ej.: '<el sintoma visible>
>      cuando esto se rompe')
> Si alguno no aplica, dilo y lo dejo fuera — no hay que forzar los tres."

Con esas respuestas, escribe en el bloque `meta:` de `curation.yaml`:
```yaml
meta:
  titulo: <nombre corto del subsistema>
  contexto: <la respuesta a (a), en prosa>
  problema: <la respuesta a (b), en prosa — omite la clave si no aplica>
  sintomas: <la respuesta a (c), en prosa — omite la clave si no aplica>
```
Si el humano no tiene respuesta todavia, deja el paso abierto y sigue con el
resto de la planificacion — pero no cierres el subsistema sin volver a esto:
un grafo sin `meta.contexto` fuerza al visor a decirlo en vez de inventarlo
(mismo principio que "no derivar la descripcion del nombre" del Paso 5).

### Paso 2 - Confirmar el modo y preparar la extraccion

<CRITICAL>
Decide el modo ANTES de seguir. Confirma con
`find <objetivo> -type f | grep -viE '\.(md|txt|pdf|json|ya?ml|csv)$' | head`:

- Si hay codigo fuente real -> `EXTRACT_MODE = 'code'` (Paso 2a).
- Si el objetivo es un corpus sin codigo (PDFs, Markdown, JSON de citas) ->
  `EXTRACT_MODE = 'docs'` (Paso 2b). Ver seccion "Corpus sin codigo" mas abajo.

Correr el modo equivocado no falla ruidosamente: `code` sobre un corpus sin
codigo da un grafo vacio sin aviso claro. Decidelo con el humano, no lo asumas.
</CRITICAL>

**Paso 2a - modo `code`:**
```bash
python3 -c "import graphify" 2>/dev/null || pip install graphifyy -q
```
Si falla, prueba `pip install graphifyy --break-system-packages` o un venv.
graphify extrae AST de 25 lenguajes con tree-sitter, en local, sin API key.

**Paso 2b - modo `docs`:** no necesita instalar nada — el extractor de
`build.py` no tiene dependencias externas. Solo confirma que el corpus tiene
referencias explicitas entre documentos (wikilinks, campos de relacion en el
JSON); si no las tiene, el grafo saldra sin aristas (ver mas abajo).

### Paso 3 - Configurar y extraer

Copia `scripts/build.py` al proyecto (sugerido: `docs/code-graph/`) y rellena su
bloque CONFIG con lo que salio del Paso 1. Luego:

```bash
python3 build.py --extract
```

Reporta al humano: cuantos nodos core, cuantos vecinos, cuantos edges.

Si salen mas de ~1500 nodos, para y revisa el alcance con el humano: el grafo
esta cogiendo demasiado y la curacion se hara inviable.

### Paso 4 - Curar los grupos (rapido, primero)

Antes del significado, asigna `layer` a cada ARCHIVO en `curation.yaml` — el
numero del grupo que salio del Paso 1.2. Es rapido y da su sitio a cada nodo en
el visor.

Declara tambien los grupos en el bloque `meta:`, que es de donde el visor saca
los carriles y sus nombres:

```yaml
meta:
  layer_1: Atomos - los ladrillos sin dependencias
  layer_2: Moleculas - composicion de atomos
  layer_3: Organismos - secciones completas
```

<IMPORTANT>
Si un archivo es transversal (grupo 0), sus simbolos tambien. Curar el archivo
como transversal y dejar sus simbolos en otro grupo rompe la exencion por la
puerta de atras: los edges apuntan al simbolo, no al archivo.
</IMPORTANT>

<CRITICAL>
Si el corpus mezcla varios ESPACIOS DE NOMBRES distintos bajo un mismo criterio
de agrupacion (ej.: unos carriles son categorias de la literatura, otros son
hallazgos propios, otros son preguntas sin resolver — cualquier caso donde
"el numero 6" signifique algo distinto segun de que carril se trate), NO
numeres los carriles en una sola secuencia (`layer_1`...`layer_N`). Un numero
suelto no dice a que espacio pertenece sin memorizar una tabla externa —
el mismo problema que tiene usar el ID interno de un hallazgo (`H-6`) como si
fuera autoexplicativo fuera de su documento de origen.

Usa un prefijo explicito por espacio de nombres en el NOMBRE del carril
(no en el numero): si un proyecto tiene "huecos de la literatura", "hallazgos
propios" y "preguntas abiertas", los carriles se llaman con ese prefijo
legible (el proyecto elige las palabras — no hay una lista fija), nunca solo
un numero. El humano decide los prefijos en el Paso 1.2, junto con el resto
del criterio de agrupacion.
</CRITICAL>

Si activaste `CHECK_LAYER_VIOLATIONS`, corre `python3 build.py` y mira las
violaciones. Si salen decenas, casi seguro hay infraestructura sin marcar como
transversal: vuelve al Paso 1.4.

<IMPORTANT>
Un carril declarado y sin nodos NO es un error a limpiar. Si un grupo se
queda vacio porque su unico nodo se retiro o dejo de aplicar (ej.: una fuente
descartada por no cumplir un criterio de calidad del proyecto), dejalo
declarado en `meta:` con una nota corta de por que esta vacio y desde cuando.
Un carril vacio con nota es informacion honesta sobre un hueco abierto;
borrarlo lo esconde. Mismo principio que "el visor dice que no tiene
introduccion escrita en vez de inventarla" (Paso 1.6) aplicado a carriles.
</IMPORTANT>

### Paso 5 - Curar el significado (el grueso)

Lee `references/curation.md` antes de escribir la primera descripcion.

<IMPORTANT>
Antes del primer nodo, pregunta al humano si el set de campos por defecto
(`character`/`what`/`why`/`ux`/`when`/`if_broken`) alcanza o si este proyecto
necesita alguno propio (cumplimiento, restriccion fisica, dueño del nodo...).
Ver la pregunta cerrada en `references/curation.md`, seccion "Los campos" —
no lo decidas tu solo ni lo dejes para descubrirlo a mitad de la curacion.
</IMPORTANT>

Por cada archivo del subsistema:
1. **Leelo entero.** No el nombre, no la firma: el archivo.
2. Escribe `character`: que TIPO de cosa es (singleton, hook, DAO, reducer,
   modulo nativo...). El vocabulario sale del proyecto, no de un catalogo.
3. Escribe `what`, `why`, `ux`, `when`, `if_broken` (mas los campos propios
   del proyecto si el humano definio alguno en el paso anterior).
4. Decide `collapse` (ver abajo).
5. Marca `gotchas` cuando el codigo esconda algo no obvio.
6. Marca `issue` cuando el nodo tenga una falla (ver Paso 6).

**Sobre el colapso archivo + simbolo homonimo:**

<CRITICAL>
NO colapses porque los nombres coincidan. Colapsa cuando archivo y simbolo son
el MISMO CONCEPTO — y eso se decide leyendo que exporta el archivo:

  UN caracter  -> colapsa. Un archivo que exporta una sola entidad principal
                  (una funcion, una clase): el archivo ES esa entidad. Dos
                  nodos serian el mismo concepto duplicado.
  DOS o mas    -> NO colapses. Un archivo que exporta, por ejemplo, una clase
                  singleton Y una funcion independiente con consumidores casi
                  disjuntos: fusionarlos junta dos APIs que se usan por separado.

La pista fiable: ¿el homonimo es el `export default` del archivo? Si lo es,
colapsa. Si el archivo exporta varias cosas de igual rango, son nodos distintos.
</CRITICAL>

Al colapsar, los grados se FUSIONAN. En el caso original el impacto estaba
partido en dos —quien importaba el modulo contaba en un nodo, quien llamaba a la
funcion en otro— y ninguno de los dos numeros era el real: 60 + 30 = 90.

**Valida por bloques.** Cada 15-20 archivos, corre el build y ensena al humano
2-3 descripciones. Pregunta si el nivel es el correcto. Es barato corregir el
criterio en el archivo 20 y carisimo en el 200.

Tras cada bloque:
```bash
python3 build.py
```
Si avisa de **curacion huerfana**, una clave apunta a codigo que no existe:
corrigela ANTES de seguir. Ese aviso es lo que impide que el grafo mienta.

### Paso 6 - Marcar fallas (a mano, nodo a nodo)

<CRITICAL>
La bandera `issue` la pones TU leyendo el nodo. NUNCA la deduzcas buscando una
palabra clave en el texto: el dia que alguien escriba un gotcha con otras
palabras, el nodo desaparece del filtro y nadie se entera.
</CRITICAL>

Tres tipos:
- `bug` - esta mal y se nota
- `muerto` - escrito pero nunca corre (comentado, stub, no llamado)
- `duplicado` - la misma logica repetida en varios sitios

**Para `muerto`, empieza por los candidatos que ya calculo el build**, no por
los 900 nodos a ciegas. `python3 build.py` reporta los simbolos con 0
consumidores en TODO el grafo (no solo el subsistema) — es la misma señal de
alcanzabilidad que la deteccion automatica de codigo muerto usa en la
literatura, con 87.9% de acierto combinando analisis estatico+dinamico
(Malavolta et al., 2023, "Lacuna", IEEE TSE). No decide por ti: 17.5% de esos
candidatos son falsos positivos reales (exports publicos, entry points) —
tu confirmas cada uno, la lista solo reduce donde mirar primero.

Para los duplicados, busca patrones de verdad antes de marcar:
```bash
grep -rn "<el patron sospechoso>" src/ --include="*.js" | grep -v test
```

### Paso 7 - Verificar y entregar

```bash
python3 build.py --extract    # regeneracion limpia desde cero
```

**7a - Los datos.** Comprueba y reporta:
- [ ] Curacion huerfana: **0**
- [ ] Nodos sin descripcion propia: los que sean, dilo con su numero
- [ ] Violaciones (si estan activas): ¿señal real o transversal sin marcar?
- [ ] Aristas descartadas: si el build avisa, ¿por que? Un descarte mudo hace
      que un grafo incompleto parezca completo.

**7b - Lo que se VE.** No basta con "el visor abre y el JS no da error".

<CRITICAL>
Ese check pasa aunque el visor este roto. Comprobado: en un corpus real paso
limpio mientras el panel mostraba la narrativa de OTRO proyecto, faltaban 10
de 18 carriles, y los iconos de la leyenda se estiraban hasta tapar su texto.
Ninguna verificacion de datos caza un fallo de presentacion.
</CRITICAL>

Abre el visor de verdad y recorre CADA superficie que renderiza texto o
iconos — leyenda, panel de introduccion, rotulos de carril, tarjeta de nodo:

- [ ] **Nada del dominio esta escrito en la plantilla.** Todo rotulo visible
      sale de `meta:`. Si lees una palabra que pertenece a OTRO proyecto (o al
      caso que origino la plantilla), es un texto fosilizado: sacalo a `meta`.
- [ ] **El vocabulario es el de ESTE proyecto.** Si agrupaste por dominio, el
      visor no puede decir "capa". Sale de `meta.grupo_label`.
- [ ] **Carriles declarados == carriles dibujados.** Cuentalos. Un filtro
      demasiado estrecho los tira en silencio y sus nodos quedan sin sitio.
- [ ] **Solo se muestra lo que este grafo usa.** Sin regla de dependencia, la
      leyenda no debe ofrecer "violacion"; sin fallas marcadas, no debe
      listarlas.
- [ ] **Ningun selector CSS de elemento suelto** (`svg{}`, `div{}`, `circle{}`).
      Una regla global pensada para el lienzo alcanza tambien a los iconos
      inline y los deforma — y el CSS gana a los atributos `width`/`height`.
      Acotalos con id o clase.
- [ ] **Nada se sale de su caja** con los textos reales del proyecto, que son
      mas largos que los del ejemplo.

Arregla en la PLANTILLA, no en el `index.html` generado: el build lo pisa.

**7c - El humano.** Abre el visor y pasa la pelota: **el resultado lo valida el.**
Preguntale por lo que ve, no por los numeros. En el caso que origino este
apartado, los tres fallos visuales los encontro el humano mirando la pantalla,
despues de que toda la verificacion automatica saliera en verde.

### Paso 8 - Mantener: re-verificar antes de cerrar la sesion (si paso tiempo o hubo cambios)

<IMPORTANT>
El grafo no se corrompe por edad: se corrompe porque el codigo debajo de el
sigue moviendose mientras curas. Un estudio sobre 1000 repositorios de GitHub
encontro que mas de una cuarta parte (28.9%) tenia documentacion con al menos
una referencia a codigo que ya no existia — y el patron confirmado es que el
mismo commit que cambia el codigo es el que deja la documentacion mintiendo,
sin ningun aviso hasta que algo la revisa explicitamente (Tan, Wagner & Treude,
2023, "Wait, wasn't that code here before?"). El Paso 7 verifica el grafo
recien construido; este paso verifica el mismo grafo despues de que paso
tiempo real — varias iteraciones de curacion, o cualquier cambio de codigo
en paralelo.
</IMPORTANT>

**Antes de cerrar la sesion de curacion** (no tras cada archivo — al final del
bloque de trabajo, igual que el Paso 5 valida por lotes de 15-20):

```bash
python3 build.py --extract    # vuelve a leer el codigo real, no lo cacheado
```

- [ ] **Curacion huerfana sigue en 0.** Si subio desde el ultimo Paso 7, algo
      del codigo cambio bajo un nodo ya curado — no es un bug nuevo del build,
      es la senal de que toca revisar esos nodos, no solo silenciar el aviso.
- [ ] **Si trabajaste en la MISMA sesion en la que tocaste codigo del
      subsistema graficado**, corre esto ANTES de dar la curacion por cerrada,
      no en la siguiente sesion — es el punto de intervencion mas barato,
      igual que el aviso de DOCER llega en el propio pull request y no despues
      de fusionarlo.
- [ ] **Si el humano no va a volver pronto**, dejalo dicho en el propio
      `curation.yaml` o en el resumen de cierre: que subsistema quedo curado y
      contra que commit — para que la proxima sesion sepa si hace falta repetir
      este paso antes de confiar en el grafo.

Este paso no sustituye al Paso 7: 7 verifica que el grafo nuevo es correcto;
8 verifica que un grafo que ya diste por bueno sigue siendolo.

## Errores que este skill existe para evitar

Todos ocurrieron de verdad construyendo el grafo que lo origino:

| Error | Que produjo | El paso que lo evita |
|---|---|---|
| Derivar descripciones del nombre | Tautologias con apariencia de doc | Paso 5.1 |
| Infraestructura marcada como grupo | 112 falsos positivos de 112 | Paso 1.4 |
| Claves de curacion inventadas | ~15 nodos apuntando a nada | El aviso de huerfana |
| Contar herencia como descripcion | 100% reportado con 547 huecos | Paso 7 |
| Detectar fallas por palabra clave | Nodos que salen del filtro en silencio | Paso 6 |
| Curar antes de agrupar | Rehacer las violaciones enteras | El orden de los pasos |
| Asumir capas donde hay composicion | Alarmas que no significan nada | Paso 1.2 y 1.3 |
| Texto del dominio dentro de la plantilla | El visor de un proyecto contaba la historia de otro proyecto distinto | Paso 7b |
| Verificar solo datos, nunca lo que se ve | Tres fallos visuales con toda la verificacion en verde | Paso 7b |
| Un selector CSS de elemento sin acotar | Los iconos de la leyenda tapando su propio texto | Paso 7b |
| Dar el grafo por bueno y no volver a mirarlo aunque el codigo siguiera cambiando | Curacion que mentia en silencio sin que ningun aviso lo marcara | Paso 8 |

## Corpus sin codigo (PDFs, Markdown, JSON de investigacion)

<IMPORTANT>
El principio del skill (estructura automatizable + significado leido a mano)
es agnostico al tipo de producto. La capa de extraccion NO — un PDF no tiene
AST. Para corpus sin codigo fuente, `build.py` tiene un segundo modo:
`EXTRACT_MODE = 'docs'` en vez de `'code'`.
</IMPORTANT>

En modo `docs`, la extraccion sale de referencias YA ESCRITAS en el corpus,
nunca inferidas por similitud semantica (inferir seria alucinar relaciones —
la misma razon por la que el Paso 5 prohibe derivar del nombre):

- **Markdown**: nodo por archivo (+ nodo por heading `##` si hay varios).
  Arista por wikilink `[[id]]` o link relativo `[texto](otro.md)`.
- **JSON de registro** (ej. una lista de fuentes/citas con `id`): nodo por
  entrada. Arista por el primer campo de lista que declare una relacion
  (`relevancia_hueco`, `relacionado_con`, `cita_a`, `refs`).
- **PDF**: nodo por archivo, sin estructura interna — es un nodo hoja para
  curar (`what`/`why`) igual que cualquier simbolo sin AST propio.

Si el corpus no tiene referencias explicitas entre documentos, el grafo sale
con nodos sueltos y cero aristas: sigue sirviendo para CURAR (una tarjeta por
documento) pero no da blast-radius. Eso es correcto, no un bug — no hay nada
que inferir sin alucinar.

Los pasos 4-7 (curar, marcar fallas, verificar) no cambian: `curation.yaml`
sigue funcionando igual, solo que la clave es `archivo.pdf` o
`registro.json::N2-047` en vez de `archivo.js::simbolo`.

## Que NO cubre este skill

- **Repos enteros.** Esta probado en subsistemas (~900 nodos de 3.500). Un
  monorepo completo es otro problema y no esta resuelto.
- **Mantener el grafo vivo.** Regenera la estructura, pero si el codigo (o el
  corpus) cambia, la curacion hay que revisarla a mano. El aviso de huerfana
  ayuda, no resuelve.
- **Imports dinamicos.** `require(variable)` o `import()` en runtime no los ve
  el AST. Si sospechas dispatch dinamico, verifica a mano.
- **Relaciones inferidas por significado, en cualquier modo.** Ni en `code`
  (el AST no adivina un import dinamico) ni en `docs` (el extractor no adivina
  que dos papers "se parecen" sin un link explicito). Si la relacion no esta
  escrita, no se dibuja — se cura a mano o se deja sin conectar.
