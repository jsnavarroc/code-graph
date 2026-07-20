# Paso 5 — Curar el significado

Curar = leer la unidad completa y escribir lo que significa. Es la mitad del
grafo que el AST no puede dar, y la que determina si el grafo ahorra contexto
o lo malgasta.

---

## La regla que gobierna todo

<CRITICAL>
Si no has leido la unidad completa, el nodo se queda sin describir.

Derivar del nombre produce texto que PARECE documentacion y no dice nada:
  `setIsLoading` -> "Escribe is loading en el estado"   ← inutil
Eso es repetir el nombre con mas palabras. Ensucia el grafo y da falsa
sensacion de cobertura.
</CRITICAL>

---

## Los campos

| Campo | Responde | ¿Sale del AST? |
|---|---|---|
| `character` | Que TIPO de cosa es | No |
| `what` | Que hace, en concreto | No |
| `why` | Que problema resuelve ← **el mas valioso** | Jamas |
| `ux` | Que ve o siente quien lo usa | Jamas |
| `when` | Cuando corre, quien lo dispara | Parcial |
| `if_broken` | Que se rompe si falla | No |

Ademas: `protected`, `gotchas`, `issue`, `cases` (ver "Los otros campos" mas
abajo) — no son parte del set principal pero se curan con la misma regla.

<CRITICAL>
Esta tabla es el set POR DEFECTO, no un catalogo cerrado. `what`/`why` cubren
la mayoria de los casos, pero no todos los proyectos necesitan lo mismo — un
subsistema con requisitos de cumplimiento normativo puede necesitar un campo
que registre bajo que regla existe cada pieza; uno con restricciones fisicas
(hardware, memoria, tiempo real) puede necesitar uno que registre el limite
exacto que impone la decision. Antes de curar el primer nodo, pregunta al
humano si el set por defecto alcanza o si falta algo — no lo decidas tu solo
ni asumas que what/why siempre bastan.
</CRITICAL>

**Pregunta (formato cerrado, antes del primer nodo — mismo patron que la
pregunta del `why`):**
> "Voy a curar cada nodo con `character`, `what`, `why`, `ux`, `when`,
> `if_broken` (mas `protected`/`gotchas`/`issue`/`cases` cuando aplique).
> ¿Este set cubre lo que este subsistema necesita, o falta algo especifico de
> tu dominio? Ejemplos de por que podria faltar algo:
>   a) **Cumplimiento/regulacion** — el nodo existe por una norma o requisito
>      externo auditable (ej.: 'bajo que articulo o politica existe esto')
>   b) **Restriccion fisica o de plataforma** — un limite numerico o de
>      entorno que el `why` no captura bien como prosa (ej.: 'el limite exacto
>      de memoria/latencia/hardware que esto respeta')
>   c) **Propiedad/dueño** — quien es responsable de este nodo cuando cambia,
>      si no es obvio por el repositorio (ej.: 'que equipo lo mantiene')
>   d) **Ninguno, el set por defecto alcanza** — el caso mas comun
> Si eliges (a), (b) o (c), dime el nombre del campo nuevo y anadelo a la
> tabla de este documento para el resto de la curacion — no lo definas nodo a
> nodo, decidelo una vez al principio."

Si el humano no tiene preferencia, sigue con el set por defecto — **(d)** es
la opcion mas comun y la unica sin coste adicional. No fuerces campos nuevos
sin que el humano los pida.

---

## `character` — que tipo de cosa es

<IMPORTANT>
El caracter determina las REGLAS de uso del artefacto. No es adorno: cada tipo
de cosa (un singleton, un objeto inmutable, un componente con ciclo de vida,
un proceso sin estado...) trae consigo restricciones propias de como se
instancia, se llama o se combina con otras.

Si el grafo no lo dice, quien lo consulta tiene que abrir la unidad para saber
como se usa la cosa — que es justo lo que el grafo deberia ahorrarle.
</IMPORTANT>

**El vocabulario sale del proyecto, no de un catalogo.** El nombre que usa ESTE
proyecto/dominio para un tipo de artefacto puede no coincidir con el nombre
generico que tu conoces. Lee la unidad (archivo, funcion, seccion, lo que sea
el nodo en este producto) y di lo que ES en el vocabulario que el propio
producto usa; si el termino no lo reconoces, buscalo; si sigue sin estar claro,
pregunta al humano.

<IMPORTANT>
Busca en la web ANTES de preguntar al humano, no en vez de leer la unidad
completa. Mismo principio que el Paso 1.2 (agrupacion): tu conocimiento previo
del dominio tiene huecos, y una busqueda rapida contra la fuente autoritativa
del ecosistema (el framework, el estandar, la convencion del campo) evita
adivinar mal el `character` o forzar un `why` generico. Util cuando:
- Reconoces un patron a medias pero no ubicas el nombre exacto que su
  ecosistema usa para el — busca la terminologia oficial antes de inventar tu
  propio termino aproximado.
- La unidad pertenece a un ecosistema con vocabulario propio y tecnico —
  confirma el termino EXACTO que usa esa comunidad, no un sinonimo.
- Un numero, constante o umbral "con historia" (ver seccion "Que buscar al
  leer" mas abajo) podria coincidir con un limite conocido y documentado del
  entorno donde corre/vive esta unidad — buscar confirma si es una decision
  propia del proyecto o un limite externo heredado, lo cual cambia por
  completo el `why` que corresponde escribir.

La query de busqueda se construye con lo que YA viste en el nodo real que estas
curando (el termino exacto, el nombre del framework/estandar que declara el
propio proyecto, el numero exacto) — nunca con un ejemplo de otro proyecto.

**La busqueda informa, no reemplaza la lectura.** Si la busqueda contradice lo
que la unidad realmente hace (el proyecto usa el patron "a su manera"), manda
lo que hay — igual que en el Paso 1.2, lo local manda sobre lo publicado. Y si
tras buscar sigue sin estar claro, pregunta al humano en vez de adivinar: una
pregunta cerrada con lo que encontraste ("Veo que esto usa <patron detectado>,
segun <fuente> significa <X> — ¿es asi aqui, o se usa distinto?") cuesta menos
que una descripcion mal curada que hay que deshacer despues.
</IMPORTANT>

---

## El `why` no tiene un formato fijo — pregunta al humano CUÁL es el criterio antes de curar el primer nodo

<CRITICAL>
"Que problema resuelve" no significa lo mismo en todos los proyectos ni para
todos los equipos. Un `why` generico ("gestiona el estado", "procesa la
peticion") es tan inutil como derivarlo del nombre — es la misma tautologia de
la regla que gobierna todo, solo que mas larga. Antes de escribir el primer
`why` del subsistema, pregunta al humano bajo que criterio quiere que se
defina, con opciones concretas y un ejemplo para cada una — no le pidas que
lo defina el desde cero.
</CRITICAL>

**Pregunta (formato cerrado, con ejemplos — nunca "¿como quieres el why?"
abierta):**
> "Para el `why` de cada nodo, ¿cual de estos criterios prefieres? Puedo
> combinar mas de uno si aplica:
>   a) **Decision de diseño** — por que se construyo asi y no de otra forma
>      (ej.: 'usa X en vez de Y porque Z falla bajo esta condicion')
>   b) **Restriccion externa** — un limite del entorno/plataforma que obligo
>      esta solucion (ej.: 'el limite de <el entorno> obliga a este workaround')
>   c) **Historia/incidente** — nace de un problema real que paso antes
>      (ej.: 'se añadio tras el caso donde <lo que fallo>')
>   d) **Consecuencia si falla** — que se rompe en la practica si esto deja
>      de funcionar (ej.: 'sin esto, <el efecto observable para quien lo usa>')
> ¿Cual(es) quieres que priorice, o hay otro criterio que uses en este equipo?"

Si el humano no tiene una preferencia clara, ofrece **(d) consecuencia si
falla** como la mas obvia por defecto — es la mas facil de verificar (se puede
probar rompiendo la unidad y observando que pasa) y la que mas rinde para
alguien que llega sin contexto al subsistema.

Una vez el humano fija el criterio, cada `why` que escribas debe ser
verificable contra ESE criterio — no una mezcla ambigua de los cuatro sin que
quede claro cual se esta aplicando en cada nodo.

**Formato de ejemplo (los nombres son ilustrativos, sustituyelos por los
reales del proyecto que estes curando):**
```yaml
modulo/ClaseSingleton.ext:
  character: singleton
modulo/utilidades/funcionReactiva.ext:
  character: <tipo real segun el ecosistema del proyecto>
modulo/estado/valorDerivado.ext:
  character: <tipo real segun el ecosistema del proyecto>
plataforma/ComponenteNativo.ext:
  character: <tipo real segun el ecosistema del proyecto>
```

**Escribelo especifico.** "funcion" no aporta nada — se ve en el label. "funcion
pura sin estado, reutilizable" si: dice como se puede usar.

<CRITICAL>
El caracter NO se hereda. Nunca. Cada simbolo declara el suyo o se queda sin el.

Una funcion auxiliar de logging que vive dentro de un archivo que exporta una
clase singleton NO hereda "singleton" solo por vivir ahi — seria mentira. Si es
una funcion, es una funcion.

La diferencia con los otros campos: el `what` heredado da CONTEXTO ("esto vive
en el modulo que hace X"), lo cual es un hecho. El caracter heredado AFIRMA que
la cosa es algo que no es. Uno situa, el otro miente.

Unica excepcion: cuando archivo y simbolo se colapsan. Ahi no hay herencia sino
fusion — son la misma cosa, comparten caracter por definicion.
</CRITICAL>

**Ojo con la redundancia:** si el proyecto agrupa POR tipo de artefacto (una
carpeta por cada tipo de componente), el `character` y el grupo dicen casi lo
mismo. Ahi el caracter debe aportar el matiz que el grupo no da: no basta con
repetir el tipo, hay que decir la restriccion especifica de uso (ej. "solo
valido dentro de X contexto").

**Y el caracter decide el colapso:** un archivo con UN caracter (una sola
entidad exportada) se colapsa con su simbolo homonimo. Un archivo con DOS APIs
de distinto caracter (ej. una clase Y una funcion independiente, con
consumidores distintos) son nodos separados.

`why` y `ux` son los que justifican el trabajo. `what` sin `why` es un
comentario glorificado.

**El `ux` decide si un cambio merece la pena.** Escribelo en terminos de lo que
experimenta quien usa el producto final, no de codigo/implementacion. Si el
nodo no tiene efecto directamente observable, dilo: "Invisible: es
infraestructura interna. Si falla, <el efecto indirecto que sí se nota>."

---

## Que es una buena descripcion

**Malo** (deducido, sin leer):
> "Logica de validacion y avance de un flujo."

**Bueno** (tras leer la unidad completa):
> **what**: Gobierna el avance de un formulario multi-paso. Reparte el foco
> entre los campos, abre el input correspondiente una sola vez por visita,
> valida al confirmar.
>
> **why**: Este flujo tiene DOS capas de estado que deben coordinarse: el
> contenedor recibe la interaccion primero, y solo entonces se habilita el
> campo interno. Esta funcion coordina esas dos capas, y de ahi salen sus dos
> guardas. Una de ellas evita que el campo se re-active mas de una vez por
> visita: sin ella, cada vez que el foco regresara al contenedor —por ejemplo
> al volver de una accion de retroceso— el campo se activaria de nuevo encima
> del usuario sin que lo pidiera.
>
> **ux**: El usuario llega al campo y este se activa solo, una vez. Al volver
> de otra pantalla, no se le activa de nuevo sin que lo pida.

La diferencia: la segunda explica **por que esto es asi y no de otra forma**.
Eso no esta en ningun sitio salvo en la unidad misma.

---

## Que buscar al leer

Lo que hace valioso un nodo casi siempre es una de estas cinco:

1. **Numeros con historia.** Un timeout, un limite de reintentos, un umbral
   especifico. Nunca son arbitrarios: alguien los ajusto peleando con un
   problema real. Averigua contra que.
   > "60 reintentos frente a los 10 por defecto: el flujo mas largo del
   > sistema encadena cuatro esperas seguidas, y con 10 se agotaba el limite
   > antes de que la operacion terminara."

2. **Guardas que parecen defensivas y no lo son.**
   > "Las tres condiciones son OBLIGATORIAS, no redundantes: el evento que
   > dispara esto es de difusion general (le llega a todos los oyentes), asi
   > que sin la condicion que filtra por identidad, cualquier oyente
   > procesaria el evento aunque no le correspondiera."

3. **Codigo comentado o vaciado.** Es un hallazgo, no basura. Alguien lo apago
   por una razon y esa razon suele explicar un comportamiento raro de hoy.

4. **Comentarios del autor.** Cuando el codigo explica su propio porque, esa es
   la mejor fuente que hay. Citalo.

5. **Diferencias por plataforma/entorno.** Casi siempre esconden un limite
   real del entorno donde corre, no un descuido.

---

## Los otros campos

**`protected`** — el nodo no se toca sin coordinar (ej: referencia a un
ticket/PR que explica por que esta congelado).

**`gotchas`** — lo que rompe si lo tocas mal. Uno por linea, concreto.
Si detectas logica duplicada, dilo aqui con los sitios donde esta:
> "DUPLICADO: la misma comprobacion de estado esta implementada en tres
> sitios distintos, con tiempos de espera diferentes cada uno (100ms, 250ms,
> inmediato). Un fix en uno NO llega a los otros dos."

**`issue`** — `bug` | `muerto` | `duplicado`. A mano, leyendo el nodo. Ver Paso 6.

**`cases`** — casos documentados que tocan este nodo.

---

## Herencia archivo -> simbolo

El simbolo homonimo de su archivo (la funcion/clase principal que el archivo
exporta como `export default` o equivalente) hereda su curacion: curar los dos
seria duplicar.

Los demas simbolos del archivo NO heredan `what` propio — muestran el contexto
del modulo, que es un hecho verificado, no una invencion.

<IMPORTANT>
Al contar cobertura, herencia != descripcion propia. Contarlas juntas reporta
100% cuando falta la mitad del trabajo. Caso real: un contador reporto 100%
de cobertura mientras 547 nodos (mas de la mitad del subsistema) solo tenian
el contexto heredado del archivo, sin `what` propio.
</IMPORTANT>

---

## El ritmo

Unidad por unidad, empezando por las de mas impacto (mayor `in_degree`, o mayor
centralidad si el grafo la calcula).

<IMPORTANT>
La centralidad es el punto de partida, no el ranking final. Un archivo muy
central pero sin actividad de desarrollo reciente puede pesar menos que uno
con centralidad media que se toco la semana pasada — un estudio industrial
real (3 productos, 10 practicantes) encontro que los profesionales SIEMPRE
combinaban la señal estructural con contexto (actividad reciente, rol
arquitectonico) antes de decidir; nunca trataron la centralidad como una
respuesta automatica. Si tienes acceso al historial del repo (`git log
--since` sobre los archivos del subsistema), usalo para ajustar el orden que
propone `in_degree` — y sigue siendo una PROPUESTA a confirmar con el humano,
no una decision tuya sola.
</IMPORTANT>

**Antes de curar el primer nodo de cada bloque de 15-20, repasa la lista
completa del bloque una vez** (que hace cada uno, en una frase) antes de
empezar a escribir la curacion del primero. No es redundante: procesar una
lista larga en orden secuencial sesga hacia curar mejor los primeros items de
la lista y peor los ultimos — el mismo efecto esta documentado en modelos de
lenguaje procesando listas largas, y se mitiga (no se elimina del todo)
pidiendo explicitamente considerar todas las opciones antes de decidir. Este
repaso previo es esa mitigacion.

Cada 15-20 unidades:

1. `python3 build.py`
2. Corrige la curacion huerfana si la hay
3. Ensena 2-3 descripciones al humano y pregunta si el nivel esta bien

Ese ultimo paso es el que salva el trabajo. Detectar tarde que el criterio de
curacion esta flojo (a mitad de un subsistema grande) cuesta horas de
correccion retroactiva; detectarlo en las primeras 20-50 unidades cuesta
minutos.
