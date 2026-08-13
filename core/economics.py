"""Analisis economico del patron de inyeccion, centrado en OPEX.

El perfil de produccion no es una curva inventada: sale de la misma solucion
de Buckley-Leverett. Antes de la irrupcion cada productor entrega su corte de
agua base; despues, el corte lo dicta Welge

    Wi(pv) = 1 / (dfw/dSw)|Sw2        y        corte = fw(Sw2)

de modo que el pozo al que el agua llega primero es tambien el que primero
encarece el barril. Esa es la pregunta que responde esta pestana: hasta que
mes el patron paga el agua que mueve.
"""
import math
from typing import Dict, List

from . import engine
from .models import ParametrosEconomicos, Pozo, TipoPozo

DIAS_MES = 30.4375


# ---------------------------------------------------------------------------
# Inversion de Welge: que saturacion corresponde a Wi volumenes porosos
# ---------------------------------------------------------------------------
def sw_para_wi(sol, wi_pv: float) -> float:
    """Sw en la cara del productor tras inyectar wi_pv volumenes porosos."""
    if wi_pv <= 0:
        return sol.swi
    objetivo = 1.0 / wi_pv
    lo, hi = sol.swf, 1.0 - sol.sor
    if sol.dfw(lo) <= objetivo:
        return lo
    if sol.dfw(hi) >= objetivo:
        return hi
    for _ in range(90):
        mid = 0.5 * (lo + hi)
        if sol.dfw(mid) > objetivo:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def corte_agua_superficie(sol, fw_res: float) -> float:
    """Convierte fraccion de flujo de yacimiento a corte de agua de superficie."""
    qw = fw_res / max(sol.bw, 1e-9)
    qo = (1.0 - fw_res) / max(sol.bo, 1e-9)
    return qw / (qw + qo) if (qw + qo) > 0 else 1.0


# ---------------------------------------------------------------------------
# Simulacion mensual
# ---------------------------------------------------------------------------
def simular(proyecto, params: ParametrosEconomicos, precio_marcador: float) -> dict:
    analisis = engine.analizar_proyecto(proyecto, persistir=False)

    productores = list(Pozo.objects.filter(proyecto=proyecto, tipo=TipoPozo.PRODUCTOR))
    inyectores = list(Pozo.objects.filter(proyecto=proyecto, tipo=TipoPozo.INYECTOR))
    q_iny_total = sum(max(i.q or 0.0, 0.0) for i in inyectores)

    # Solucion y tiempo de irrupcion por productor
    estados = []
    por_id = {p["id"]: p for p in analisis["productores"]}
    for p in productores:
        sol = engine.resolver_pozo(p)
        if not sol.ok:
            continue
        info = por_id.get(p.id, {})
        tbt = info.get("tbt")
        estados.append({
            "pozo": p, "sol": sol,
            "tbt": tbt if tbt and tbt > 0 else None,
            "qL": max(p.q or 0.0, 0.0),
            "wi_pv_bt": 1.0 / sol.dfwf if sol.dfwf > 0 else None,
        })

    if not estados:
        return {"ok": False, "mensaje": "No hay productores con solucion valida."}

    # -- punto de partida del perfil ---------------------------------------
    # El liquido total lo fijan los caudales de los pozos y no se reescala:
    # hacerlo rompe el balance con el agua inyectada (la relacion de reemplazo
    # de vaciamiento se dispararia). Por eso el caudal de petroleo y el corte
    # de agua son dos formas de decir lo mismo, y solo uno de los dos manda.
    qL_total = sum(e["qL"] for e in estados)

    if qL_total <= 0:
        # Proyecto sin caudales cargados: se cae al valor declarado.
        cut0 = min(max(params.corte_agua_inicial, 0.0), 0.98)
        qL_total = params.qo_inicial / max(1.0 - cut0, 1e-6)
        for e in estados:
            e["qL"] = qL_total / len(estados)
    elif params.base_produccion == ParametrosEconomicos.Base.CAUDAL:
        cut0 = min(max(1.0 - params.qo_inicial / qL_total, 0.0), 0.98)
    else:
        cut0 = min(max(params.corte_agua_inicial, 0.0), 0.98)

    qo_inicial_efectivo = qL_total * (1.0 - cut0)
    vrr = (q_iny_total / qL_total) if qL_total > 0 else None

    precio_neto = precio_marcador + params.diferencial
    factor_ingreso = max(precio_neto, 0.0) * (1.0 - params.regalia)
    i_mes = (1.0 + params.tasa_descuento) ** (1.0 / 12.0) - 1.0

    filas: List[dict] = []
    acum_no_desc = -params.capex_inicial
    vpn = -params.capex_inicial
    np_total = 0.0
    wp_total = 0.0
    wi_total = 0.0
    mes_limite = None
    payback = None

    for mes in range(1, params.horizonte_meses + 1):
        t_dias = (mes - 0.5) * DIAS_MES
        anios = t_dias / 365.25
        decl = math.exp(-params.declinacion_anual * anios)

        qo = 0.0
        qw = 0.0
        for e in estados:
            sol, qL, tbt = e["sol"], e["qL"], e["tbt"]
            if tbt and t_dias > tbt and e["wi_pv_bt"]:
                wi_pv = e["wi_pv_bt"] * (t_dias / tbt)
                sw2 = sw_para_wi(sol, wi_pv)
                cut = max(corte_agua_superficie(sol, sol.fw(sw2)), cut0)
            else:
                cut = cut0
            qo_j = qL * (1.0 - cut) * decl
            qo += qo_j
            qw += max(qL - qo_j, 0.0)

        if qo < params.limite_economico_bopd and mes_limite is None:
            mes_limite = mes

        oil = qo * DIAS_MES
        water = qw * DIAS_MES
        winj = q_iny_total * DIAS_MES

        ingreso = oil * factor_ingreso
        op_iny = winj * params.costo_iny_agua
        op_agua = water * (params.costo_manejo_agua + params.costo_quimicos)
        op_lev = (oil + water) * params.costo_levantamiento
        op_crudo = oil * params.costo_tratamiento_crudo
        opex = op_iny + op_agua + op_lev + op_crudo + params.opex_fijo_mes

        neto = ingreso - opex
        acum_no_desc += neto
        vpn += neto / ((1.0 + i_mes) ** mes)

        np_total += oil
        wp_total += water
        wi_total += winj

        if payback is None and acum_no_desc >= 0:
            payback = mes

        filas.append({
            "mes": mes,
            "anio": round(mes / 12.0, 2),
            "qo": round(qo, 2),
            "qw": round(qw, 2),
            "corte": round(qw / (qo + qw), 4) if (qo + qw) > 0 else 1.0,
            "oil": round(oil, 1),
            "water": round(water, 1),
            "ingreso": round(ingreso, 0),
            "opex": round(opex, 0),
            "op_iny": round(op_iny, 0),
            "op_agua": round(op_agua, 0),
            "op_lev": round(op_lev, 0),
            "op_crudo": round(op_crudo, 0),
            "op_fijo": round(params.opex_fijo_mes, 0),
            "neto": round(neto, 0),
            "acum": round(acum_no_desc, 0),
            "vpn": round(vpn, 0),
            "opex_bbl": round(opex / oil, 2) if oil > 1 else None,
        })

    # -- primer mes con margen negativo ------------------------------------
    mes_margen_neg = next((f["mes"] for f in filas if f["neto"] < 0), None)

    # -- precio de equilibrio: VPN(P) = 0, lineal en P ---------------------
    #    VPN = sum[ d_m·( oil_m·(P + dif)·(1-reg) - opex_m ) ] - capex
    a = sum(f["oil"] * (1.0 - params.regalia) / ((1.0 + i_mes) ** f["mes"]) for f in filas)
    b = sum((-f["opex"]) / ((1.0 + i_mes) ** f["mes"]) for f in filas) - params.capex_inicial
    b += a * params.diferencial
    precio_equilibrio = (-b / a) if a > 0 else None

    opex_total = sum(f["opex"] for f in filas)
    ingreso_total = sum(f["ingreso"] for f in filas)

    return {
        "ok": True,
        "filas": filas,
        "resumen": {
            "vpn": round(vpn, 0),
            "payback_meses": payback,
            "mes_margen_negativo": mes_margen_neg,
            "mes_limite_economico": mes_limite,
            "np_total": round(np_total, 0),
            "wp_total": round(wp_total, 0),
            "wi_total": round(wi_total, 0),
            "opex_total": round(opex_total, 0),
            "ingreso_total": round(ingreso_total, 0),
            "opex_por_bbl": round(opex_total / np_total, 2) if np_total > 0 else None,
            "utilidad_total": round(ingreso_total - opex_total - params.capex_inicial, 0),
            "precio_equilibrio": round(precio_equilibrio, 2) if precio_equilibrio else None,
            "precio_neto": round(precio_neto, 2),
            "razon_agua_petroleo": round(wi_total / np_total, 2) if np_total > 0 else None,
            "q_iny_total": round(q_iny_total, 1),
            "q_liquido_total": round(qL_total, 1),
            "qo_inicial": round(qo_inicial_efectivo, 1),
            "corte_inicial": round(cut0, 4),
            "vrr": round(vrr, 2) if vrr else None,
            "viable": vpn > 0,
        },
        "desglose_opex": _desglose(filas),
        "irrupciones": analisis["orden_irrupcion"],
    }


def _desglose(filas) -> List[dict]:
    """Reparto del OPEX acumulado por concepto, para la grafica de torta."""
    conceptos = [
        ("Inyeccion de agua", "op_iny", "var(--brine)"),
        ("Manejo de agua producida", "op_agua", "var(--gas)"),
        ("Levantamiento", "op_lev", "var(--crude)"),
        ("Tratamiento de crudo", "op_crudo", "var(--rock)"),
        ("OPEX fijo", "op_fijo", "var(--faint)"),
    ]
    total = sum(sum(f[c[1]] for f in filas) for c in conceptos) or 1.0
    return [{
        "concepto": nombre,
        "monto": round(sum(f[clave] for f in filas), 0),
        "fraccion": round(sum(f[clave] for f in filas) / total, 4),
        "color": color,
    } for nombre, clave, color in conceptos]


def parametros_de(proyecto) -> ParametrosEconomicos:
    """Devuelve (creando si hace falta) los supuestos economicos del proyecto."""
    obj, _ = ParametrosEconomicos.objects.get_or_create(proyecto=proyecto)
    return obj
