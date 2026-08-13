"""Vistas del simulador.

Las paginas se sirven con plantillas de Django; la pestana de estudio ademas
consume un pequeno API JSON para que la edicion de pozos y la barra de tiempo
sean inmediatas.
"""
import json

from django.contrib import messages
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from . import economics, engine, oilprice, seeds
from .forms import EconomiaForm, ProyectoForm
from .models import (CurvaKr, ParInyeccion, Pozo, Proyecto, PuntoKr,
                     TipoBombaInyeccion, TipoCompletacion, TipoLevantamiento,
                     TipoPozo)


# ===========================================================================
# Proyectos
# ===========================================================================
def proyectos(request):
    lista = (Proyecto.objects.all()
             .annotate(
                 n_iny=Count("pozo", filter=Q(pozo__tipo=TipoPozo.INYECTOR), distinct=True),
                 n_pro=Count("pozo", filter=Q(pozo__tipo=TipoPozo.PRODUCTOR), distinct=True),
                 n_par=Count("pares", distinct=True),
             ))
    return render(request, "core/proyectos.html", {
        "seccion": "proyectos",
        "lista": lista,
        "hay_ejemplos": Proyecto.objects.filter(
            id_proyecto__in=["BL-2026-001", "BL-2026-002"]).count(),
    })


@require_http_methods(["GET", "POST"])
def proyecto_form(request, pk=None):
    obj = get_object_or_404(Proyecto, pk=pk) if pk else None
    if request.method == "POST":
        form = ProyectoForm(request.POST, instance=obj)
        if form.is_valid():
            p = form.save()
            economics.parametros_de(p)          # crea supuestos por defecto
            if obj is None:
                _curva_inicial(p)
                messages.success(
                    request,
                    f"Proyecto {p.id_proyecto} creado. Se cargó una curva kr "
                    "por defecto; agregue los pozos en la pestaña Estudio.")
            else:
                messages.success(request, "Proyecto actualizado.")
            return redirect("core:estudio", pk=p.pk)
    else:
        form = ProyectoForm(instance=obj)
    return render(request, "core/proyecto_form.html", {
        "seccion": "proyectos", "form": form, "obj": obj, "proyecto": obj,
    })


def _curva_inicial(proyecto):
    c = CurvaKr.objects.create(
        proyecto=proyecto, nombre="Curva base del proyecto",
        tipo_roca="Arenisca", fuente=CurvaKr.Fuente.COREY,
        swc=proyecto.swi_def, sor=proyecto.sor_def,
        krw_max=0.32, kro_max=0.90, nw=2.8, no=2.2,
        notas="Generada con Corey a partir de los valores por defecto del "
              "proyecto. Reemplácela con datos de laboratorio cuando los tenga.",
    )
    c.generar_corey(n=9)
    return c


@require_POST
def proyecto_eliminar(request, pk):
    p = get_object_or_404(Proyecto, pk=pk)
    nombre = p.id_proyecto
    p.delete()
    messages.success(request, f"Proyecto {nombre} eliminado.")
    return redirect("core:proyectos")


@require_POST
def cargar_ejemplos(request):
    creados = seeds.crear_todos(reemplazar=True)
    for p in creados:
        engine.analizar_proyecto(p)
    messages.success(
        request, "Se cargaron los dos proyectos de ejemplo con sus resultados.")
    return redirect("core:estudio", pk=creados[0].pk)


# ===========================================================================
# Estudio: entradas + resultados
# ===========================================================================
def estudio(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk)
    datos = engine.analizar_proyecto(proyecto)
    activo = request.GET.get("pozo")
    if activo:
        try:
            activo = int(activo)
        except ValueError:
            activo = None
    if not activo and datos["productores"]:
        activo = datos["productores"][0]["id"]

    return render(request, "core/estudio.html", {
        "seccion": "estudio",
        "proyecto": proyecto,
        "datos": datos,
        "activo": activo,
        "pozos": _pozos_payload(proyecto),
        "curvas": list(CurvaKr.objects.filter(
            Q(proyecto=proyecto) | Q(proyecto__isnull=True)
        ).values("id", "nombre")),
        "opciones": _opciones(),
        "todos_proyectos": Proyecto.objects.all().only("id", "id_proyecto", "nombre"),
    })


def _opciones():
    return {
        "levantamiento": TipoLevantamiento.choices,
        "bomba": TipoBombaInyeccion.choices,
        "completacion": TipoCompletacion.choices,
    }


def _pozos_payload(proyecto):
    """Estructura editable de pozos, pares y curvas para el panel de entrada."""
    pozos = list(Pozo.objects.filter(proyecto=proyecto)
                 .select_related("curva_kr", "proyecto").order_by("tipo", "id_pozo"))
    pares = list(ParInyeccion.objects.filter(proyecto=proyecto)
                 .select_related("inyector__proyecto", "productor__proyecto"))
    return {
        "pozos": [{
            "id": p.id, "id_pozo": p.id_pozo, "nombre_pozo": p.nombre_pozo,
            "tipo": p.tipo, "x": p.x, "y": p.y, "q": p.q,
            "h": p.h, "phi": p.phi, "k": p.k, "kv": p.kv,
            "swi": p.swi, "sor": p.sor, "muw": p.muw, "muo": p.muo,
            "bo": p.bo, "bw": p.bw, "api": p.api,
            "pwf": p.pwf, "presion_cabeza": p.presion_cabeza, "skin": p.skin,
            "pc_entrada": p.pc_entrada, "sigma_ow": p.sigma_ow,
            "angulo_contacto": p.angulo_contacto,
            "prof_md": p.prof_md, "prof_tvd": p.prof_tvd,
            "tope_arena": p.tope_arena, "base_arena": p.base_arena,
            "diametro_casing": p.diametro_casing,
            "tipo_completacion": p.tipo_completacion,
            "tipo_levantamiento": p.tipo_levantamiento,
            "tipo_bomba_iny": p.tipo_bomba_iny,
            "parametros_levantamiento": p.parametros_levantamiento or {},
            "curva_kr": p.curva_kr_id,
            "notas": p.notas,
        } for p in pozos],
        "pares": [{
            "id": q.id, "inyector": q.inyector_id, "productor": q.productor_id,
            "k_direccional": q.k_direccional, "ancho_brazo": q.ancho_brazo,
            "h_direccional": q.h_direccional,
            "factor_asignacion": q.factor_asignacion,
            "eficiencia_areal": q.eficiencia_areal,
            "activo": q.activo, "notas": q.notas,
            "L": round(q.L, 1),
        } for q in pares],
        "defaults": {
            "h": proyecto.h_def, "phi": proyecto.phi_def, "swi": proyecto.swi_def,
            "sor": proyecto.sor_def, "k": proyecto.k_def, "muw": proyecto.muw_def,
            "muo": proyecto.muo_def, "bo": proyecto.bo_def, "bw": proyecto.bw_def,
        },
        "unidad": proyecto.unidad_coord,
    }


# ===========================================================================
# API JSON
# ===========================================================================
def _num(v):
    if v in (None, "", "null"):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


CAMPOS_NUM = ["x", "y", "q", "h", "phi", "k", "kv", "swi", "sor", "muw", "muo",
              "bo", "bw", "api", "pwf", "presion_cabeza", "skin", "pc_entrada",
              "sigma_ow", "angulo_contacto", "prof_md", "prof_tvd", "tope_arena",
              "base_arena", "diametro_casing"]
CAMPOS_TXT = ["id_pozo", "nombre_pozo", "tipo_completacion",
              "tipo_levantamiento", "tipo_bomba_iny", "notas"]


@require_POST
def api_pozo_guardar(request, pk):
    pozo = get_object_or_404(Pozo, pk=pk)
    datos = json.loads(request.body or "{}")
    for campo in CAMPOS_NUM:
        if campo in datos:
            valor = _num(datos[campo])
            if campo in ("x", "y", "q", "skin") and valor is None:
                valor = 0.0
            setattr(pozo, campo, valor)
    for campo in CAMPOS_TXT:
        if campo in datos and datos[campo] is not None:
            setattr(pozo, campo, str(datos[campo])[:120])
    if "curva_kr" in datos:
        pozo.curva_kr_id = datos["curva_kr"] or None
    if "parametros_levantamiento" in datos and isinstance(
            datos["parametros_levantamiento"], dict):
        pozo.parametros_levantamiento = datos["parametros_levantamiento"]
    try:
        pozo.save()
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
    return JsonResponse({"ok": True, "analisis": engine.analizar_proyecto(pozo.proyecto)})


@require_POST
def api_pozo_crear(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk)
    datos = json.loads(request.body or "{}")
    tipo = TipoPozo.INYECTOR if datos.get("tipo") == "INY" else TipoPozo.PRODUCTOR

    existentes = Pozo.objects.filter(proyecto=proyecto, tipo=tipo).count()
    pref = "I" if tipo == TipoPozo.INYECTOR else "P"
    n = existentes + 1
    while Pozo.objects.filter(proyecto=proyecto, id_pozo=f"{pref}-{n}").exists():
        n += 1

    # Se coloca el pozo nuevo en un punto libre alrededor del centro del patron
    otros = list(Pozo.objects.filter(proyecto=proyecto))
    if otros:
        cx = sum(o.x for o in otros) / len(otros)
        cy = sum(o.y for o in otros) / len(otros)
        radio = max((max(abs(o.x - cx), abs(o.y - cy)) for o in otros), default=0) or 800
    else:
        cx = cy = 0.0
        radio = 800.0 if proyecto.unidad_coord == Proyecto.UnidadCoord.PIES else 250.0
    import math
    ang = math.radians(40 * len(otros))
    escala = 0.55 if tipo == TipoPozo.INYECTOR else 1.05

    curva = CurvaKr.objects.filter(proyecto=proyecto).first()
    pozo = Pozo.objects.create(
        proyecto=proyecto, tipo=tipo, id_pozo=f"{pref}-{n}",
        nombre_pozo=f"{'Inyector' if tipo == TipoPozo.INYECTOR else 'Productor'} {n}",
        x=round(cx + radio * escala * math.cos(ang), 1),
        y=round(cy + radio * escala * math.sin(ang), 1),
        q=3000.0 if tipo == TipoPozo.INYECTOR else 900.0,
        curva_kr=curva,
        tipo_levantamiento=(TipoLevantamiento.INY_RECRIPROACTE if tipo == TipoPozo.INYECTOR
                            else TipoLevantamiento.BES),
        tipo_bomba_iny=(TipoBombaInyeccion.TRIPLEX if tipo == TipoPozo.INYECTOR
                        else TipoBombaInyeccion.NA),
    )

    # Conexion automatica: un pozo nuevo se enlaza con los del tipo contrario
    if tipo == TipoPozo.INYECTOR:
        for prod in Pozo.objects.filter(proyecto=proyecto, tipo=TipoPozo.PRODUCTOR):
            ParInyeccion.objects.get_or_create(
                inyector=pozo, productor=prod,
                defaults={"proyecto": proyecto, "k_direccional": proyecto.k_def})
    else:
        for iny in Pozo.objects.filter(proyecto=proyecto, tipo=TipoPozo.INYECTOR):
            ParInyeccion.objects.get_or_create(
                inyector=iny, productor=pozo,
                defaults={"proyecto": proyecto, "k_direccional": proyecto.k_def})

    return JsonResponse({
        "ok": True, "id": pozo.id,
        "analisis": engine.analizar_proyecto(proyecto),
        "pozos": _pozos_payload(proyecto),
    })


@require_POST
def api_pozo_borrar(request, pk):
    pozo = get_object_or_404(Pozo, pk=pk)
    proyecto = pozo.proyecto
    pozo.delete()
    return JsonResponse({
        "ok": True,
        "analisis": engine.analizar_proyecto(proyecto),
        "pozos": _pozos_payload(proyecto),
    })


@require_POST
def api_par_guardar(request, pk):
    par = get_object_or_404(ParInyeccion, pk=pk)
    datos = json.loads(request.body or "{}")
    for campo in ("k_direccional", "ancho_brazo", "h_direccional",
                  "factor_asignacion", "eficiencia_areal"):
        if campo in datos:
            valor = _num(datos[campo])
            if campo in ("k_direccional", "ancho_brazo", "eficiencia_areal") and valor is None:
                continue
            setattr(par, campo, valor)
    if "activo" in datos:
        par.activo = bool(datos["activo"])
    if "notas" in datos:
        par.notas = str(datos["notas"])[:200]
    par.k_direccional = max(par.k_direccional, 0.1)
    par.ancho_brazo = min(max(par.ancho_brazo, 4.0), 180.0)
    par.save()
    return JsonResponse({"ok": True, "analisis": engine.analizar_proyecto(par.proyecto)})


@require_POST
def api_par_crear(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk)
    datos = json.loads(request.body or "{}")
    iny = get_object_or_404(Pozo, pk=datos.get("inyector"), proyecto=proyecto,
                            tipo=TipoPozo.INYECTOR)
    prod = get_object_or_404(Pozo, pk=datos.get("productor"), proyecto=proyecto,
                             tipo=TipoPozo.PRODUCTOR)
    par, creado = ParInyeccion.objects.get_or_create(
        inyector=iny, productor=prod,
        defaults={"proyecto": proyecto,
                  "k_direccional": _num(datos.get("k_direccional")) or proyecto.k_def})
    if not creado and not par.activo:
        par.activo = True
        par.save()
    return JsonResponse({
        "ok": True, "id": par.id,
        "analisis": engine.analizar_proyecto(proyecto),
        "pozos": _pozos_payload(proyecto),
    })


@require_POST
def api_par_borrar(request, pk):
    par = get_object_or_404(ParInyeccion, pk=pk)
    proyecto = par.proyecto
    par.delete()
    return JsonResponse({
        "ok": True,
        "analisis": engine.analizar_proyecto(proyecto),
        "pozos": _pozos_payload(proyecto),
    })


def api_curva(request, pk):
    curva = get_object_or_404(CurvaKr, pk=pk)
    return JsonResponse({
        "ok": True, "id": curva.id, "nombre": curva.nombre,
        "puntos": [{"sw": p.sw, "krw": p.krw, "kro": p.kro} for p in curva.puntos.all()],
    })


@require_POST
def api_curva_guardar(request, pk):
    curva = get_object_or_404(CurvaKr, pk=pk)
    datos = json.loads(request.body or "{}")
    puntos = datos.get("puntos") or []
    limpios = []
    for fila in puntos:
        sw, krw, kro = _num(fila.get("sw")), _num(fila.get("krw")), _num(fila.get("kro"))
        if sw is None or krw is None or kro is None:
            continue
        limpios.append((min(max(sw, 0.0), 1.0), max(krw, 0.0), max(kro, 0.0)))
    if len(limpios) < 3:
        return JsonResponse(
            {"ok": False, "error": "Se necesitan al menos 3 filas completas."}, status=400)
    limpios.sort(key=lambda z: z[0])
    curva.puntos.all().delete()
    PuntoKr.objects.bulk_create([
        PuntoKr(curva=curva, sw=s, krw=w, kro=o, orden=i)
        for i, (s, w, o) in enumerate(limpios)])
    proyecto = curva.proyecto or Proyecto.objects.filter(
        pozo__curva_kr=curva).first()
    salida = {"ok": True}
    if proyecto:
        salida["analisis"] = engine.analizar_proyecto(proyecto)
    return JsonResponse(salida)


# ===========================================================================
# Calculos por pozo
# ===========================================================================
def calculos(request, pk, pozo_id=None):
    proyecto = get_object_or_404(Proyecto, pk=pk)
    pozos = list(Pozo.objects.filter(proyecto=proyecto)
                 .select_related("curva_kr", "proyecto").order_by("tipo", "id_pozo"))
    if not pozos:
        return render(request, "core/calculos.html", {
            "seccion": "calculos", "proyecto": proyecto, "pozos": [], "pozo": None,
        })

    if pozo_id:
        pozo = next((p for p in pozos if p.id == pozo_id), None)
        if pozo is None:
            raise Http404("El pozo no pertenece a este proyecto.")
    else:
        pozo = next((p for p in pozos if p.tipo == TipoPozo.PRODUCTOR), pozos[0])

    ficha = engine.ficha_pozo(pozo)
    campo = ficha.get("campo")
    return render(request, "core/calculos.html", {
        "seccion": "calculos",
        "proyecto": proyecto,
        "pozos": pozos,
        "pozo": pozo,
        "f": ficha,
        "series": ficha.get("series", {}),
        "pc": ficha.get("pc") or [],
        "campo": engine.iny_json(campo, pozo) if campo else None,
        "params": sorted((pozo.parametros_levantamiento or {}).items()),
        "curva_puntos": [
            {"sw": s, "krw": w, "kro": o} for s, w, o in
            [(p["sw"], p["krw"], p["kro"]) for p in ficha["tabla_kr"]]
        ],
        "curva_id": pozo.curva_kr_id,
    })


# ===========================================================================
# Economia
# ===========================================================================
@require_http_methods(["GET", "POST"])
def economia(request, pk):
    proyecto = get_object_or_404(Proyecto, pk=pk)
    params = economics.parametros_de(proyecto)

    if request.method == "POST":
        form = EconomiaForm(request.POST, instance=params)
        if form.is_valid():
            form.save()
            messages.success(request, "Supuestos económicos actualizados.")
            return redirect("core:economia", pk=pk)
    else:
        form = EconomiaForm(instance=params)

    cotizacion = oilprice.precio_actual(
        params.marcador, forzar=request.GET.get("refrescar") == "1")
    precio = params.precio_manual if params.precio_manual else cotizacion["precio"]
    resultado = economics.simular(proyecto, params, precio)
    hist = oilprice.historico(params.marcador)

    return render(request, "core/economia.html", {
        "seccion": "economia",
        "proyecto": proyecto,
        "form": form,
        "params": params,
        "cotizacion": cotizacion,
        "precio_usado": precio,
        "res": resultado,
        "series": {
            "filas": resultado.get("filas", []),
            "desglose": resultado.get("desglose_opex", []),
            "precio_hist": hist.get("serie", []),
            "precio_neto": resultado.get("resumen", {}).get("precio_neto"),
        },
        "hist_error": hist.get("error"),
    })


# ===========================================================================
# Estaticas
# ===========================================================================
def metodo(request):
    proyecto = None
    pid = request.GET.get("p")
    if pid:
        proyecto = Proyecto.objects.filter(pk=pid).first()
    return render(request, "core/metodo.html", {"seccion": "metodo", "proyecto": proyecto})


def contacto(request):
    proyecto = None
    pid = request.GET.get("p")
    if pid:
        proyecto = Proyecto.objects.filter(pk=pid).first()
    return render(request, "core/contacto.html", {"seccion": "contacto", "proyecto": proyecto})


def inicio(request):
    p = Proyecto.objects.first()
    if p:
        return redirect("core:estudio", pk=p.pk)
    return redirect("core:proyectos")
