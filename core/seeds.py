"""Dos ejemplos completos, con datos coherentes de campo.

Ejemplo 1 - Patron irregular con dos inyectores (coordenadas UTM en metros).
            I-1 alimenta a 4 de los 5 productores, I-2 a 3 de los 5.
            P-3 y P-4 reciben agua de ambos inyectores.

Ejemplo 2 - Un solo inyector rodeado de 6 productores (coordenadas en pies).
            La permeabilidad direccional va de 28 md a 380 md, de modo que el
            agua llega a cada pozo en un tiempo distinto.

Los valores son representativos de arenas de la cuenca Oriente: crudo de
21-24 API, arenas U/T de 30-45 ft, levantamiento con BES, PCP y jet.
"""
import datetime

from django.db import transaction

from .models import (CurvaKr, ParametrosEconomicos, ParInyeccion, Pozo,
                     Proyecto, TipoBombaInyeccion, TipoCompletacion,
                     TipoLevantamiento, TipoPozo)


def _curva(proyecto, nombre, tipo_roca, swc, sor, krw_max, kro_max, nw, no, fuente):
    c = CurvaKr.objects.create(
        proyecto=proyecto, nombre=nombre, tipo_roca=tipo_roca, fuente=fuente,
        swc=swc, sor=sor, krw_max=krw_max, kro_max=kro_max, nw=nw, no=no,
        notas="Puntos generados con el modelo de Corey a partir de los "
              "extremos medidos en nucleo.",
    )
    c.generar_corey(n=9)
    return c


# ===========================================================================
# Ejemplo 1
# ===========================================================================
@transaction.atomic
def ejemplo_dos_inyectores(reemplazar=True) -> Proyecto:
    ID = "BL-2026-001"
    if reemplazar:
        Proyecto.objects.filter(id_proyecto=ID).delete()

    p = Proyecto.objects.create(
        id_proyecto=ID,
        nombre="Inyeccion de agua · Patron Norte, arena U Inferior",
        fecha=datetime.date(2026, 3, 18),
        bloque="Bloque 43",
        campo="Yuturi Este",
        operadora="Consorcio Operativo Oriente",
        yacimiento="U Inferior",
        pozos=7,
        area_acres=210.0,
        unidad_coord=Proyecto.UnidadCoord.METROS,
        descripcion=(
            "Patron irregular de siete pozos. El inyector I-1 comunica con "
            "cuatro productores y el I-2 con tres; P-3 y P-4 reciben agua de "
            "los dos. El canal I-1 → P-3 (420 md) es el que gobierna la "
            "irrupcion temprana del patron."
        ),
        h_def=38.0, phi_def=0.19, swi_def=0.24, sor_def=0.26, k_def=250.0,
        muw_def=0.48, muo_def=14.0, bo_def=1.16, bw_def=1.02,
        presion_def=3150.0, temperatura_def=210.0, api_def=23.0, rw_def=0.354,
    )

    limpia = _curva(p, "U Inferior · facie limpia", "Arenisca cuarzosa",
                    0.22, 0.24, 0.36, 0.94, 2.7, 2.3, CurvaKr.Fuente.SCAL)
    sucia = _curva(p, "U Inferior · facie arcillosa", "Arenisca con arcilla",
                   0.28, 0.30, 0.24, 0.82, 3.2, 2.0, CurvaKr.Fuente.SCAL)
    media = _curva(p, "U Inferior · facie intermedia", "Arenisca media",
                   0.24, 0.26, 0.31, 0.90, 2.9, 2.2, CurvaKr.Fuente.CAMPO)

    def pozo(**kw):
        return Pozo.objects.create(proyecto=p, **kw)

    # -- inyectores --------------------------------------------------------
    i1 = pozo(
        id_pozo="I-1", nombre_pozo="YUT-I-001", tipo=TipoPozo.INYECTOR,
        x=341200.0, y=9902400.0, q=4200.0,
        h=41.0, phi=0.20, k=280.0, kv=48.0, swi=0.23, sor=0.25,
        muw=0.48, muo=14.0, bw=1.02, presion_cabeza=1980.0, skin=-1.2,
        prof_md=9820.0, prof_tvd=9640.0, tope_arena=9598.0, base_arena=9639.0,
        diametro_casing=7.0, tipo_completacion=TipoCompletacion.CANONEADA,
        tipo_levantamiento=TipoLevantamiento.INY_RECRIPROACTE,
        tipo_bomba_iny=TipoBombaInyeccion.QUINTUPLEX,
        curva_kr=limpia,
        parametros_levantamiento={
            "marca": "Gardner Denver", "modelo": "TEE-3000",
            "pistones": 5, "carrera_pulg": 5.0, "presion_maxima_psi": 4500,
            "caudal_maximo_bpd": 7800, "potencia_hp": 900,
            "eficiencia_volumetrica": 0.94, "velocidad_rpm": 320,
            "fluido": "Agua de formacion tratada",
        },
        notas="Inyector principal del patron. Prueba de trazadores confirma "
              "comunicacion preferencial hacia el sureste.",
    )
    i2 = pozo(
        id_pozo="I-2", nombre_pozo="YUT-I-002", tipo=TipoPozo.INYECTOR,
        x=342600.0, y=9902900.0, q=3100.0,
        h=35.0, phi=0.18, k=195.0, kv=26.0, swi=0.25, sor=0.27,
        muw=0.48, muo=14.0, bw=1.02, presion_cabeza=2240.0, skin=0.8,
        prof_md=9915.0, prof_tvd=9702.0, tope_arena=9666.0, base_arena=9701.0,
        diametro_casing=7.0, tipo_completacion=TipoCompletacion.SELECTIVA,
        tipo_levantamiento=TipoLevantamiento.INY_RECRIPROACTE,
        tipo_bomba_iny=TipoBombaInyeccion.TRIPLEX,
        curva_kr=media,
        parametros_levantamiento={
            "marca": "Weatherford", "modelo": "T-2200",
            "pistones": 3, "carrera_pulg": 6.0, "presion_maxima_psi": 3800,
            "caudal_maximo_bpd": 5200, "potencia_hp": 650,
            "eficiencia_volumetrica": 0.91, "velocidad_rpm": 290,
            "fluido": "Agua de formacion tratada",
        },
        notas="Inyector secundario. Completacion selectiva por presencia de "
              "una lutita de 4 ft dentro de la arena.",
    )

    # -- productores -------------------------------------------------------
    p1 = pozo(
        id_pozo="P-1", nombre_pozo="YUT-A-014", tipo=TipoPozo.PRODUCTOR,
        x=340450.0, y=9902850.0, q=1350.0,
        h=39.0, phi=0.195, k=210.0, kv=31.0, swi=0.24, sor=0.26,
        muw=0.48, muo=13.5, bo=1.165, bw=1.02, api=23.4,
        pwf=1180.0, skin=2.4, sigma_ow=26.0, angulo_contacto=30.0,
        prof_md=9740.0, prof_tvd=9585.0, tope_arena=9544.0, base_arena=9583.0,
        diametro_casing=7.0, tipo_completacion=TipoCompletacion.CANONEADA,
        tipo_levantamiento=TipoLevantamiento.BES, curva_kr=limpia,
        parametros_levantamiento={
            "serie": "538", "modelo": "P-23", "etapas": 178,
            "frecuencia_hz": 54.0, "motor_hp": 195, "eficiencia": 0.62,
            "profundidad_bomba_ft": 9180, "sumergencia_ft": 620,
        },
    )
    p2 = pozo(
        id_pozo="P-2", nombre_pozo="YUT-A-021", tipo=TipoPozo.PRODUCTOR,
        x=340700.0, y=9901750.0, q=880.0,
        h=31.0, phi=0.165, k=48.0, kv=5.2, swi=0.28, sor=0.30,
        muw=0.50, muo=16.5, bo=1.14, bw=1.02, api=21.6,
        pwf=1420.0, skin=4.8, sigma_ow=24.0, angulo_contacto=35.0,
        prof_md=9905.0, prof_tvd=9668.0, tope_arena=9639.0, base_arena=9670.0,
        diametro_casing=7.0, tipo_completacion=TipoCompletacion.LINER_RANURADO,
        tipo_levantamiento=TipoLevantamiento.PCP, curva_kr=sucia,
        parametros_levantamiento={
            "modelo": "60-N-1200", "velocidad_rpm": 215, "torque_lb_ft": 940,
            "elastomero": "NBR alto nitrilo", "profundidad_bomba_ft": 8950,
            "eficiencia": 0.58,
        },
        notas="Facie arcillosa. Canal de baja permeabilidad hacia el inyector: "
              "es el ultimo pozo del patron en ver el agua.",
    )
    p3 = pozo(
        id_pozo="P-3", nombre_pozo="YUT-A-008", tipo=TipoPozo.PRODUCTOR,
        x=341900.0, y=9902100.0, q=1620.0,
        h=44.0, phi=0.215, k=430.0, kv=88.0, swi=0.22, sor=0.24,
        muw=0.47, muo=12.8, bo=1.175, bw=1.02, api=24.1,
        pwf=1050.0, skin=-0.6, sigma_ow=27.0, angulo_contacto=28.0,
        prof_md=9688.0, prof_tvd=9552.0, tope_arena=9506.0, base_arena=9550.0,
        diametro_casing=7.0, tipo_completacion=TipoCompletacion.CANONEADA,
        tipo_levantamiento=TipoLevantamiento.BES, curva_kr=limpia,
        parametros_levantamiento={
            "serie": "562", "modelo": "P-47", "etapas": 142,
            "frecuencia_hz": 58.0, "motor_hp": 260, "eficiencia": 0.66,
            "profundidad_bomba_ft": 9020, "sumergencia_ft": 780,
        },
        notas="Pozo de mayor permeabilidad del patron y el mas cercano al "
              "canal de alta conductividad de I-1. Primera irrupcion esperada.",
    )
    p4 = pozo(
        id_pozo="P-4", nombre_pozo="YUT-A-017", tipo=TipoPozo.PRODUCTOR,
        x=341750.0, y=9903050.0, q=1180.0,
        h=36.0, phi=0.185, k=130.0, kv=18.0, swi=0.25, sor=0.27,
        muw=0.48, muo=14.8, bo=1.155, bw=1.02, api=22.7,
        pwf=1290.0, skin=1.9, sigma_ow=25.0, angulo_contacto=32.0,
        prof_md=9802.0, prof_tvd=9618.0, tope_arena=9581.0, base_arena=9617.0,
        diametro_casing=7.0, tipo_completacion=TipoCompletacion.CANONEADA,
        tipo_levantamiento=TipoLevantamiento.BES, curva_kr=media,
        parametros_levantamiento={
            "serie": "538", "modelo": "P-18", "etapas": 205,
            "frecuencia_hz": 52.0, "motor_hp": 175, "eficiencia": 0.60,
            "profundidad_bomba_ft": 9110, "sumergencia_ft": 540,
        },
        notas="Recibe agua de los dos inyectores; el aporte de I-2 llega "
              "antes por el canal de 140 md.",
    )
    p5 = pozo(
        id_pozo="P-5", nombre_pozo="YUT-B-004", tipo=TipoPozo.PRODUCTOR,
        x=343350.0, y=9902550.0, q=1240.0,
        h=37.0, phi=0.19, k=305.0, kv=52.0, swi=0.235, sor=0.255,
        muw=0.48, muo=13.2, bo=1.17, bw=1.02, api=23.8,
        pwf=1150.0, skin=0.4, sigma_ow=26.5, angulo_contacto=30.0,
        prof_md=9860.0, prof_tvd=9675.0, tope_arena=9637.0, base_arena=9674.0,
        diametro_casing=7.0, tipo_completacion=TipoCompletacion.CANONEADA,
        tipo_levantamiento=TipoLevantamiento.BH, curva_kr=limpia,
        parametros_levantamiento={
            "tipo": "Bomba jet", "garganta_tobera": "11-J",
            "presion_superficie_psi": 3600, "caudal_motriz_bpd": 1900,
            "fluido_motriz": "Agua tratada", "relacion_area": 0.40,
            "profundidad_bomba_ft": 9250, "eficiencia": 0.31,
        },
        notas="Unico pozo alimentado solo por I-2.",
    )

    # -- pares inyector -> productor ---------------------------------------
    def par(iny, prod, k, ancho, notas=""):
        ParInyeccion.objects.create(
            proyecto=p, inyector=iny, productor=prod, k_direccional=k,
            ancho_brazo=ancho, notas=notas,
        )

    # I-1 alimenta a cuatro productores
    par(i1, p3, 420.0, 26.0, "Canal de alta conductividad confirmado con trazador.")
    par(i1, p1, 180.0, 34.0, "Comunicacion franca por la facie limpia.")
    par(i1, p4, 95.0, 38.0, "Aporte moderado, compartido con I-2.")
    par(i1, p2, 35.0, 44.0, "Barrera parcial de arcilla: canal lento y ancho.")
    # I-2 alimenta a tres productores
    par(i2, p5, 310.0, 28.0, "Direccion preferencial hacia el este.")
    par(i2, p4, 140.0, 32.0, "Segundo aporte a P-4.")
    par(i2, p3, 60.0, 40.0, "Aporte tardio y secundario a P-3.")

    ParametrosEconomicos.objects.create(
        proyecto=p,
        marcador=ParametrosEconomicos.Marcador.BRENT,
        diferencial=-8.20, regalia=0.125,
        costo_iny_agua=0.92, costo_manejo_agua=1.45, costo_levantamiento=2.35,
        costo_tratamiento_crudo=1.90, costo_quimicos=0.31,
        opex_fijo_mes=62000.0, capex_inicial=2450000.0,
        qo_inicial=2383.0, declinacion_anual=0.11, corte_agua_inicial=0.62,
        tasa_descuento=0.12, horizonte_meses=120, limite_economico_bopd=30.0,
    )
    return p


# ===========================================================================
# Ejemplo 2
# ===========================================================================
@transaction.atomic
def ejemplo_un_inyector(reemplazar=True) -> Proyecto:
    ID = "BL-2026-002"
    if reemplazar:
        Proyecto.objects.filter(id_proyecto=ID).delete()

    p = Proyecto.objects.create(
        id_proyecto=ID,
        nombre="Inyeccion radial · Patron estrella, arena T Principal",
        fecha=datetime.date(2026, 6, 2),
        bloque="Bloque 12",
        campo="Sacha Sur",
        operadora="Petroamazonas EP",
        yacimiento="T Principal",
        pozos=7,
        area_acres=145.0,
        unidad_coord=Proyecto.UnidadCoord.PIES,
        descripcion=(
            "Un inyector central rodeado por seis productores. La "
            "permeabilidad direccional va de 9 md al suroeste hasta 430 md "
            "al este, asi que el frente sale muy deformado y el agua llega a "
            "cada pozo en un momento distinto: de nueve meses en P-201 a mas "
            "de siete anos en P-205. P-201 y P-206 comparten canales igual de "
            "buenos y se separan solo por la distancia."
        ),
        h_def=45.0, phi_def=0.21, swi_def=0.23, sor_def=0.25, k_def=160.0,
        muw_def=0.52, muo_def=11.5, bo_def=1.21, bw_def=1.03,
        presion_def=3480.0, temperatura_def=218.0, api_def=26.5, rw_def=0.354,
    )

    principal = _curva(p, "T Principal · SCAL pozo 205", "Arenisca fina",
                       0.23, 0.25, 0.33, 0.91, 2.8, 2.2, CurvaKr.Fuente.SCAL)
    marginal = _curva(p, "T Principal · borde de arena", "Arenisca sucia",
                      0.27, 0.29, 0.22, 0.80, 3.4, 1.9, CurvaKr.Fuente.COREY)

    def pozo(**kw):
        return Pozo.objects.create(proyecto=p, **kw)

    iny = pozo(
        id_pozo="I-101", nombre_pozo="SAC-I-101", tipo=TipoPozo.INYECTOR,
        x=0.0, y=0.0, q=5400.0,
        h=47.0, phi=0.22, k=190.0, kv=34.0, swi=0.23, sor=0.25,
        muw=0.52, muo=11.5, bw=1.03, presion_cabeza=2350.0, skin=-2.1,
        prof_md=10250.0, prof_tvd=10040.0, tope_arena=9992.0, base_arena=10039.0,
        diametro_casing=9.625, tipo_completacion=TipoCompletacion.CANONEADA,
        tipo_levantamiento=TipoLevantamiento.INY_HPS,
        tipo_bomba_iny=TipoBombaInyeccion.HPS,
        curva_kr=principal,
        parametros_levantamiento={
            "tipo": "Bomba horizontal multietapa de superficie",
            "marca": "REDA", "etapas": 62, "potencia_hp": 1250,
            "presion_descarga_psi": 2900, "caudal_bpd": 6000,
            "eficiencia": 0.71, "velocidad_rpm": 3560,
            "fluido": "Mezcla agua de formacion y agua fresca",
        },
        notas="Inyector central del patron estrella. Registro de trazadores "
              "muestra una anisotropia marcada este-oeste.",
    )

    # Los seis canales estan calibrados para que la irrupcion ocurra en seis
    # momentos claramente distintos: 280, 552, 933, 1516, 2290 y 2763 dias.
    # P-201 y P-206 tienen canales igual de buenos (420 y 430 md) y se separan
    # solo por distancia; en el resto manda la permeabilidad.
    #
    # (id, nombre, x, y, q, k_dir, ancho, h, phi, k, kv, swi, sor, muo, api,
    #  levantamiento, curva, nota)
    fichas = [
        ("P-201", "SAC-A-201", 1500.0, 350.0, 1480.0, 420.0, 24.0,
         49.0, 0.225, 435.0, 84.0, 0.22, 0.24, 10.8, 27.2,
         TipoLevantamiento.BES, principal,
         "El mas cercano y por el mejor canal: primera irrupcion del patron, "
         "a los nueve meses."),
        ("P-202", "SAC-A-202", 2300.0, 1750.0, 1150.0, 120.0, 32.0,
         42.0, 0.19, 132.0, 17.0, 0.245, 0.265, 12.1, 25.9,
         TipoLevantamiento.BES, principal,
         "El pozo mas lejano del inyector y por un canal apenas moderado: "
         "la distancia pesa al cuadrado en el tiempo de irrupcion."),
        ("P-203", "SAC-A-203", 250.0, 2350.0, 1240.0, 290.0, 30.0,
         45.0, 0.21, 305.0, 54.0, 0.23, 0.25, 11.2, 26.8,
         TipoLevantamiento.PCP, principal,
         "Buen canal hacia el norte, pero mas lejos que P-201."),
        ("P-204", "SAC-A-204", -1900.0, 800.0, 870.0, 78.0, 38.0,
         38.0, 0.18, 84.0, 9.6, 0.26, 0.28, 12.8, 25.3,
         TipoLevantamiento.BM, marginal,
         "Hacia el borde de la arena: la permeabilidad cae y el agua se demora "
         "cuatro anos pese a estar relativamente cerca."),
        ("P-205", "SAC-A-205", -1350.0, -1850.0, 610.0, 9.0, 48.0,
         31.0, 0.155, 11.0, 0.9, 0.29, 0.31, 14.6, 24.1,
         TipoLevantamiento.BM, marginal,
         "Canal practicamente cerrado por cemento y arcilla. Recibe agua solo "
         "por el avance matricial: es el ultimo del patron."),
        ("P-206", "SAC-A-206", 850.0, -1950.0, 1320.0, 430.0, 26.0,
         48.0, 0.22, 445.0, 91.0, 0.225, 0.245, 10.9, 27.0,
         TipoLevantamiento.BH, principal,
         "Canal tan bueno como el de P-201; irrumpe despues solo porque esta "
         "mas lejos. Es el par que muestra el efecto puro de la distancia."),
    ]

    lift_params = {
        TipoLevantamiento.BES: {
            "serie": "562", "modelo": "P-35", "etapas": 160,
            "frecuencia_hz": 56.0, "motor_hp": 225, "eficiencia": 0.64,
            "profundidad_bomba_ft": 9500, "sumergencia_ft": 700,
        },
        TipoLevantamiento.PCP: {
            "modelo": "40-N-1600", "velocidad_rpm": 240, "torque_lb_ft": 810,
            "elastomero": "NBR", "profundidad_bomba_ft": 9300, "eficiencia": 0.60,
        },
        TipoLevantamiento.BM: {
            "unidad": "C-456D-256-120", "carrera_pulg": 120,
            "emboladas_por_minuto": 7.5, "diametro_piston_pulg": 2.25,
            "varillas": "API 76 grado D", "profundidad_bomba_ft": 8700,
            "eficiencia": 0.72,
        },
        TipoLevantamiento.BH: {
            "tipo": "Bomba jet", "garganta_tobera": "10-I",
            "presion_superficie_psi": 3400, "caudal_motriz_bpd": 1650,
            "fluido_motriz": "Agua tratada", "relacion_area": 0.38,
            "profundidad_bomba_ft": 9600, "eficiencia": 0.29,
        },
    }

    for (idp, nom, x, y, q, kdir, ancho, h, phi, k, kv, swi, sor,
         muo, api, lev, curva, nota) in fichas:
        prod = pozo(
            id_pozo=idp, nombre_pozo=nom, tipo=TipoPozo.PRODUCTOR,
            x=x, y=y, q=q,
            h=h, phi=phi, k=k, kv=kv, swi=swi, sor=sor,
            muw=0.52, muo=muo, bo=1.21, bw=1.03, api=api,
            pwf=1250.0, skin=1.5, sigma_ow=25.5, angulo_contacto=31.0,
            prof_md=10180.0, prof_tvd=9985.0,
            tope_arena=9940.0, base_arena=9984.0,
            diametro_casing=7.0, tipo_completacion=TipoCompletacion.CANONEADA,
            tipo_levantamiento=lev, curva_kr=curva,
            parametros_levantamiento=dict(lift_params[lev]),
            notas=nota,
        )
        ParInyeccion.objects.create(
            proyecto=p, inyector=iny, productor=prod,
            k_direccional=kdir, ancho_brazo=ancho, notas=nota,
        )

    ParametrosEconomicos.objects.create(
        proyecto=p,
        marcador=ParametrosEconomicos.Marcador.WTI,
        diferencial=-6.40, regalia=0.125,
        costo_iny_agua=0.78, costo_manejo_agua=1.28, costo_levantamiento=2.05,
        costo_tratamiento_crudo=1.72, costo_quimicos=0.26,
        opex_fijo_mes=51000.0, capex_inicial=1980000.0,
        qo_inicial=2001.0, declinacion_anual=0.13, corte_agua_inicial=0.70,
        tasa_descuento=0.12, horizonte_meses=120, limite_economico_bopd=25.0,
    )
    return p


def crear_todos(reemplazar=True):
    return [ejemplo_dos_inyectores(reemplazar), ejemplo_un_inyector(reemplazar)]
