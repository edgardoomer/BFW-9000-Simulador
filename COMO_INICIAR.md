# Cómo iniciar BFW-9000

Dos formas. La primera es la del día a día; la segunda sirve para llevarse el
proyecto a otra máquina sin instalar nada.

---

## 1. Con el acceso directo (recomendado)

La primera vez, doble clic en:

**`Crear acceso directo.bat`**

Eso genera el icono a partir de `logo.png` y deja un **BFW-9000** en el
Escritorio. Desde ahí, doble clic y listo: prepara la base, enciende el
servidor y abre el navegador solo.

Puede arrastrar el acceso directo a la barra de tareas o al menú Inicio.

Para apagarlo: **`Detener BFW-9000.bat`**. Cierra únicamente el proceso que
escucha en el puerto 8017, no todo Python.

### Qué hace el lanzador

1. Si no hay entorno virtual, lo crea e instala las dependencias.
2. Si el servidor ya estaba encendido, sólo abre el navegador.
3. Aplica las migraciones pendientes.
4. Si la base está vacía, carga los dos proyectos de ejemplo.
5. Levanta el servidor en una ventana aparte, minimizada.
6. Espera a que responda de verdad y recién ahí abre el navegador.

Nada de esto pisa datos existentes: los ejemplos se cargan sólo si no hay
ningún proyecto.

---

## 2. Con Docker

Para copiar la carpeta a otra máquina y que funcione sin instalar Python ni
dependencias. Requiere **Docker Desktop** encendido.

**`Iniciar BFW-9000 (Docker).bat`** — construye la imagen la primera vez
(varios minutos) y después arranca en segundos.

**`Detener BFW-9000 (Docker).bat`** — apaga el contenedor.

### Dónde quedan los datos

En la carpeta **`datos\`**, junto al proyecto. Está montada como volumen, así
que:

- Sobrevive a reconstruir la imagen.
- Si copia la carpeta del proyecto a otra máquina, **se lleva sus proyectos
  con ella**.

### La llave de la API

No se hornea en la imagen: `.env` está en `.dockerignore` a propósito. Docker
Compose lee el `.env` de la carpeta y la inyecta al arrancar el contenedor. Si
falta el archivo, el simulador arranca igual y el análisis económico usa el
precio de respaldo.

---

> **No use las dos formas a la vez.** Ambas ocupan el puerto 8017 y son bases
> de datos distintas: la nativa usa `db.sqlite3` en la raíz y la de Docker usa
> `datos\db.sqlite3`. Apague una antes de encender la otra, o no verá los
> mismos proyectos.

---

## Si algo falla

**«Python no se reconoce»** — instale Python 3.11 o superior desde
<https://www.python.org/downloads/> marcando *Add Python to PATH*.

**«Docker no responde»** — abra Docker Desktop y espere a que el icono de la
ballena deje de animarse.

**El puerto 8017 está ocupado** — ejecute `Detener BFW-9000.bat`, o cambie
`PUERTO` en el `.bat` y el mapeo en `docker-compose.yml`.

**La página no refleja un cambio en el código** — los estáticos llevan
versión automática, así que basta recargar. Si tocó un archivo `.py`, reinicie
el servidor.

**El icono se ve mal** — `logo.png` es rectangular (236×183) y el generador lo
cuadra sobre su propio color de fondo. Si prefiere control total, reemplácelo
por un PNG cuadrado y vuelva a correr `Crear acceso directo.bat`.

---

## Arranque manual

Si prefiere la terminal:

```bash
.venv/Scripts/python.exe manage.py runserver 8017
```
