"""Modelo de datos del simulador de inyeccion de agua (Buckley-Leverett).

Cuatro tablas maestras:

  Proyecto           - cabecera del estudio (bloque, campo, area, pozos)
  Pozo               - inyectores y productores, con petrofisica y completacion
  CurvaKr / PuntoKr  - curvas de permeabilidad relativa krw / kro vs Sw
  ParInyeccion       - enlace inyector -> productor (varios a varios)

Mas dos tablas de apoyo: ResultadoPozo (cache de calculos) y
ParametrosEconomicos + PrecioCrudo (analisis de OPEX).

Unidades de campo en todo el modelo: ft, md, cp, psi, BPD, bbl, USD.
"""
import math

from django.db import models
from django.utils import timezone

# Conversion barril <-> pie cubico
FT3_POR_BBL = 5.6145833
PIES2_POR_ACRE = 43560.0


class TipoPozo(models.TextChoices):
    INYECTOR = "INY", "Inyector"
    PRODUCTOR = "PRO", "Productor"


class TipoLevantamiento(models.TextChoices):
    NATURAL = "NAT", "Flujo natural"
    BES = "BES", "Bombeo electrosumergible (BES/ESP)"
    BH = "BH", "Bombeo hidráulico (Jet)"
    BM = "BM", "Bombeo mecánico"
    PCP = "PCP", "Bomba de cavidad progresiva (PCP)"
    GAS_LIFT = "GL", "Gas lift"
    INY_HPS = "HPS", "Inyección con HPS"
    INY_RECRIPROACTE = "Q/T", "Inyección con bomba reciprocante (quintuplex o triplex)"

class TipoBombaInyeccion(models.TextChoices):
    TRIPLEX = "TRIPLEX", "BombaTriplex"
    QUINTUPLEX = "QUINTUPLEX", "Bomba Quintuplex"
    HPS = "HPS", "HPS - sistema de bombeo horizontal"
    NA = "NA", "No aplica (productor)"


class TipoCompletacion(models.TextChoices):
    HUECO_ABIERTO = "OH", "Hueco abierto"
    CANONEADA = "PERF", "Revestidor canoneado"
    LINER_RANURADO = "LR", "Liner ranurado"
    MALLA = "SS", "Malla / screen"
    SELECTIVA = "SEL", "Selectiva multizona"


# ---------------------------------------------------------------------------
# 1. Proyecto
# ---------------------------------------------------------------------------
class Proyecto(models.Model):
    """Base maestra de proyectos de inyeccion de agua."""

    id_proyecto = models.CharField(
        "ID Proyecto", max_length=32, unique=True,
        help_text="Codigo unico del estudio, p.ej. BL-2026-001",
    )
    nombre = models.CharField("Nombre del proyecto", max_length=160)
    fecha = models.DateField("Fecha", default=timezone.localdate)
    bloque = models.CharField("Bloque", max_length=80, blank=True)
    campo = models.CharField("Campo", max_length=80, blank=True)
    pozos = models.PositiveIntegerField(
        "Pozos declarados", default=0,
        help_text="Numero de pozos del patron segun la ficha del proyecto.",
    )
    area_acres = models.FloatField("Area (acres)", default=160.0)

    class UnidadCoord(models.TextChoices):
        PIES = "FT", "Pies"
        METROS = "M", "Metros (UTM)"

    unidad_coord = models.CharField(
        "Unidad de las coordenadas", max_length=2,
        choices=UnidadCoord.choices, default=UnidadCoord.PIES,
        help_text="Las coordenadas se guardan tal como se cargan; el calculo "
                  "las convierte a pies internamente.",
    )

    operadora = models.CharField("Operadora", max_length=120, blank=True)
    yacimiento = models.CharField("Yacimiento / arena", max_length=120, blank=True)
    descripcion = models.TextField("Descripcion", blank=True)

    # Valores por defecto del yacimiento. Se usan cuando un pozo no trae dato
    # propio, para que un proyecto nuevo pueda calcularse de inmediato.
    h_def = models.FloatField("Espesor neto h (ft)", default=42.0)
    phi_def = models.FloatField("Porosidad phi (fracc.)", default=0.20)
    swi_def = models.FloatField("Swi (fracc.)", default=0.22)
    sor_def = models.FloatField("Sor (fracc.)", default=0.25)
    k_def = models.FloatField("Permeabilidad k (md)", default=120.0)
    muw_def = models.FloatField("Viscosidad agua (cp)", default=0.55)
    muo_def = models.FloatField("Viscosidad petroleo (cp)", default=12.0)
    bo_def = models.FloatField("Bo (by/bn)", default=1.18)
    bw_def = models.FloatField("Bw (by/bn)", default=1.02)
    presion_def = models.FloatField("Presion de yacimiento (psi)", default=2900.0)
    temperatura_def = models.FloatField("Temperatura (F)", default=200.0)
    api_def = models.FloatField("Gravedad API", default=27.0)
    rw_def = models.FloatField("Radio de pozo rw (ft)", default=0.354)

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"
        ordering = ["-fecha", "id_proyecto"]

    def __str__(self):
        return f"{self.id_proyecto} · {self.nombre}"

    # -- consultas de conveniencia ------------------------------------------
    @property
    def inyectores(self):
        return self.pozo_set.filter(tipo=TipoPozo.INYECTOR)

    @property
    def productores(self):
        return self.pozo_set.filter(tipo=TipoPozo.PRODUCTOR)

    @property
    def n_inyectores(self):
        return self.inyectores.count()

    @property
    def n_productores(self):
        return self.productores.count()

    @property
    def factor_coord(self):
        """Multiplicador para llevar las coordenadas cargadas a pies."""
        return 3.280839895 if self.unidad_coord == self.UnidadCoord.METROS else 1.0

    @property
    def area_ft2(self):
        return self.area_acres * PIES2_POR_ACRE

    def volumen_poroso_bbl(self):
        """Volumen poroso total del patron, en barriles de yacimiento."""
        return self.area_ft2 * self.h_def * self.phi_def / FT3_POR_BBL

    def poes_bbl(self):
        """Petroleo original en sitio (STB) a partir del area declarada."""
        so = max(0.0, 1.0 - self.swi_def)
        return self.volumen_poroso_bbl() * so / max(self.bo_def, 1e-9)


# ---------------------------------------------------------------------------
# 2. Curvas de permeabilidad relativa
# ---------------------------------------------------------------------------
class CurvaKr(models.Model):
    """Curva krw / kro vs Sw. Base de datos independiente y reutilizable."""

    class Fuente(models.TextChoices):
        SCAL = "SCAL", "Laboratorio SCAL (nucleo)"
        COREY = "COREY", "Correlacion de Corey"
        CAMPO = "CAMPO", "Ajuste a historia de campo"
        LIBRERIA = "LIB", "Curva de libreria"

    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.CASCADE, null=True, blank=True,
        related_name="curvas_kr",
        help_text="Vacio = curva de libreria disponible para cualquier proyecto.",
    )
    nombre = models.CharField("Nombre de la curva", max_length=120)
    tipo_roca = models.CharField("Tipo de roca / facie", max_length=80, blank=True)
    fuente = models.CharField(max_length=8, choices=Fuente.choices, default=Fuente.SCAL)

    # Puntos extremos, utiles para regenerar la curva con Corey.
    swc = models.FloatField("Swc (saturacion de agua connata)", default=0.22)
    sor = models.FloatField("Sor (saturacion residual de petroleo)", default=0.25)
    krw_max = models.FloatField("krw @ Sor", default=0.38)
    kro_max = models.FloatField("kro @ Swc", default=0.90)
    nw = models.FloatField("Exponente Corey agua (nw)", default=2.6)
    no = models.FloatField("Exponente Corey petroleo (no)", default=2.2)

    notas = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Curva de permeabilidad relativa"
        verbose_name_plural = "Curvas de permeabilidad relativa"
        ordering = ["nombre"]

    def __str__(self):
        etiqueta = self.tipo_roca or self.get_fuente_display()
        return f"{self.nombre} ({etiqueta})"

    def tabla(self):
        """[(Sw, krw, kro), ...] ordenada por Sw."""
        return [(p.sw, p.krw, p.kro) for p in self.puntos.all()]

    def generar_corey(self, n=8, guardar=True):
        """Rellena la curva con el modelo de Corey entre Swc y 1 - Sor."""
        puntos = []
        span = (1.0 - self.sor) - self.swc
        for i in range(n):
            sw = self.swc + span * i / (n - 1)
            swn = (sw - self.swc) / span if span > 0 else 0.0
            swn = min(max(swn, 0.0), 1.0)
            krw = self.krw_max * swn ** self.nw
            kro = self.kro_max * (1.0 - swn) ** self.no
            puntos.append((round(sw, 4), round(krw, 6), round(kro, 6)))
        if guardar:
            self.puntos.all().delete()
            PuntoKr.objects.bulk_create(
                [PuntoKr(curva=self, sw=s, krw=w, kro=o, orden=i)
                 for i, (s, w, o) in enumerate(puntos)]
            )
        return puntos


class PuntoKr(models.Model):
    """Un renglon de la tabla Sw / krw / kro."""

    curva = models.ForeignKey(CurvaKr, on_delete=models.CASCADE, related_name="puntos")
    sw = models.FloatField("Sw (fracc.)")
    krw = models.FloatField("krw")
    kro = models.FloatField("kro")
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Punto de curva kr"
        verbose_name_plural = "Puntos de curva kr"
        ordering = ["curva", "sw"]

    def __str__(self):
        return f"Sw={self.sw:.3f} krw={self.krw:.4f} kro={self.kro:.4f}"

    @property
    def razon(self):
        """kro/krw, la razon que se ajusta exponencialmente."""
        return self.kro / self.krw if self.krw > 0 else None


# ---------------------------------------------------------------------------
# 3. Pozos
# ---------------------------------------------------------------------------
class Pozo(models.Model):
    """Inyector o productor, con petrofisica, completacion y levantamiento."""

    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE)
    id_pozo = models.CharField("ID Pozo", max_length=32)
    nombre_pozo = models.CharField("Nombre del pozo", max_length=120)
    tipo = models.CharField(max_length=3, choices=TipoPozo.choices, default=TipoPozo.PRODUCTOR)

    # -- ubicacion (coordenadas de campo, ft o metros UTM: se autoescalan) --
    x = models.FloatField("Coordenada X", default=0.0)
    y = models.FloatField("Coordenada Y", default=0.0)

    # -- petrofisica local -------------------------------------------------
    h = models.FloatField("Espesor neto h (ft)", null=True, blank=True)
    phi = models.FloatField("Porosidad (fracc.)", null=True, blank=True)
    k = models.FloatField("Permeabilidad horizontal kh (md)", null=True, blank=True)
    kv = models.FloatField("Permeabilidad vertical kv (md)", null=True, blank=True)
    swi = models.FloatField("Swi (fracc.)", null=True, blank=True)
    sor = models.FloatField("Sor (fracc.)", null=True, blank=True)

    # -- fluidos -----------------------------------------------------------
    muw = models.FloatField("Viscosidad agua (cp)", null=True, blank=True)
    muo = models.FloatField("Viscosidad petroleo (cp)", null=True, blank=True)
    bo = models.FloatField("Bo (by/bn)", null=True, blank=True)
    bw = models.FloatField("Bw (by/bn)", null=True, blank=True)
    api = models.FloatField("Gravedad API", null=True, blank=True)

    # -- operacion ---------------------------------------------------------
    q = models.FloatField(
        "Caudal (BPD)", default=500.0,
        help_text="Inyector: agua inyectada. Productor: liquido total.",
    )
    pwf = models.FloatField("Presion de fondo fluyente (psi)", null=True, blank=True)
    presion_cabeza = models.FloatField("Presion de cabeza (psi)", null=True, blank=True)
    skin = models.FloatField("Factor de dano (skin)", default=0.0)

    # -- presion capilar / mecanica de fluidos ------------------------------
    pc_entrada = models.FloatField("Presion de entrada Pc (psi)", null=True, blank=True)
    sigma_ow = models.FloatField("Tension interfacial o/w (dina/cm)", null=True, blank=True)
    angulo_contacto = models.FloatField("Angulo de contacto (grados)", null=True, blank=True)

    # -- completacion -------------------------------------------------------
    prof_md = models.FloatField("Profundidad MD (ft)", null=True, blank=True)
    prof_tvd = models.FloatField("Profundidad TVD (ft)", null=True, blank=True)
    tope_arena = models.FloatField("Tope de arena (ft MD)", null=True, blank=True)
    base_arena = models.FloatField("Base de arena (ft MD)", null=True, blank=True)
    diametro_casing = models.FloatField("Diametro de revestidor (pulg)", null=True, blank=True)
    tipo_completacion = models.CharField(
        max_length=8, choices=TipoCompletacion.choices,
        default=TipoCompletacion.CANONEADA, blank=True,
    )

    # -- levantamiento / inyeccion -----------------------------------------
    tipo_levantamiento = models.CharField(
        max_length=4, choices=TipoLevantamiento.choices, default=TipoLevantamiento.BES,
    )
    tipo_bomba_iny = models.CharField(
        max_length=12, choices=TipoBombaInyeccion.choices, default=TipoBombaInyeccion.NA,
    )
    parametros_levantamiento = models.JSONField(
        "Parametros del sistema", default=dict, blank=True,
        help_text="Campos propios del equipo: etapas, Hz, HP, GPM, presion, eficiencia...",
    )

    # -- curva kr asignada --------------------------------------------------
    curva_kr = models.ForeignKey(
        CurvaKr, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="pozos", verbose_name="Curva kr asignada",
    )

    notas = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pozo"
        verbose_name_plural = "Pozos"
        ordering = ["proyecto", "tipo", "id_pozo"]
        constraints = [
            models.UniqueConstraint(fields=["proyecto", "id_pozo"], name="uniq_pozo_por_proyecto"),
        ]

    def __str__(self):
        return f"{self.nombre_pozo} ({self.get_tipo_display()})"

    # -- herencia de valores por defecto del proyecto ----------------------
    def val(self, campo):
        """Valor local del pozo o, si esta vacio, el default del proyecto."""
        propio = getattr(self, campo, None)
        if propio is not None:
            return propio
        return getattr(self.proyecto, f"{campo}_def", None)

    @property
    def es_inyector(self):
        return self.tipo == TipoPozo.INYECTOR

    # Toda la fisica trabaja en pies. Estas dos propiedades son el unico punto
    # donde se aplica la conversion, para que no haya mezcla de unidades.
    @property
    def x_ft(self):
        return self.x * self.proyecto.factor_coord

    @property
    def y_ft(self):
        return self.y * self.proyecto.factor_coord

    def distancia_a(self, otro):
        """Distancia en pies, sin importar la unidad en que se cargo el mapa."""
        return math.hypot(self.x_ft - otro.x_ft, self.y_ft - otro.y_ft)

    def azimut_a(self, otro):
        """Angulo en radianes desde este pozo hacia otro (eje +X = 0)."""
        return math.atan2(otro.y_ft - self.y_ft, otro.x_ft - self.x_ft)

    def kv_kh(self):
        kh, kv = self.val("k"), self.kv
        if kh and kv:
            return kv / kh
        return None

    def movilidad_agua(self):
        """krw_max / muw, indicador de movilidad del agua."""
        muw = self.val("muw")
        if self.curva_kr and muw:
            return self.curva_kr.krw_max / muw
        return None

    def razon_movilidad(self):
        """M = (krw/muw) / (kro/muo) en los extremos. M > 1 = desplazamiento inestable."""
        muw, muo = self.val("muw"), self.val("muo")
        if not (self.curva_kr and muw and muo):
            return None
        return (self.curva_kr.krw_max / muw) / (self.curva_kr.kro_max / muo)


# ---------------------------------------------------------------------------
# 4. Enlace inyector -> productor
# ---------------------------------------------------------------------------
class ParInyeccion(models.Model):
    """Linea de flujo entre un inyector y un productor.

    Es la tabla que permite que un inyector afecte a varios productores y que
    un productor reciba agua de varios inyectores. La permeabilidad direccional
    de cada par es lo que hace que el agua llegue antes a unos pozos que a otros.
    """

    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name="pares")
    inyector = models.ForeignKey(
        Pozo, on_delete=models.CASCADE, related_name="pares_como_inyector",
        limit_choices_to={"tipo": TipoPozo.INYECTOR},
    )
    productor = models.ForeignKey(
        Pozo, on_delete=models.CASCADE, related_name="pares_como_productor",
        limit_choices_to={"tipo": TipoPozo.PRODUCTOR},
    )

    k_direccional = models.FloatField(
        "Permeabilidad direccional (md)", default=100.0,
        help_text="Permeabilidad efectiva del canal inyector-productor. "
                  "Un canal de 100 md conduce el agua ~10 veces mas rapido que uno de 10 md.",
    )
    h_direccional = models.FloatField(
        "Espesor comunicado (ft)", null=True, blank=True,
        help_text="Vacio = usa el espesor del inyector.",
    )
    factor_asignacion = models.FloatField(
        "Factor de asignacion manual", null=True, blank=True,
        help_text="Vacio = se calcula por transmisibilidad k·h/ln(L/rw). "
                  "Un valor fija la fraccion relativa de agua que toma esta linea.",
    )
    ancho_brazo = models.FloatField(
        "Ancho angular del brazo (grados)", default=34.0,
        help_text="Apertura del canal preferencial. Menor valor = digitacion mas marcada.",
    )
    eficiencia_areal = models.FloatField(
        "Eficiencia areal de barrido", default=0.72,
        help_text="Fraccion del area del canal efectivamente barrida.",
    )
    activo = models.BooleanField("Par activo", default=True)
    notas = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Par inyector-productor"
        verbose_name_plural = "Pares inyector-productor"
        ordering = ["proyecto", "inyector", "productor"]
        constraints = [
            models.UniqueConstraint(fields=["inyector", "productor"], name="uniq_par_iny_prod"),
        ]

    def __str__(self):
        return f"{self.inyector.nombre_pozo} → {self.productor.nombre_pozo}"

    @property
    def L(self):
        """Distancia inyector-productor, en ft."""
        return self.inyector.distancia_a(self.productor)

    @property
    def azimut(self):
        return self.inyector.azimut_a(self.productor)

    @property
    def azimut_grados(self):
        return math.degrees(self.azimut) % 360.0

    def espesor(self):
        return self.h_direccional or self.inyector.val("h") or 40.0

    def transmisibilidad(self):
        """k·h / ln(L/rw): peso natural de asignacion de caudal a esta linea."""
        L = max(self.L, 1.0)
        rw = self.inyector.proyecto.rw_def or 0.354
        return self.k_direccional * self.espesor() / max(math.log(L / rw), 0.5)


# ---------------------------------------------------------------------------
# 5. Resultados calculados por pozo
# ---------------------------------------------------------------------------
class ResultadoPozo(models.Model):
    """Cache de los resultados Buckley-Leverett de un productor."""

    pozo = models.OneToOneField(
        Pozo, on_delete=models.CASCADE, related_name="resultado",
        limit_choices_to={"tipo": TipoPozo.PRODUCTOR},
    )

    # Ajuste kro/krw = a·e^(-b·Sw)
    a_ajuste = models.FloatField("a del ajuste", null=True, blank=True)
    b_ajuste = models.FloatField("b del ajuste", null=True, blank=True)
    r2_ajuste = models.FloatField("R² del ajuste", null=True, blank=True)

    # Solucion de Welge
    swf = models.FloatField("Sw del frente", null=True, blank=True)
    fwf = models.FloatField("fw en el frente", null=True, blank=True)
    dfwf = models.FloatField("(dfw/dSw) en el frente", null=True, blank=True)
    sw_prom = models.FloatField("Sw promedio tras el frente", null=True, blank=True)

    # Irrupcion
    L_critica = models.FloatField("Distancia al inyector dominante (ft)", null=True, blank=True)
    tbt_dias = models.FloatField("Tiempo de irrupcion (dias)", null=True, blank=True)
    inyector_critico = models.ForeignKey(
        Pozo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name="Inyector que irrumpe primero",
    )

    # Recobro a la irrupcion
    np_bt = models.FloatField("Np a la irrupcion (bbl)", null=True, blank=True)
    wi_bt = models.FloatField("Agua inyectada a la irrupcion (bbl)", null=True, blank=True)
    ed_bt = models.FloatField("Eficiencia de desplazamiento a BT", null=True, blank=True)
    razon_movilidad = models.FloatField("Razon de movilidad M", null=True, blank=True)

    mensaje = models.CharField(max_length=240, blank=True)
    calculado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Resultado de pozo"
        verbose_name_plural = "Resultados de pozos"

    def __str__(self):
        return f"Resultado · {self.pozo.nombre_pozo}"


# ---------------------------------------------------------------------------
# 6. Economia
# ---------------------------------------------------------------------------
class ParametrosEconomicos(models.Model):
    """Supuestos de OPEX y precio para el analisis economico del proyecto."""

    class Marcador(models.TextChoices):
        BRENT = "BRENT_CRUDE_USD", "Brent"
        WTI = "WTI_USD", "WTI"

    proyecto = models.OneToOneField(
        Proyecto, on_delete=models.CASCADE, related_name="economia",
    )

    # -- ingresos ----------------------------------------------------------
    marcador = models.CharField(
        "Marcador de referencia", max_length=24,
        choices=Marcador.choices, default=Marcador.BRENT,
    )
    precio_manual = models.FloatField(
        "Precio manual (USD/bbl)", null=True, blank=True,
        help_text="Vacio = se consulta el precio en linea (oilpriceapi.com).",
    )
    diferencial = models.FloatField(
        "Diferencial del crudo (USD/bbl)", default=-7.5,
        help_text="Castigo o premio del crudo del campo frente al marcador.",
    )
    regalia = models.FloatField("Regalia / participacion estatal (fracc.)", default=0.125)

    # -- OPEX --------------------------------------------------------------
    costo_iny_agua = models.FloatField(
        "Costo de inyeccion de agua (USD/bbl inyectado)", default=0.85,
        help_text="Bombeo, filtrado y tratamiento del agua de inyeccion.",
    )
    costo_manejo_agua = models.FloatField(
        "Costo de manejo de agua producida (USD/bbl)", default=1.35,
        help_text="Separacion, deshidratacion, quimica y reinyeccion.",
    )
    costo_levantamiento = models.FloatField(
        "Costo de levantamiento (USD/bbl liquido)", default=2.10,
    )
    costo_tratamiento_crudo = models.FloatField(
        "Tratamiento y transporte del crudo (USD/bbl)", default=1.80,
    )
    costo_quimicos = models.FloatField(
        "Quimicos (USD/bbl agua producida)", default=0.28,
    )
    opex_fijo_mes = models.FloatField("OPEX fijo (USD/mes)", default=48000.0)
    capex_inicial = models.FloatField("CAPEX inicial del proyecto (USD)", default=1850000.0)

    # -- perfil de produccion ----------------------------------------------
    class Base(models.TextChoices):
        CORTE = "CORTE", "Partir del corte de agua (el petroleo se deduce)"
        CAUDAL = "CAUDAL", "Partir del caudal de petroleo (el corte se deduce)"

    base_produccion = models.CharField(
        "Base del perfil", max_length=8, choices=Base.choices, default=Base.CORTE,
        help_text="El liquido total lo fijan los pozos. Elija cual de los dos "
                  "valores manda; el otro se calcula para no romper el balance.",
    )
    qo_inicial = models.FloatField(
        "Caudal de petroleo inicial (BOPD)", default=520.0,
        help_text="Se usa como dato de partida en modo CAUDAL, y como respaldo "
                  "cuando el proyecto todavia no tiene productores con caudal.",
    )
    declinacion_anual = models.FloatField("Declinacion anual (fracc.)", default=0.12)
    corte_agua_inicial = models.FloatField(
        "Corte de agua inicial (fracc.)", default=0.70,
        help_text="Corte del patron antes de la primera irrupcion.",
    )

    # -- financiero ---------------------------------------------------------
    tasa_descuento = models.FloatField("Tasa de descuento anual (fracc.)", default=0.12)
    horizonte_meses = models.PositiveIntegerField("Horizonte de evaluacion (meses)", default=120)
    limite_economico_bopd = models.FloatField(
        "Limite economico (BOPD)", default=25.0,
        help_text="Caudal por debajo del cual se abandona el patron.",
    )

    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Parametros economicos"
        verbose_name_plural = "Parametros economicos"

    def __str__(self):
        return f"Economia · {self.proyecto.id_proyecto}"


class PrecioCrudo(models.Model):
    """Historico de cotizaciones traidas de la API, para auditoria y respaldo."""

    codigo = models.CharField(max_length=32, db_index=True)
    precio = models.FloatField("Precio (USD/bbl)")
    moneda = models.CharField(max_length=8, default="USD")
    tipo = models.CharField(max_length=32, blank=True)
    as_of = models.DateTimeField("Vigencia del dato", null=True, blank=True)
    obtenido_en = models.DateTimeField(auto_now_add=True)
    exitoso = models.BooleanField(default=True)
    detalle = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Cotizacion de crudo"
        verbose_name_plural = "Cotizaciones de crudo"
        ordering = ["-obtenido_en"]

    def __str__(self):
        return f"{self.codigo} · {self.precio:.2f} USD/bbl"
