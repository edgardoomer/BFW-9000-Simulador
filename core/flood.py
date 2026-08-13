"""Geometria areal del frente de agua: el area barrida y sus brazos.

El modelo lineal clasico de Buckley-Leverett entrega una sola distancia xf(t).
Un patron real no avanza igual en todas las direcciones: el agua corre por los
canales de mayor permeabilidad y llega antes a unos productores que a otros.

Aqui se reparte el caudal de cada inyector entre azimuts mediante una densidad
angular w(theta) y se cierra el balance volumetrico por sectores:

    volumen inyectado en el sector d(theta)  =  volumen poroso barrido

    5.6146·q·t · w(theta)d(theta)/W  =  phi·h·(Sw_prom - Swi)·(r²/2)·d(theta)

de donde

    r(theta, t) = sqrt( 2·5.6146·q·t·w(theta) / (W·phi·h·dS) ) = r_unit(theta)·sqrt(t)

El frente avanza con la raiz del tiempo (radial) y la direccion pesa a traves
de w(theta). La irrupcion en el productor j ocurre cuando r(theta_j, t) = L_j:

    t_BT,j = ( L_j / r_unit(theta_j) )²

w(theta) es un fondo constante (la matriz, que da el cuerpo circular) mas una
campana de Gauss por cada productor conectado, con amplitud proporcional a la
transmisibilidad k·h/ln(L/rw) del canal. Esas campanas son los brazos.
"""
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

FT3_POR_BBL = 5.6145833

# Numero de azimuts con que se discretiza el contorno para dibujar.
N_AZIMUT = 240
# El brazo se detiene en el productor: la linea de corriente termina ahi.
# Con 1.25 el radio efectivo vale exactamente L justo en la irrupcion.
FACTOR_TOPE = 1.25
# Peso del fondo matricial frente al brazo mas conductivo (que vale 1.0).
PESO_FONDO = 0.26


def _envolver(delta: float) -> float:
    """Lleva una diferencia de angulos al intervalo [-pi, pi]."""
    return (delta + math.pi) % (2.0 * math.pi) - math.pi


def _tope_suave(r: float, tope: float) -> float:
    """Limita r a `tope` con transicion C1 a partir del 80 % del tope."""
    if tope <= 0:
        return 0.0
    u = r / tope
    if u <= 0.8:
        return r
    return tope * (1.0 - 0.2 * math.exp(-(u - 0.8) / 0.2))


@dataclass
class Brazo:
    """Un canal inyector -> productor."""
    par_id: int
    productor_id: int
    productor_nombre: str
    azimut: float                 # rad
    L: float                      # ft
    sigma: float                  # rad, ancho angular de la campana
    k_direccional: float          # md
    transmisibilidad: float
    peso: float = 0.0             # transmisibilidad normalizada (0..1]
    fraccion_caudal: float = 0.0  # fraccion del agua del inyector
    r_unit: float = 0.0           # ft/sqrt(dia) en el azimut del productor
    tbt_dias: float = float("inf")


@dataclass
class CampoInyector:
    """Densidad angular y contorno del frente de un inyector."""
    inyector_id: int
    nombre: str
    x: float
    y: float
    q: float
    phi: float
    h: float
    delta_s: float
    brazos: List[Brazo] = field(default_factory=list)
    azimutes: List[float] = field(default_factory=list)
    r_unit: List[float] = field(default_factory=list)
    tope: List[float] = field(default_factory=list)
    mensaje: str = ""
    ok: bool = True

    def radio(self, theta_idx: int, t: float) -> float:
        return _tope_suave(self.r_unit[theta_idx] * math.sqrt(max(t, 0.0)),
                           self.tope[theta_idx])

    def contorno(self, t: float) -> List[tuple]:
        """Puntos (x, y) del contorno del area barrida al tiempo t."""
        pts = []
        for i, th in enumerate(self.azimutes):
            r = self.radio(i, t)
            pts.append((self.x + r * math.cos(th), self.y + r * math.sin(th)))
        return pts

    def radio_maximo(self, t: float) -> float:
        return max((self.radio(i, t) for i in range(len(self.azimutes))), default=0.0)


def construir_campo(
    inyector,
    pares,
    delta_s_por_productor: Dict[int, float],
    semilla_rugosidad: int = 0,
    rugosidad: float = 0.13,
) -> CampoInyector:
    """Arma la densidad angular w(theta) de un inyector y su contorno.

    `pares` son los ParInyeccion activos de este inyector.
    `delta_s_por_productor` mapea id de productor -> (Sw_prom - Swi) de su
    propia solucion Buckley-Leverett.
    """
    phi = inyector.val("phi") or 0.2
    h = inyector.val("h") or 40.0
    q = max(inyector.q or 0.0, 0.0)

    campo = CampoInyector(
        inyector_id=inyector.id, nombre=inyector.nombre_pozo,
        x=inyector.x_ft, y=inyector.y_ft, q=q, phi=phi, h=h, delta_s=0.0,
    )

    if q <= 0:
        campo.ok = False
        campo.mensaje = f"{inyector.nombre_pozo}: caudal de inyeccion nulo."
        return campo

    # ---- brazos --------------------------------------------------------
    brazos: List[Brazo] = []
    for par in pares:
        L = par.L
        if L <= 1.0:
            continue
        sigma = max(math.radians(par.ancho_brazo) / 2.0, 0.05)
        brazos.append(Brazo(
            par_id=par.id,
            productor_id=par.productor_id,
            productor_nombre=par.productor.nombre_pozo,
            azimut=par.azimut,
            L=L,
            sigma=sigma,
            k_direccional=par.k_direccional,
            transmisibilidad=(par.factor_asignacion
                              if par.factor_asignacion else par.transmisibilidad()),
        ))

    if not brazos:
        campo.mensaje = (f"{inyector.nombre_pozo}: sin productores conectados. "
                         "Se dibuja un frente radial uniforme.")

    t_max = max((b.transmisibilidad for b in brazos), default=1.0) or 1.0
    for b in brazos:
        b.peso = b.transmisibilidad / t_max

    # ---- dS representativo, ponderado por la conductividad de cada canal --
    if brazos:
        num = sum(b.peso * delta_s_por_productor.get(b.productor_id, 0.35) for b in brazos)
        den = sum(b.peso for b in brazos)
        campo.delta_s = max(num / den, 1e-3) if den > 0 else 0.35
    else:
        campo.delta_s = 0.35

    # ---- rugosidad determinista (heterogeneidad de la matriz) -----------
    # Armonicos fijos por inyector: el contorno se ve natural y no cambia
    # entre recargas de la pagina.
    s = (semilla_rugosidad * 2654435761) % 2147483647 or 7
    armonicos = []
    for m in (2, 3, 5, 7):
        s = (s * 1103515245 + 12345) % 2147483648
        fase = 2.0 * math.pi * (s / 2147483648.0)
        s = (s * 1103515245 + 12345) % 2147483648
        amp = rugosidad * (0.35 + 0.65 * (s / 2147483648.0)) / (m ** 0.55)
        armonicos.append((m, fase, amp))

    def rugoso(th: float) -> float:
        return sum(a * math.sin(m * th + f) for m, f, a in armonicos)

    # ---- densidad angular w(theta) --------------------------------------
    def lobulos(th: float) -> float:
        total = 0.0
        for b in brazos:
            d = _envolver(th - b.azimut) / b.sigma
            if abs(d) < 6.0:
                total += b.peso * math.exp(-d * d)
        return total

    def w(th: float) -> float:
        lob = lobulos(th)
        # La rugosidad se apaga donde manda un brazo, para que el azimut del
        # productor conserve el valor fisico exacto.
        atenua = max(0.0, 1.0 - min(lob, 1.0))
        return max(PESO_FONDO * (1.0 + rugoso(th) * atenua) + lob, 1e-4)

    # ---- normalizacion: W = integral de w en 0..2pi ----------------------
    n_int = 720
    dth_int = 2.0 * math.pi / n_int
    W = sum(w(i * dth_int) for i in range(n_int)) * dth_int
    if W <= 0:
        campo.ok = False
        campo.mensaje = "Densidad angular degenerada."
        return campo

    # ---- r_unit(theta) ---------------------------------------------------
    denom = phi * h * campo.delta_s
    if denom <= 0:
        campo.ok = False
        campo.mensaje = f"{inyector.nombre_pozo}: phi·h·dS invalido."
        return campo

    def r_unit(th: float) -> float:
        return math.sqrt(2.0 * FT3_POR_BBL * q * (w(th) / W) / denom)

    # ---- tope por azimut: el brazo termina en su productor ---------------
    L_fondo = (sum(b.L for b in brazos) / len(brazos)) if brazos else 1000.0

    def tope(th: float) -> float:
        num = PESO_FONDO * L_fondo
        den = PESO_FONDO
        for b in brazos:
            d = _envolver(th - b.azimut) / b.sigma
            if abs(d) < 6.0:
                g = b.peso * math.exp(-d * d)
                num += g * b.L
                den += g
        return FACTOR_TOPE * num / den

    # ---- muestreo del contorno ------------------------------------------
    campo.azimutes = [2.0 * math.pi * i / N_AZIMUT for i in range(N_AZIMUT)]
    campo.r_unit = [r_unit(th) for th in campo.azimutes]
    campo.tope = [tope(th) for th in campo.azimutes]

    # ---- irrupcion por brazo, evaluada en el azimut exacto ---------------
    q_total_peso = sum(w(b.azimut) for b in brazos) or 1.0
    for b in brazos:
        b.r_unit = r_unit(b.azimut)
        b.tbt_dias = (b.L / b.r_unit) ** 2 if b.r_unit > 0 else float("inf")
        # Fraccion de agua que toma el canal, integrando su campana
        area_lobulo = b.peso * b.sigma * math.sqrt(math.pi)   # integral de la gaussiana
        b.fraccion_caudal = area_lobulo / W

    campo.brazos = brazos
    return campo


def marco_de_vista(inyectores: List[CampoInyector], pozos, t_max: float, margen: float = 0.12):
    """Rectangulo estable que encuadra todos los pozos y el frente a t_max.

    Se calcula una sola vez con el tiempo maximo para que la vista no salte
    mientras se mueve la barra de tiempo.
    """
    xs, ys = [], []
    for p in pozos:
        xs.append(p.x_ft)
        ys.append(p.y_ft)
    for campo in inyectores:
        if not campo.ok or not campo.azimutes:
            continue
        for x, y in campo.contorno(t_max):
            xs.append(x)
            ys.append(y)

    if not xs:
        return {"x0": -500.0, "x1": 500.0, "y0": -500.0, "y1": 500.0}

    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    dx = (x1 - x0) or 1000.0
    dy = (y1 - y0) or 1000.0
    return {
        "x0": x0 - dx * margen, "x1": x1 + dx * margen,
        "y0": y0 - dy * margen, "y1": y1 + dy * margen,
    }
