"""Solucion de Buckley-Leverett en Python puro (sin numpy).

Secuencia implementada:

  1. Ajuste  kro/krw = a·e^(-b·Sw)   por minimos cuadrados sobre ln(kro/krw).
  2. Flujo fraccional  fw = 1 / (1 + (mu_w/mu_o)·a·e^(-b·Sw)).
  3. Derivada analitica  dfw/dSw = b·fw·(1 - fw).
  4. Frente de choque por construccion de Welge: se maximiza la pendiente de
     la cuerda desde (Swi, 0). Maximizar la cuerda es equivalente a la
     condicion de tangencia y evita la ambiguedad de las dos raices que tiene
     la ecuacion de tangencia con el modelo exponencial.
  5. Comportamiento posterior a la irrupcion (Welge) para recobro y WOR.

Todo trabaja en unidades de campo.
"""
import math
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence, Tuple

FT3_POR_BBL = 5.6145833


# ---------------------------------------------------------------------------
# Paso 1 - ajuste exponencial de la razon de permeabilidades
# ---------------------------------------------------------------------------
@dataclass
class AjusteKr:
    a: float
    b: float
    r2: float
    puntos: List[Tuple[float, float]]      # (Sw, ln(kro/krw)) usados
    pendiente: float
    intercepto: float
    descartados: int = 0

    @property
    def valido(self) -> bool:
        return self.b > 0


def ajustar_kr(tabla: Sequence[Sequence[float]]) -> Tuple[Optional[AjusteKr], str]:
    """Regresion lineal de ln(kro/krw) contra Sw.

    `tabla` es una secuencia de (Sw, krw, kro). Devuelve (ajuste, mensaje).
    """
    puntos, descartados = [], 0
    for fila in tabla:
        try:
            sw, krw, kro = float(fila[0]), float(fila[1]), float(fila[2])
        except (TypeError, ValueError, IndexError):
            descartados += 1
            continue
        if krw > 0 and kro > 0 and 0.0 <= sw <= 1.0:
            puntos.append((sw, math.log(kro / krw)))
        else:
            descartados += 1

    if len(puntos) < 3:
        return None, ("Se necesitan al menos 3 puntos con krw > 0 y kro > 0. "
                      f"Utilizables: {len(puntos)}.")

    n = len(puntos)
    mx = sum(p[0] for p in puntos) / n
    my = sum(p[1] for p in puntos) / n
    sxy = sum((x - mx) * (y - my) for x, y in puntos)
    sxx = sum((x - mx) ** 2 for x, _ in puntos)
    syy = sum((y - my) ** 2 for _, y in puntos)
    if sxx == 0:
        return None, "Todos los valores de Sw son iguales: no hay regresion posible."

    m = sxy / sxx
    c = my - m * mx
    ssr = sum((y - (c + m * x)) ** 2 for x, y in puntos)
    r2 = 1.0 - ssr / syy if syy > 0 else 1.0

    ajuste = AjusteKr(a=math.exp(c), b=-m, r2=r2, puntos=puntos,
                      pendiente=m, intercepto=c, descartados=descartados)
    if not ajuste.valido:
        return None, ("La pendiente ajustada da b <= 0: kro/krw no decrece al "
                      "aumentar Sw. Revise la tabla de permeabilidades relativas.")
    return ajuste, ""


# ---------------------------------------------------------------------------
# Pasos 2 a 5 - solucion completa
# ---------------------------------------------------------------------------
@dataclass
class SolucionBL:
    """Resultado del analisis para un juego de propiedades roca-fluido."""

    ok: bool = False
    mensaje: str = ""

    # entradas
    swi: float = 0.0
    sor: float = 0.0
    muw: float = 0.0
    muo: float = 0.0
    phi: float = 0.0
    bo: float = 1.0
    bw: float = 1.0

    # ajuste
    a: float = 0.0
    b: float = 0.0
    r2: float = 0.0
    ajuste: Optional[AjusteKr] = None

    # frente
    swf: float = 0.0
    fwf: float = 0.0
    dfwf: float = 0.0
    fw0: float = 0.0              # fw en Swi: 0 en el caso clasico, >0 con el ajuste exponencial
    sw_prom_bt: float = 0.0
    ed_bt: float = 0.0            # eficiencia de desplazamiento a la irrupcion
    razon_movilidad: float = 0.0
    piston: bool = False          # True si no hay onda de rarefaccion

    # funciones
    fw: Callable[[float], float] = field(default=lambda s: 0.0, repr=False)
    dfw: Callable[[float], float] = field(default=lambda s: 0.0, repr=False)

    @property
    def delta_s(self) -> float:
        """Sw promedio tras el frente menos Swi: el 'relleno' de agua por PV."""
        return max(self.sw_prom_bt - self.swi, 1e-6)

    # -- utilidades ---------------------------------------------------------
    def curva_fw(self, n: int = 160) -> List[Tuple[float, float]]:
        return [(s, self.fw(s)) for s in self._malla(n)]

    def curva_dfw(self, n: int = 160) -> List[Tuple[float, float]]:
        return [(s, self.dfw(s)) for s in self._malla(n)]

    def _malla(self, n: int) -> List[float]:
        lo, hi = self.swi, 1.0 - self.sor
        return [lo + (hi - lo) * i / (n - 1) for i in range(n)]

    # -- comportamiento posterior a la irrupcion (Welge) --------------------
    def estado_post_bt(self, sw2: float) -> dict:
        """Estado del productor cuando la saturacion en la cara es sw2.

        Wi en volumenes porosos, Sw promedio, eficiencia, corte de agua y WOR.
        """
        sw2 = min(max(sw2, self.swf), 1.0 - self.sor)
        fw2 = self.fw(sw2)
        d2 = self.dfw(sw2)
        wi_pv = 1.0 / d2 if d2 > 1e-12 else float("inf")
        sw_prom = sw2 + (1.0 - fw2) * wi_pv
        sw_prom = min(sw_prom, 1.0 - self.sor)
        ed = (sw_prom - self.swi) / max(1.0 - self.swi, 1e-9)
        # Conversion de fraccion de flujo de yacimiento a superficie
        qw_std = fw2 / max(self.bw, 1e-9)
        qo_std = (1.0 - fw2) / max(self.bo, 1e-9)
        corte = qw_std / (qw_std + qo_std) if (qw_std + qo_std) > 0 else 1.0
        wor = qw_std / qo_std if qo_std > 1e-12 else float("inf")
        return {
            "sw2": sw2, "fw2": fw2, "dfw2": d2, "wi_pv": wi_pv,
            "sw_prom": sw_prom, "ed": ed, "corte_agua": corte, "wor": wor,
            "np_pv": sw_prom - self.swi,
        }

    def historia_post_bt(self, n: int = 60) -> List[dict]:
        """Recorrido desde Swf hasta 1 - Sor: recobro y corte de agua."""
        hi = 1.0 - self.sor
        salida = []
        for i in range(n):
            # se acerca a hi sin alcanzarlo (dfw -> 0 hace Wi -> infinito)
            sw2 = self.swf + (hi - self.swf) * (i / n) ** 0.85
            if sw2 <= self.swf:
                sw2 = self.swf + 1e-6
            salida.append(self.estado_post_bt(sw2))
        return salida

    def perfil_saturacion(self, x_frente: float, n: int = 120) -> List[Tuple[float, float]]:
        """Perfil Sw vs distancia. El frente en x_frente marca el salto."""
        if x_frente <= 0:
            return [(0.0, self.swi)]
        hi = 1.0 - self.sor
        pts = []
        for i in range(n):
            s = hi - (hi - self.swf) * i / (n - 1)
            # x/x_frente = (dfw/dSw)(s) / (dfw/dSw)(Swf)
            x = x_frente * self.dfw(s) / self.dfwf if self.dfwf > 0 else 0.0
            pts.append((x, s))
        pts.append((x_frente, self.swi))       # salto vertical del choque
        pts.append((x_frente * 1.6 + 1.0, self.swi))
        return pts


def resolver(tabla, swi, sor, muw, muo, phi=0.2, bo=1.0, bw=1.0) -> SolucionBL:
    """Punto de entrada: de la tabla kr a la solucion completa."""
    sol = SolucionBL(swi=swi, sor=sor, muw=muw, muo=muo, phi=phi, bo=bo, bw=bw)

    if swi + sor >= 1.0:
        sol.mensaje = f"Swi + Sor = {swi + sor:.3f} debe ser menor que 1."
        return sol
    if min(muw, muo, phi) <= 0:
        sol.mensaje = "Viscosidades y porosidad deben ser mayores que cero."
        return sol

    ajuste, msg = ajustar_kr(tabla)
    if ajuste is None:
        sol.mensaje = msg
        return sol

    sol.ajuste, sol.a, sol.b, sol.r2 = ajuste, ajuste.a, ajuste.b, ajuste.r2

    K = (muw / muo) * ajuste.a
    b = ajuste.b
    sol.fw = lambda s: 1.0 / (1.0 + K * math.exp(-b * s))
    sol.dfw = lambda s: b * sol.fw(s) * (1.0 - sol.fw(s))

    # --- Welge / Rankine-Hugoniot -----------------------------------------
    # El choque une el estado de adelante (Swi) con el del frente (Swf):
    #
    #     dfw/dSw|Swf = [ fw(Swf) - fw(Swi) ] / (Swf - Swi)
    #
    # El texto clasico dibuja la tangente desde (Swi, 0) porque krw(Swc) = 0
    # hace fw(Swi) = 0. El ajuste exponencial kro/krw = a·e^(-b·Sw) no puede
    # representar krw -> 0 y deja un fw(Swi) pequeno pero no nulo, asi que se
    # usa la forma general. Si fw(Swi) tiende a 0 se recupera el caso clasico.
    #
    # Entre todas las cuerdas, la fisica (condicion de entropia de Oleinik)
    # elige la de mayor pendiente: maximizar la cuerda equivale a la condicion
    # de tangencia y evita la ambiguedad de las dos raices que tiene la
    # ecuacion de tangencia con este modelo.
    hi = 1.0 - sor
    lo = swi + 1e-6
    if hi <= lo:
        sol.mensaje = "Rango de saturacion movil nulo."
        return sol

    sol.fw0 = sol.fw(swi)

    def cuerda(s: float) -> float:
        return (sol.fw(s) - sol.fw0) / (s - swi) if s > swi else sol.dfw(swi)

    # barrido grueso
    N = 1200
    mejor_s, mejor_v = lo, cuerda(lo)
    for i in range(N + 1):
        s = lo + (hi - lo) * i / N
        v = cuerda(s)
        if v > mejor_v:
            mejor_v, mejor_s = v, s

    # Refinamiento por busqueda ternaria dentro del intervalo que rodea al
    # mejor punto del barrido. La cuerda es unimodal ahi, asi que converge.
    paso = (hi - lo) / N
    izq, der = max(lo, mejor_s - paso), min(hi, mejor_s + paso)
    for _ in range(100):
        if der - izq < 1e-13:
            break
        m1 = izq + (der - izq) / 3.0
        m2 = der - (der - izq) / 3.0
        if cuerda(m1) < cuerda(m2):
            izq = m1
        else:
            der = m2
    swf = 0.5 * (izq + der)

    # Si el maximo cae en el extremo, el desplazamiento es tipo piston:
    # no hay zona de transicion, el frente llega con Sw = 1 - Sor.
    if swf >= hi - 1e-6:
        swf = hi
        sol.piston = True

    sol.swf = swf
    sol.fwf = sol.fw(swf)
    # En un maximo interior la cuerda y la derivada coinciden; en los extremos
    # manda la cuerda, que es la velocidad real del choque.
    sol.dfwf = max(cuerda(swf), 1e-9)
    if sol.dfwf <= 1e-9:
        sol.mensaje = "La velocidad del frente es nula: revise los datos de entrada."
        return sol

    # Sw promedio tras el frente: la tangente extendida corta fw = 1.
    #   1 = fw(Swi) + dfwf·(Sw_prom - Swi)
    sol.sw_prom_bt = min(swi + (1.0 - sol.fw0) / sol.dfwf, 1.0 - sor)
    sol.ed_bt = (sol.sw_prom_bt - swi) / max(1.0 - swi, 1e-9)

    # Razon de movilidad de puntos extremos:  M = (krw@Sor/mu_w)/(kro@Swc/mu_o)
    # Necesita los kr individuales, que el ajuste exponencial no conserva
    # (solo guarda la razon), asi que se leen de la tabla original.
    validos = [(float(f[0]), float(f[1]), float(f[2])) for f in tabla
               if len(f) >= 3 and f[1] is not None and f[2] is not None]
    if validos:
        krw_sor = max(validos, key=lambda f: f[0])[1]     # krw al mayor Sw
        kro_swc = max(validos, key=lambda f: -f[0])[2]    # kro al menor Sw
        if kro_swc > 0:
            sol.razon_movilidad = (muo / muw) * (krw_sor / kro_swc)

    sol.ok = True
    return sol


# ---------------------------------------------------------------------------
# Avance lineal clasico (se conserva para la ficha por pozo)
# ---------------------------------------------------------------------------
def avance_lineal(sol: SolucionBL, q_bpd: float, area_ft2: float, L_ft: float) -> dict:
    """Modelo 1D clasico: xf(t) y tiempo de irrupcion en un area constante."""
    if not sol.ok or q_bpd <= 0 or area_ft2 <= 0:
        return {"ok": False}
    vel = FT3_POR_BBL * q_bpd * sol.dfwf / (sol.phi * area_ft2)     # ft/dia
    tbt = L_ft / vel if vel > 0 else float("inf")
    return {
        "ok": True,
        "velocidad_frente": vel,
        "tbt_dias": tbt,
        "xf": lambda t: vel * t,
        "vp_bbl": area_ft2 * L_ft * sol.phi / FT3_POR_BBL,
    }
