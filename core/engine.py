"""Orquestacion: del modelo de datos al resultado listo para graficar.

`analizar_proyecto` es el punto unico de verdad. Resuelve Buckley-Leverett por
productor, arma el campo areal de cada inyector, ordena las irrupciones y
persiste el cache de resultados.
"""
import math
import zlib
from typing import Dict, List, Optional

from . import bl, flood
from .models import CurvaKr, ParInyeccion, Pozo, ResultadoPozo, TipoPozo

FT3_POR_BBL = 5.6145833


def semilla(pozo: Pozo) -> int:
    """Semilla estable de la rugosidad del contorno.

    Se deriva del codigo del pozo y no de su clave primaria: asi los resultados
    se repiten exactamente aunque se vuelvan a cargar los datos y la base
    asigne identificadores nuevos.
    """
    return zlib.crc32(f"{pozo.id_pozo}".encode("utf-8")) & 0x7FFFFFFF


def r(v, n=4):
    """Redondeo seguro para JSON."""
    if v is None:
        return None
    if isinstance(v, float):
        if math.isnan(v):
            return None
        if math.isinf(v):
            return None
        return round(v, n)
    return v


# ---------------------------------------------------------------------------
# Tabla kr aplicable a un pozo
# ---------------------------------------------------------------------------
_CURVA_RESPALDO = [
    (0.22, 0.000, 0.900), (0.30, 0.019, 0.560), (0.38, 0.057, 0.330),
    (0.46, 0.112, 0.176), (0.54, 0.186, 0.079), (0.62, 0.278, 0.024),
    (0.70, 0.360, 0.004), (0.75, 0.380, 0.000),
]


def tabla_kr_de(pozo: Pozo):
    """Curva kr del pozo, o la del proyecto, o una de respaldo."""
    if pozo.curva_kr_id:
        t = pozo.curva_kr.tabla()
        if len(t) >= 3:
            return t, pozo.curva_kr.nombre
    curva = CurvaKr.objects.filter(proyecto=pozo.proyecto).first()
    if curva:
        t = curva.tabla()
        if len(t) >= 3:
            return t, curva.nombre + " (del proyecto)"
    return list(_CURVA_RESPALDO), "Curva de respaldo del sistema"


def resolver_pozo(pozo: Pozo) -> bl.SolucionBL:
    """Solucion Buckley-Leverett de un productor con herencia de defaults."""
    tabla, _ = tabla_kr_de(pozo)
    return bl.resolver(
        tabla,
        swi=pozo.val("swi") or 0.2,
        sor=pozo.val("sor") or 0.25,
        muw=pozo.val("muw") or 0.5,
        muo=pozo.val("muo") or 10.0,
        phi=pozo.val("phi") or 0.2,
        bo=pozo.val("bo") or 1.15,
        bw=pozo.val("bw") or 1.02,
    )


# ---------------------------------------------------------------------------
# Analisis completo del proyecto
# ---------------------------------------------------------------------------
def analizar_proyecto(proyecto, persistir: bool = True) -> dict:
    pozos = list(Pozo.objects.filter(proyecto=proyecto)
                 .select_related("curva_kr", "proyecto"))
    inyectores = [p for p in pozos if p.tipo == TipoPozo.INYECTOR]
    productores = [p for p in pozos if p.tipo == TipoPozo.PRODUCTOR]
    pares = list(
        ParInyeccion.objects.filter(proyecto=proyecto, activo=True)
        .select_related("inyector__proyecto", "productor__proyecto")
    )

    avisos: List[str] = []
    if not inyectores:
        avisos.append("El proyecto no tiene inyectores: no hay frente de agua que simular.")
    if not productores:
        avisos.append("El proyecto no tiene productores.")

    # -- 1. Buckley-Leverett por productor --------------------------------
    soluciones: Dict[int, bl.SolucionBL] = {}
    delta_s: Dict[int, float] = {}
    for p in productores:
        sol = resolver_pozo(p)
        soluciones[p.id] = sol
        if sol.ok:
            delta_s[p.id] = sol.delta_s
        else:
            delta_s[p.id] = 0.35
            avisos.append(f"{p.nombre_pozo}: {sol.mensaje}")

    # -- 2. Campo areal por inyector ---------------------------------------
    campos: List[flood.CampoInyector] = []
    for i, iny in enumerate(inyectores):
        sus_pares = [q for q in pares if q.inyector_id == iny.id]
        campo = flood.construir_campo(iny, sus_pares, delta_s, semilla_rugosidad=semilla(iny))
        if campo.mensaje:
            avisos.append(campo.mensaje)
        campos.append(campo)

    # -- 3. Irrupcion por productor (el primer inyector que llega) ---------
    llegada: Dict[int, List[dict]] = {p.id: [] for p in productores}
    for campo in campos:
        if not campo.ok:
            continue
        for b in campo.brazos:
            llegada.setdefault(b.productor_id, []).append({
                "inyector_id": campo.inyector_id,
                "inyector": campo.nombre,
                "par_id": b.par_id,
                "L": b.L,
                "k": b.k_direccional,
                "azimut_deg": math.degrees(b.azimut) % 360.0,
                "tbt": b.tbt_dias,
                "fraccion_caudal": b.fraccion_caudal,
                "peso": b.peso,
            })

    tbt_finales = []
    for pid, lista in llegada.items():
        lista.sort(key=lambda d: d["tbt"])
        if lista and math.isfinite(lista[0]["tbt"]):
            tbt_finales.append(lista[0]["tbt"])

    t_max = max(tbt_finales) * 1.30 if tbt_finales else 1000.0
    t_max = max(t_max, 1.0)

    # -- 4. Marco de vista estable -----------------------------------------
    marco = flood.marco_de_vista(campos, pozos, t_max)

    # -- 5. Persistencia del cache de resultados ---------------------------
    if persistir:
        for p in productores:
            sol = soluciones[p.id]
            primera = llegada.get(p.id, [])
            top = primera[0] if primera else None
            defaults = {
                "a_ajuste": sol.a if sol.ok else None,
                "b_ajuste": sol.b if sol.ok else None,
                "r2_ajuste": sol.r2 if sol.ok else None,
                "swf": sol.swf if sol.ok else None,
                "fwf": sol.fwf if sol.ok else None,
                "dfwf": sol.dfwf if sol.ok else None,
                "sw_prom": sol.sw_prom_bt if sol.ok else None,
                "ed_bt": sol.ed_bt if sol.ok else None,
                "razon_movilidad": sol.razon_movilidad if sol.ok else None,
                "L_critica": top["L"] if top else None,
                "tbt_dias": (top["tbt"] if top and math.isfinite(top["tbt"]) else None),
                "inyector_critico_id": top["inyector_id"] if top else None,
                "mensaje": sol.mensaje[:240],
            }
            if top and sol.ok:
                # Volumen poroso del canal y agua inyectada hasta la irrupcion
                iny = next((c for c in campos if c.inyector_id == top["inyector_id"]), None)
                if iny:
                    wi = iny.q * top["fraccion_caudal"] * top["tbt"] if math.isfinite(top["tbt"]) else None
                    defaults["wi_bt"] = wi
                    if wi:
                        defaults["np_bt"] = wi / max(p.val("bo") or 1.15, 1e-9)
            ResultadoPozo.objects.update_or_create(pozo=p, defaults=defaults)

    # -- 6. Empaquetado para el frontend -----------------------------------
    return {
        "proyecto": {
            "id": proyecto.id,
            "id_proyecto": proyecto.id_proyecto,
            "nombre": proyecto.nombre,
            "campo": proyecto.campo,
            "bloque": proyecto.bloque,
            "area_acres": proyecto.area_acres,
            "fecha": proyecto.fecha.isoformat(),
        },
        "t_max": r(t_max, 2),
        "marco": {k: r(v, 2) for k, v in marco.items()},
        "avisos": avisos,
        "inyectores": [iny_json(c, i) for i, c in zip(inyectores, campos)],
        "productores": [
            _prod_json(p, soluciones[p.id], llegada.get(p.id, []))
            for p in productores
        ],
        "orden_irrupcion": _orden(productores, llegada),
    }


def iny_json(campo: flood.CampoInyector, pozo: Pozo) -> dict:
    return {
        "id": campo.inyector_id,
        "id_pozo": pozo.id_pozo,
        "nombre": campo.nombre,
        "x": r(campo.x, 2), "y": r(campo.y, 2),          # ya en pies
        "x_orig": r(pozo.x, 2), "y_orig": r(pozo.y, 2),  # como los cargo el usuario
        "q": r(campo.q, 1),
        "phi": r(campo.phi, 4), "h": r(campo.h, 2),
        "delta_s": r(campo.delta_s, 4),
        "ok": campo.ok,
        # r(theta,t) = r_unit(theta)·sqrt(t), limitado por tope(theta)
        "th": [r(v, 5) for v in campo.azimutes],
        "ru": [r(v, 4) for v in campo.r_unit],
        "tope": [r(v, 2) for v in campo.tope],
        "brazos": [{
            "productor_id": b.productor_id,
            "productor": b.productor_nombre,
            "azimut": r(b.azimut, 5),
            "L": r(b.L, 1),
            "k": r(b.k_direccional, 1),
            "tbt": r(b.tbt_dias, 2),
            "fraccion_caudal": r(b.fraccion_caudal, 4),
        } for b in campo.brazos],
    }


def _prod_json(pozo: Pozo, sol: bl.SolucionBL, llegadas: List[dict]) -> dict:
    d = {
        "id": pozo.id,
        "id_pozo": pozo.id_pozo,
        "nombre": pozo.nombre_pozo,
        "x": r(pozo.x_ft, 2), "y": r(pozo.y_ft, 2),
        "x_orig": r(pozo.x, 2), "y_orig": r(pozo.y, 2),
        "q": r(pozo.q, 1),
        "ok": sol.ok,
        "mensaje": sol.mensaje,
        "llegadas": [{
            "inyector": l["inyector"],
            "inyector_id": l["inyector_id"],
            "L": r(l["L"], 1),
            "k": r(l["k"], 1),
            "tbt": r(l["tbt"], 2),
            "fraccion_caudal": r(l["fraccion_caudal"], 4),
        } for l in llegadas],
        "tbt": r(llegadas[0]["tbt"], 2) if llegadas else None,
        "L": r(llegadas[0]["L"], 1) if llegadas else None,
        "inyector_dominante": llegadas[0]["inyector"] if llegadas else None,
    }
    if sol.ok:
        d.update({
            "swi": r(sol.swi, 4), "sor": r(sol.sor, 4),
            "a": r(sol.a, 6), "b": r(sol.b, 4), "r2": r(sol.r2, 5),
            "swf": r(sol.swf, 4), "fwf": r(sol.fwf, 4), "dfwf": r(sol.dfwf, 4),
            "fw0": r(sol.fw0, 5),
            "sw_prom": r(sol.sw_prom_bt, 4), "ed_bt": r(sol.ed_bt, 4),
            "M": r(sol.razon_movilidad, 3),
            "piston": sol.piston,
            "fw_curva": [[r(s, 4), r(f, 5)] for s, f in sol.curva_fw(140)],
            "dfw_curva": [[r(s, 4), r(f, 5)] for s, f in sol.curva_dfw(140)],
            # La tangente arranca en (Swi, fw(Swi)) y se prolonga hasta fw = 1,
            # donde corta en Sw promedio tras el frente.
            "tangente": [[r(sol.swi, 4), r(sol.fw0, 5)],
                         [r(sol.swf, 4), r(sol.fwf, 5)],
                         [r(sol.sw_prom_bt, 4), 1.0]],
        })
    return d


def _orden(productores, llegada) -> List[dict]:
    filas = []
    for p in productores:
        l = llegada.get(p.id, [])
        if not l:
            continue
        filas.append({
            "id": p.id,
            "nombre": p.nombre_pozo,
            "id_pozo": p.id_pozo,
            "tbt": r(l[0]["tbt"], 1),
            "anios": r(l[0]["tbt"] / 365.25, 2) if math.isfinite(l[0]["tbt"]) else None,
            "mes": (round(l[0]["tbt"] / 30.4375) if math.isfinite(l[0]["tbt"]) else None),
            "L": r(l[0]["L"], 0),
            "k": r(l[0]["k"], 0),
            "inyector": l[0]["inyector"],
            "n_fuentes": len(l),
        })
    filas.sort(key=lambda f: (f["tbt"] is None, f["tbt"]))
    for i, f in enumerate(filas, 1):
        f["orden"] = i
    return filas


# ---------------------------------------------------------------------------
# Ficha detallada de un pozo (pestana de calculos)
# ---------------------------------------------------------------------------
def ficha_pozo(pozo: Pozo) -> dict:
    """Todos los graficos y numeros inherentes al metodo, para un pozo."""
    tabla, nombre_curva = tabla_kr_de(pozo)
    datos = {
        "pozo": pozo,
        "curva_nombre": nombre_curva,
        "tabla_kr": [{"sw": s, "krw": w, "kro": o,
                      "razon": (o / w if w > 0 else None)} for s, w, o in tabla],
    }

    if pozo.tipo == TipoPozo.INYECTOR:
        datos["es_inyector"] = True
        pares = ParInyeccion.objects.filter(inyector=pozo, activo=True).select_related("productor")
        ds = {}
        for par in pares:
            sol = resolver_pozo(par.productor)
            ds[par.productor_id] = sol.delta_s if sol.ok else 0.35
        campo = flood.construir_campo(pozo, list(pares), ds, semilla_rugosidad=semilla(pozo))
        datos["campo"] = campo
        datos["pares"] = sorted([{
            "productor": b.productor_nombre,
            "L": b.L, "k": b.k_direccional,
            "azimut": math.degrees(b.azimut) % 360.0,
            "tbt": b.tbt_dias,
            "anios": b.tbt_dias / 365.25 if math.isfinite(b.tbt_dias) else None,
            "fraccion": b.fraccion_caudal,
            "q_asignado": campo.q * b.fraccion_caudal,
            "peso": b.peso,
            "ancho": math.degrees(b.sigma * 2),
        } for b in campo.brazos], key=lambda d: d["tbt"])
        return datos

    # -- productor ---------------------------------------------------------
    sol = resolver_pozo(pozo)
    datos["sol"] = sol
    datos["es_inyector"] = False
    if not sol.ok:
        return datos

    llegadas = []
    for par in ParInyeccion.objects.filter(productor=pozo, activo=True).select_related("inyector"):
        otros = ParInyeccion.objects.filter(inyector=par.inyector, activo=True).select_related("productor")
        ds = {}
        for o in otros:
            s = resolver_pozo(o.productor)
            ds[o.productor_id] = s.delta_s if s.ok else 0.35
        campo = flood.construir_campo(par.inyector, list(otros), ds, semilla_rugosidad=semilla(par.inyector))
        b = next((z for z in campo.brazos if z.productor_id == pozo.id), None)
        if b:
            llegadas.append({
                "inyector": par.inyector.nombre_pozo,
                "L": b.L, "k": b.k_direccional, "tbt": b.tbt_dias,
                "anios": b.tbt_dias / 365.25 if math.isfinite(b.tbt_dias) else None,
                "fraccion": b.fraccion_caudal,
                "q_asignado": campo.q * b.fraccion_caudal,
                "azimut": math.degrees(b.azimut) % 360.0,
                "ancho": math.degrees(b.sigma * 2),
            })
    llegadas.sort(key=lambda d: d["tbt"])
    datos["llegadas"] = llegadas
    datos["tbt"] = llegadas[0]["tbt"] if llegadas else None
    datos["L"] = llegadas[0]["L"] if llegadas else None

    # Series para los graficos
    datos["series"] = {
        "kr": [[s, w, o] for s, w, o in tabla],
        "ajuste": [[x, y] for x, y in (sol.ajuste.puntos if sol.ajuste else [])],
        "recta": _recta_ajuste(sol),
        "fw": [[round(s, 4), round(f, 5)] for s, f in sol.curva_fw(140)],
        "dfw": [[round(s, 4), round(f, 5)] for s, f in sol.curva_dfw(140)],
        "tangente": [[round(sol.swi, 4), round(sol.fw0, 5)],
                     [round(sol.swf, 4), round(sol.fwf, 5)],
                     [round(sol.sw_prom_bt, 4), 1.0]],
        "post_bt": [[round(e["wi_pv"], 4), round(e["ed"], 5), round(e["corte_agua"], 5),
                     round(min(e["wor"], 200.0), 4), round(e["sw2"], 4)]
                    for e in sol.historia_post_bt(70) if math.isfinite(e["wi_pv"])],
    }

    # Perfil de saturacion a la irrupcion
    if datos["L"]:
        datos["series"]["perfil"] = [[round(x, 2), round(s, 4)]
                                     for x, s in sol.perfil_saturacion(datos["L"], 110)]

    # Presion capilar por J de Leverett, si hay datos
    datos["pc"] = _curva_pc(pozo, sol)
    return datos


def _recta_ajuste(sol: bl.SolucionBL):
    if not sol.ajuste or not sol.ajuste.puntos:
        return []
    xs = [p[0] for p in sol.ajuste.puntos]
    x0, x1 = min(xs) - 0.02, max(xs) + 0.02
    f = lambda x: sol.ajuste.intercepto + sol.ajuste.pendiente * x
    return [[round(x0, 4), round(f(x0), 5)], [round(x1, 4), round(f(x1), 5)]]


def _curva_pc(pozo: Pozo, sol: bl.SolucionBL):
    """Presion capilar por funcion J de Leverett.

        Pc = sigma·cos(theta)·J(Sw) / sqrt(k/phi) · 0.21584

    El factor convierte dina/cm y md a psi. J(Sw) se toma como una ley de
    potencia sobre la saturacion normalizada, que es la forma habitual de
    drenaje/imbibicion cuando no hay datos de laboratorio.
    """
    k = pozo.val("k")
    phi = pozo.val("phi")
    sigma = pozo.sigma_ow
    theta = pozo.angulo_contacto
    if not (k and phi and sigma):
        return None
    theta = 30.0 if theta is None else theta
    swi, sor = sol.swi, sol.sor
    span = (1.0 - sor) - swi
    if span <= 0:
        return None
    factor = 0.21584 * sigma * math.cos(math.radians(theta)) / math.sqrt(k / phi)
    pts = []
    for i in range(60):
        sw = swi + span * (i / 59.0)
        swn = max((sw - swi) / span, 1e-3)
        j = 0.22 * swn ** -0.55 - 0.14      # J decreciente tipico de imbibicion
        pc = max(factor * j, 0.0)
        pts.append([round(sw, 4), round(pc, 4)])
    return pts
