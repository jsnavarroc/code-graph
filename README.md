# code-graph

Skill de Claude para construir un **grafo de código híbrido**: la estructura
(quién llama a quién, cuántos dependen) sale del AST de forma automática y
fiable; el significado (por qué existe algo, qué se rompe si falla, qué race
condition esconde) lo lee y escribe un humano. El skill hace las dos mitades
y las mantiene separadas — nunca deja que una se haga pasar por la otra.

## Por qué

Un grafo de solo-estructura puede consumir **más** contexto que no tener
grafo: un nodo con 60 aristas y sin descripción obliga a abrir 60 archivos
para entenderlo. Medido en código real, un grafo curado usa ~1.000
tokens/consulta contra ~10.000 sin curar — 10x. Lo que ahorra contexto no es
el grafo en sí, es la densidad semántica de sus nodos.

De ahí la regla que gobierna todo el skill: **nunca derivar una descripción
del nombre del símbolo**. Si no se ha leído el archivo, el nodo se queda sin
describir. Sin excepciones.

## Qué hace

| Lo hace el script | Lo hace el agente leyendo | Lo decide el humano |
|---|---|---|
| Extraer AST | Leer cada archivo | Alcance: qué entra |
| Calcular impacto | Escribir `what`/`why`/`ux` | Por qué criterio se agrupa |
| Detectar huérfanos | Detectar duplicación | Si hay regla de dependencia |
| Generar el visor | Marcar fallas | Validar que no miente |

El resultado es un visor HTML autocontenido: tarjetas de nodo con
`character`/`what`/`why`/`ux`/`when`/`if_broken`, agrupadas en carriles según
el criterio de organización real del proyecto (no asume capas de dependencia
— puede ser Atomic Design, feature-sliced, por dominio, lo que corresponda),
con blast-radius calculado sobre el grafo completo.

## Los 8 pasos

1. **Planificar** con el humano — alcance, agrupación, regla de dependencia
   (opcional), transversal, ruido a excluir, e introducción del subsistema.
2. **Confirmar el modo** — `code` (hay AST vía tree-sitter) o `docs` (corpus
   sin código: Markdown, JSON de registro, PDF).
3. **Configurar y extraer** — corre `build.py --extract`.
4. **Curar los grupos** — asigna `layer` a cada archivo, rápido, antes del
   significado.
5. **Curar el significado** — el grueso: leer cada archivo entero y escribir
   sus campos. Se valida por bloques de 15-20 archivos.
6. **Marcar fallas** — `bug` / `muerto` / `duplicado`, a mano, nunca por
   palabra clave.
7. **Verificar** — los datos (curación huérfana, cobertura, violaciones) y lo
   que se VE (nada hardcodeado, carriles completos, CSS acotado).
8. **Mantener** — al cerrar la sesión, re-verificar que el código no se movió
   bajo nodos ya curados.

Cada paso existe porque un error real lo motivó — la lista completa está en
`SKILL.md`, sección "Errores que este skill existe para evitar".

## Modo `docs`

El principio (estructura automatizable + significado leído a mano) es
agnóstico al tipo de producto. Para corpus sin código fuente (una carpeta de
investigación, un registro de citas), `build.py` extrae nodos de Markdown,
JSON de registro o PDFs, y aristas solo de referencias ya escritas
explícitamente — nunca inferidas por similitud semántica.

## Qué NO cubre

- Repos enteros (probado en subsistemas de hasta ~900 nodos de 3.500).
- Mantener el grafo vivo automáticamente: la estructura se regenera, la
  curación hay que revisarla a mano cuando el código cambia.
- Imports dinámicos (`require(variable)`, `import()` en runtime).
- Relaciones inferidas por significado, en cualquier modo — si la relación
  no está escrita, no se dibuja.

## Estructura

```
SKILL.md                    # las instrucciones completas, paso a paso
references/
  planning.md                # detalle del Paso 1 (planificación)
  curation.md                 # detalle del Paso 5 (curación de significado)
scripts/
  build.py                    # extracción + build del grafo
  viewer-template.html        # plantilla del visor HTML autocontenido
```

## Uso

Este directorio es un [skill de Claude Code](https://docs.claude.com/claude-code/skills).
Colócalo en `~/.claude/skills/code-graph/` (o el directorio de skills del
proyecto) y se activa cuando la tarea coincide con su descripción — entender
un subsistema que no escribiste, mapear antes de refactorizar, o pedirlo
explícitamente ("grafo de código", "code graph").
