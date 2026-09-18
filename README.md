# Simulador Buckley-Leverett

El metodo de Buckley&Leverett es un importante porque provee de una idea general
del movimiento y desplazamiento de fluidos inmisibles en un medio poroso, para
determinar el tiempo de irrupción, breakthrou o llegada del agua inyectada al pozo
productor del cual se pretende dar tanto presión al reservorio objetivo como un 
desplazamiento del mismo.

La presente herramienta se basa:
- Django
- CSS
- Java
- Python
- .Web
- SQLite 

---

## Puesta en marcha

**Doble clic en `Iniciar BFW-9000.bat`.** Eso es todo.

El lanzador hace el resto: si no hay entorno virtual lo crea e instala las
dependencias, aplica las migraciones, carga los dos proyectos de ejemplo si la
base está vacía, enciende el servidor y abre el navegador recién cuando ya
responde. En una máquina limpia tarda alrededor de un minuto; después, segundos.

Para tener un icono en el Escritorio, la primera vez ejecute
**`Crear acceso directo.bat`**. Genera el icono a partir de `logo.png` y deja
un acceso directo que puede anclar a la barra de tareas.

Para apagar: **`Detener BFW-9000.bat`**. Cierra sólo el proceso que escucha en
el puerto 8017, no todo Python.

### Con Docker

Si prefiere no instalar Python, con **Docker Desktop** encendido:

| Archivo | Qué hace |
|---|---|
| `Iniciar BFW-9000 (Docker).bat` | Construye la imagen la primera vez y levanta el contenedor |
| `Detener BFW-9000 (Docker).bat` | Lo apaga |

La base queda en `datos\`, montada como volumen: sobrevive a reconstruir la
imagen y viaja con la carpeta.

> No use las dos formas a la vez. Ambas ocupan el puerto 8017 y son bases
> **distintas**: la nativa usa `db.sqlite3` en la raíz y la de Docker usa
> `datos\db.sqlite3`.

Detalle y solución de problemas en [COMO_INICIAR.md](COMO_INICIAR.md).

### Compartir el proyecto

**`Compartir proyecto.bat`** arma un ZIP de ~220 KB en el Escritorio, listo
para enviar. Quien lo reciba sólo descomprime y da doble clic al lanzador:
arranca con los dos proyectos de ejemplo y con el análisis económico en línea
funcionando, sin configurar nada.

| | |
|---|---|
| **Incluye** | el código, los lanzadores, Docker y `.env` con la llave de oilpriceapi |
| **No incluye** | `.venv` (45 MB, propio de cada máquina) ni la base de datos |

La llave viaja a propósito: es de plan gratuito y sólo devuelve una cotización.
Para un par de personas no representa problema.

```bash
powershell -ExecutionPolicy Bypass -File herramientas\empaquetar.ps1 -SinLlave
```

Use `-SinLlave` si el paquete va a un sitio público (GitHub, Drive abierto):
entonces sólo viaja `.env.example` y la economía usa el precio de respaldo.
Agregue `-ConDatos` para incluir también sus propios proyectos.

### Configuración

Copie `.env.example` a `.env` y complete la llave de
[oilpriceapi.com](https://www.oilpriceapi.com):

```
OILPRICE_API_KEY=su-llave-aqui
```

`.env` está en `.gitignore` y en `.dockerignore`: la llave no se sube al
repositorio ni se hornea en la imagen. **Sin llave el simulador funciona
igual**; sólo el análisis económico usa el precio de respaldo
(`OILPRICE_FALLBACK`) en lugar de la cotización en línea.

> En equipos con inspección TLS corporativa, `truststore` delega la validación
> al almacén de certificados de Windows. Ya viene en `requirements.txt`.

### Arranque manual y administración

Si prefiere la terminal:

```bash
.venv/Scripts/python.exe manage.py runserver 8017
```

Para entrar al panel de administración en `/admin/`, cree un usuario:

```bash
.venv/Scripts/python.exe manage.py createsuperuser
```

---

## Las pestañas

| Pestaña | Qué hace |
|---|---|
| **Proyectos** | Base maestra: alta, edición y borrado de estudios. |
| **Estudio** | Entrada de datos y resultados en una sola pantalla. |
| **Cálculos por pozo** | Toda la cadena del método para un pozo, con datos ampliados. |
| **Economía** | Análisis de OPEX con precio de crudo en línea. |
| **Método** | El paso a paso con las fórmulas, en notación UnicodeMath. |
| **Contacto** | Créditos y redes. |

En **Estudio**, el gráfico y la barra de tiempo van a la izquierda y las fichas
de pozo a la derecha. Cada ficha se contrae al hacer clic en su título y se
puede arrastrar para acomodarlas una al lado de otra. Todo se guarda solo.

---

## El modelo

### Buckley-Leverett clásico

1. Ajuste `kro/krw = a·e^(−b·Sw)` por mínimos cuadrados sobre `ln(kro/krw)`.
2. Flujo fraccional `fw = 1/(1 + (μw/μo)·a·e^(−b·Sw))`.
3. Derivada analítica `dfw/dSw = b·fw·(1 − fw)`.
4. Frente de choque por la condición de Rankine-Hugoniot:

   ```
   (dfw/dSw)|Swf = [fw(Swf) − fw(Swi)] / (Swf − Swi)
   ```

   Se resuelve **maximizando la cuerda**, que es equivalente a la tangencia y
   evita la ambigüedad de las dos raíces que tiene la ecuación de tangencia con
   el modelo exponencial.

   El texto clásico dibuja la tangente desde `(Swi, 0)` porque `krw(Swc) = 0`
   hace `fw(Swi) = 0`. El ajuste exponencial no puede representar `krw → 0` y
   deja un `fw(Swi)` pequeño pero no nulo, así que se usa la forma general;
   cuando `fw(Swi) → 0` se recupera el caso del libro.

### Frente areal con brazos

El caudal de cada inyector se reparte entre azimuts con una densidad angular
`w(θ)`: un fondo constante, que da el cuerpo redondeado, más una campana de
Gauss por cada productor conectado, con amplitud proporcional a la
transmisibilidad del canal `T = k·h/ln(L/rw)`. Ésas son los brazos.

El balance volumétrico por sector angular cierra el problema:

```
r(θ, t) = √( 2 · 5.6146 · q · t · w(θ) / (W · φ · h · ΔSw) )
t_BT,j  = ( L_j / r(θ_j, t=1) )²
```

El frente avanza con la **raíz del tiempo**, como corresponde a un flujo radial.
Consecuencia práctica: un canal de 100 md contra uno de 10 md lleva el agua unas
**3.2 veces más lejos**, pero irrumpe unas **10 veces antes**. Si un productor
recibe agua de varios inyectores, la irrupción es la primera llegada de todas.

### Economía

El corte de agua de cada pozo sale de la misma solución: antes de la irrupción
es el corte base; después lo dicta Welge, con `Wi = 1/(dfw/dSw)|Sw2`. El pozo
al que el agua llega primero es también el primero que encarece el barril.

El líquido total lo fijan los caudales de los pozos y **nunca se reescala**:
reescalarlo rompería el balance con el agua inyectada. El caudal de petróleo y
el corte de agua son dos formas de decir lo mismo, y el campo *Base del perfil*
elige cuál de los dos manda.

---

## Base de datos

```
Proyecto  ─┬─ Pozo ─────┬─ ResultadoPozo        (cache de los cálculos)
           │            └─ CurvaKr ── PuntoKr   (krw / kro vs Sw)
           ├─ ParInyeccion                      (inyector → productor)
           └─ ParametrosEconomicos

PrecioCrudo                                     (histórico de la API)
```

`ParInyeccion` es la tabla que permite que un inyector alimente a varios
productores y que un productor reciba agua de varios inyectores. Su campo
`k_direccional` es lo que hace que el agua llegue antes a unos pozos que a otros.

Los pozos heredan del proyecto cualquier propiedad que dejen vacía, de modo que
un proyecto recién creado se puede calcular de inmediato.

### Unidades

Las coordenadas se guardan tal como se cargan y el campo *Unidad de las
coordenadas* del proyecto dice si vienen en pies o en metros UTM. Toda la física
trabaja internamente en pies. El resto es unidad de campo: md, cp, psi, BPD, USD.

---

## Los dos ejemplos

**BL-2026-001 · Yuturi Este** — dos inyectores y cinco productores, coordenadas
en metros UTM. I-1 alimenta a cuatro productores y I-2 a tres; P-3 y P-4 reciben
agua de ambos. P-4 irrumpe desde I-2 aunque I-1 esté más cerca, porque su canal
es mejor (140 md contra 95 md).

| # | Pozo | L (ft) | k (md) | tBT (días) | Desde |
|---|---|---|---|---|---|
| 1 | YUT-A-008 | 2499 | 420 | 617 | I-1 |
| 2 | YUT-B-004 | 2715 | 310 | 733 | I-2 |
| 3 | YUT-A-017 | 2832 | 140 | 1447 | I-2 |
| 4 | YUT-A-014 | 2870 | 180 | 1519 | I-1 |
| 5 | YUT-A-021 | 2690 | 35 | 2821 | I-1 |

**BL-2026-002 · Sacha Sur** — un inyector y seis productores, coordenadas en
pies. La permeabilidad direccional va de 9 md a 430 md y el agua llega a cada
pozo en un momento distinto. P-201 y P-206 comparten canales igual de buenos y
se separan sólo por la distancia: es el par que muestra el efecto puro de `L²`.

| # | Pozo | L (ft) | k (md) | tBT (días) | años |
|---|---|---|---|---|---|
| 1 | SAC-A-201 | 1540 | 420 | 299 | 0.8 |
| 2 | SAC-A-206 | 2127 | 430 | 589 | 1.6 |
| 3 | SAC-A-203 | 2363 | 290 | 984 | 2.7 |
| 4 | SAC-A-204 | 2062 | 78 | 1599 | 4.4 |
| 5 | SAC-A-202 | 2890 | 120 | 2513 | 6.9 |
| 6 | SAC-A-205 | 2290 | 9 | 3192 | 8.7 |

Los resultados son **reproducibles**: la rugosidad del contorno se siembra con
el código del pozo, no con su clave primaria, así que recargar los ejemplos
devuelve exactamente los mismos números.

---

## Estructura

```
Iniciar BFW-9000.bat       lanzador nativo (crea el entorno si falta)
Crear acceso directo.bat   icono en el Escritorio
Compartir proyecto.bat     arma el ZIP limpio para enviar
Dockerfile                 imagen del contenedor
docker-compose.yml         puerto, volumen de datos y variables
herramientas/
  crear_icono.py           logo.png -> .ico multi-resolución
  empaquetar.ps1           empaquetado sin .venv ni llaves
blsim/           configuración de Django
core/
  models.py      seis tablas y configuraciones
  bl.py          solucion de Buckley-Leverett
  flood.py       geometría areal y animacipón
  engine.py      motor modelo → soluciones → JSON para graficar
  economics.py   perfil de producción y flujo de caja
  oilprice.py    cliente REST con caché y respaldo
  seeds.py       dos ejemplos predeterminados y de ejemplo
  views.py       páginas y API JSON
  static/core/js  chart.js
                  mapa.js
                  estudio.js
                  calculos.js
                  economia.js
  templates/core plantillas
```

---

## Limitaciones

Conviene tenerlas presentes antes de llevar un resultado a una reunión:

- Limitaciones base de acuerdo a la teoría:
    - Flujo lineal
    - Medio homogeneo
    - Fluido incompresibles
    - Fluidos inmiscibles
    - Balance de materia estable.
- El repato del flujo en el grafico es didactico y visualmente agradable, 
  no tiene una referencia a una simulacion netamente numérica, obedence a la ecuación del metodo
  de buckley&Leverett.
- La simulación funciona solo por reservorio o estrato, un mismo pozo inyector influencia otros reservorios,
  es necesario realizar otras simulaciones.
- El perfil económico responde a valores predeterminados que es posible cambiar. Los valores son tipicos o promedio,
  teniendo en cuenta al ultimo valor del precio de petroleo registrado. La simulación del mismo responde al metodo propuesto

## Desarrollo

Autor: **Ing. Edgar Fernando Izurieta Merchán**. El planteamiento del modelo de
Buckley-Leverett, los supuestos del frente areal, los criterios económicos y los
datos de entrada son propios.

La implementación del código se hizo con asistencia de **Claude (Anthropic)**,
usado como herramienta de apoyo en la escritura y revisión. La responsabilidad
sobre el contenido técnico y los resultados es del autor.

---

Edgar Fernando Izurieta Merchán · Ingeniero en Petróleos - Especialista de IA y Datos para la industria petrolera
[LinkedIn](https://www.linkedin.com/in/edgarfer/) ·
[Instagram](https://www.instagram.com/doom.petrolero)
