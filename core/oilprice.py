"""Cliente REST de oilpriceapi.com con cache y respaldo.

La llave vive en .env (OILPRICE_API_KEY) y nunca se escribe en el codigo.
Si la API no responde, el analisis economico sigue funcionando con el ultimo
precio guardado en base de datos y, en ultima instancia, con OILPRICE_FALLBACK.
"""
import logging
from datetime import datetime, timezone as dt_timezone

import requests
from django.conf import settings
from django.core.cache import cache

from .models import PrecioCrudo

log = logging.getLogger(__name__)

TIEMPO_ESPERA = 12  # segundos

ETIQUETAS = {
    "BRENT_CRUDE_USD": "Brent",
    "WTI_USD": "WTI",
}


def _headers():
    return {
        "Authorization": f"Token {settings.OILPRICE_API_KEY}",
        "Accept": "application/json",
    }


def _parsear_fecha(txt):
    if not txt:
        return None
    try:
        return datetime.fromisoformat(txt.replace("Z", "+00:00"))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Cotizacion vigente
# ---------------------------------------------------------------------------
def precio_actual(codigo=None, forzar=False) -> dict:
    """Devuelve {precio, moneda, codigo, etiqueta, as_of, fuente, error}.

    `fuente` puede ser: 'api', 'cache', 'base' (ultimo guardado) o 'respaldo'.
    """
    codigo = codigo or settings.OILPRICE_DEFAULT_CODE
    clave = f"oilprice:{codigo}"

    if not forzar:
        guardado = cache.get(clave)
        if guardado:
            return {**guardado, "fuente": "cache"}

    if not settings.OILPRICE_API_KEY:
        return _respaldo(codigo, "No hay OILPRICE_API_KEY configurada en .env")

    url = f"{settings.OILPRICE_API_BASE}/prices/latest"
    try:
        resp = requests.get(url, headers=_headers(), params={"by_code": codigo},
                            timeout=TIEMPO_ESPERA)
        resp.raise_for_status()
        cuerpo = resp.json()
        d = cuerpo.get("data") or {}
        precio = float(d["price"])
        salida = {
            "precio": precio,
            "moneda": d.get("currency", "USD"),
            "codigo": d.get("code", codigo),
            "etiqueta": ETIQUETAS.get(codigo, codigo),
            "as_of": d.get("created_at") or d.get("updated_at"),
            "tipo": d.get("type", ""),
            "obsoleto": bool(d.get("stale")),
            "cambio_24h": (d.get("changes") or {}).get("24h", {}),
            "fuente": "api",
            "error": "",
        }
        cache.set(clave, salida, settings.OILPRICE_CACHE_MINUTES * 60)
        PrecioCrudo.objects.create(
            codigo=codigo, precio=precio, moneda=salida["moneda"],
            tipo=salida["tipo"], as_of=_parsear_fecha(salida["as_of"]),
            exitoso=True, detalle={"changes": salida["cambio_24h"]},
        )
        return salida
    except Exception as exc:  # red, JSON, llave invalida...
        log.warning("oilpriceapi fallo para %s: %s", codigo, exc)
        return _respaldo(codigo, str(exc)[:160])


def _respaldo(codigo, error) -> dict:
    """Ultimo precio en base de datos; si no hay, el valor de configuracion."""
    ultimo = PrecioCrudo.objects.filter(codigo=codigo, exitoso=True).first()
    if ultimo:
        return {
            "precio": ultimo.precio, "moneda": ultimo.moneda, "codigo": codigo,
            "etiqueta": ETIQUETAS.get(codigo, codigo),
            "as_of": ultimo.as_of.isoformat() if ultimo.as_of else None,
            "tipo": ultimo.tipo, "obsoleto": True, "cambio_24h": {},
            "fuente": "base", "error": error,
        }
    return {
        "precio": settings.OILPRICE_FALLBACK, "moneda": "USD", "codigo": codigo,
        "etiqueta": ETIQUETAS.get(codigo, codigo), "as_of": None, "tipo": "",
        "obsoleto": True, "cambio_24h": {}, "fuente": "respaldo", "error": error,
    }


# ---------------------------------------------------------------------------
# Historico para el grafico de precio
# ---------------------------------------------------------------------------
def historico(codigo=None, limite=180) -> dict:
    """Serie diaria del ultimo ano: {serie: [[fecha, precio], ...], error}."""
    codigo = codigo or settings.OILPRICE_DEFAULT_CODE
    clave = f"oilprice:hist:{codigo}:{limite}"
    guardado = cache.get(clave)
    if guardado:
        return guardado

    if not settings.OILPRICE_API_KEY:
        return {"serie": [], "error": "Sin llave de API", "codigo": codigo}

    url = f"{settings.OILPRICE_API_BASE}/prices/past_year"
    try:
        resp = requests.get(url, headers=_headers(), params={"by_code": codigo},
                            timeout=TIEMPO_ESPERA + 8)
        resp.raise_for_status()
        precios = ((resp.json().get("data") or {}).get("prices")) or []
        serie = []
        for p in precios:
            f = _parsear_fecha(p.get("created_at") or p.get("as_of"))
            if f is None:
                continue
            serie.append([f.date().isoformat(), round(float(p["price"]), 2)])
        # la API entrega del mas reciente al mas antiguo
        serie.sort(key=lambda z: z[0])
        if limite and len(serie) > limite:
            serie = serie[-limite:]
        salida = {"serie": serie, "error": "", "codigo": codigo,
                  "etiqueta": ETIQUETAS.get(codigo, codigo)}
        cache.set(clave, salida, 6 * 3600)
        return salida
    except Exception as exc:
        log.warning("historico oilpriceapi fallo: %s", exc)
        return {"serie": [], "error": str(exc)[:160], "codigo": codigo,
                "etiqueta": ETIQUETAS.get(codigo, codigo)}
