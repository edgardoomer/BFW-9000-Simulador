"""Datos del autor y versionado de estaticos, para todas las plantillas."""
from pathlib import Path

from django.conf import settings

_ESTATICOS = Path(settings.BASE_DIR) / "core" / "static" / "core"
_VERSION_FIJA = None


def _calcular_version() -> int:
    """Marca de tiempo del archivo estatico modificado mas recientemente."""
    try:
        return int(max(p.stat().st_mtime for p in _ESTATICOS.rglob("*") if p.is_file()))
    except (ValueError, OSError):
        return 0


def assets(request):
    """Sufijo ?v= para el CSS y el JS.

    Sin esto el navegador se queda con la copia en cache y los cambios en los
    graficos no se ven hasta forzar una recarga dura. En desarrollo se
    recalcula en cada peticion; en produccion se resuelve una sola vez.
    """
    global _VERSION_FIJA
    if settings.DEBUG:
        return {"ASSET_V": _calcular_version()}
    if _VERSION_FIJA is None:
        _VERSION_FIJA = _calcular_version()
    return {"ASSET_V": _VERSION_FIJA}

PERFIL = {
    "nombre": "Edgar Fernando Izurieta Merchán",
    "titular": "Ingeniero en Petróleos · Especialista en Datos e Inteligencia Artificial",
    "subtitular": "Aspirante a Ingeniero de Reservorios · Creador de contenido",
    "resumen": (
        "Ingeniero en Petróleos enfocado en la intersección entre ingeniería de "
        "reservorios, producción e inteligencia artificial en modelos de "
        "recuperación mejorada, automatización de procesos y análisis de Big Data."
    ),
    "idiomas": [
        ("Español", "Nativo"),
        ("Inglés", "Fluido"),
        ("Ruso", "Fluido"),
    ],
    "redes": [
        {
            "nombre": "LinkedIn",
            "usuario": "in/edgarfer",
            "url": "https://www.linkedin.com/in/edgarfer/",
            "icono": "in",
        },
        {
            "nombre": "Instagram",
            "usuario": "@doom.petrolero",
            "url": "https://www.instagram.com/doom.petrolero?igsh=eWRwamYxMzlsb255&utm_source=qr",
            "icono": "ig",
        },
    ],
    "proyectos": [
        {
            "titulo": "Automatización de toma de decisiones con LLM para proyectos "
                      "de recuperación mejorada",
            "detalle": "Python y Eclipse 300",
            "stack": ["LangChain", "TensorFlow", "dlisio", "MATLAB", "pandas"],
        },
        {
            "titulo": "Cuantificación de ratas y ppm de polímeros y trazadores "
                      "por el método ALP",
            "detalle": "Cálculo y validación de dosificación en campo",
            "stack": ["Excel", "pandas", "numpy", "MATLAB"],
        },
        {
            "titulo": "Chatbot con inteligencia artificial para la consulta de "
                      "400 páginas de documentos técnicos",
            "detalle": "Recuperación aumentada sobre normativa y manuales",
            "stack": ["LangChain", "OpenAI"],
        },
        {
            "titulo": "Análisis de data de HPS",
            "detalle": "Diagnóstico de bombas hidráulicas de subsuelo",
            "stack": ["SQLite", "PostgreSQL", "numpy", "pandas"],
        },
    ],
    "publicaciones": [
        {
            "tipo": "Artículo científico",
            "titulo": "Caso de estudio de Culebra 21: el manejo emergente de 16 000 BFPD",
        },
        {
            "tipo": "Ponencia · Congreso SPE-ESPOCH",
            "titulo": "Sistema multi-agente basado en inteligencia artificial para la "
                      "operación total de una estación de deshidratación de petróleo",
        },
    ],
    # Coloque su fotografia en core/static/core/img/perfil.jpg para reemplazar
    # el marcador de posicion.
    "foto": "core/img/perfil.jpg",
    "cv_url": "https://www.linkedin.com/in/edgarfer/",
}


def perfil(request):
    return {"perfil": PERFIL}
