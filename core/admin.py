from django.contrib import admin

from .models import (CurvaKr, ParInyeccion, ParametrosEconomicos, Pozo,
                     PrecioCrudo, Proyecto, PuntoKr, ResultadoPozo)


class PozoInline(admin.TabularInline):
    model = Pozo
    extra = 0
    fields = ("id_pozo", "nombre_pozo", "tipo", "x", "y", "q", "curva_kr")
    show_change_link = True


class ParInline(admin.TabularInline):
    model = ParInyeccion
    extra = 0
    fields = ("inyector", "productor", "k_direccional", "ancho_brazo", "activo")
    fk_name = "proyecto"


class PuntoKrInline(admin.TabularInline):
    model = PuntoKr
    extra = 0
    fields = ("sw", "krw", "kro", "orden")


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ("id_proyecto", "nombre", "campo", "bloque", "fecha",
                    "n_inyectores", "n_productores", "area_acres")
    search_fields = ("id_proyecto", "nombre", "campo", "bloque")
    list_filter = ("campo", "bloque")
    date_hierarchy = "fecha"
    inlines = [PozoInline, ParInline]
    fieldsets = (
        ("Identificación", {
            "fields": ("id_proyecto", "nombre", "fecha", "operadora",
                       "bloque", "campo", "yacimiento", "pozos", "area_acres",
                       "descripcion")
        }),
        ("Valores por defecto del yacimiento", {
            "classes": ("collapse",),
            "fields": ("h_def", "phi_def", "swi_def", "sor_def", "k_def",
                       "muw_def", "muo_def", "bo_def", "bw_def",
                       "presion_def", "temperatura_def", "api_def", "rw_def")
        }),
    )


@admin.register(Pozo)
class PozoAdmin(admin.ModelAdmin):
    list_display = ("id_pozo", "nombre_pozo", "tipo", "proyecto", "x", "y", "q",
                    "tipo_levantamiento")
    list_filter = ("proyecto", "tipo", "tipo_levantamiento", "tipo_completacion")
    search_fields = ("id_pozo", "nombre_pozo")
    autocomplete_fields = ("proyecto",)
    fieldsets = (
        ("Identificación", {
            "fields": ("proyecto", "id_pozo", "nombre_pozo", "tipo", "x", "y", "q")
        }),
        ("Petrofísica", {
            "fields": ("h", "phi", "k", "kv", "swi", "sor", "curva_kr")
        }),
        ("Fluidos y presión", {
            "fields": ("muw", "muo", "bo", "bw", "api", "pwf", "presion_cabeza", "skin")
        }),
        ("Presión capilar", {
            "classes": ("collapse",),
            "fields": ("pc_entrada", "sigma_ow", "angulo_contacto")
        }),
        ("Completación", {
            "classes": ("collapse",),
            "fields": ("prof_md", "prof_tvd", "tope_arena", "base_arena",
                       "diametro_casing", "tipo_completacion")
        }),
        ("Levantamiento / inyección", {
            "fields": ("tipo_levantamiento", "tipo_bomba_iny", "parametros_levantamiento")
        }),
        ("Notas", {"classes": ("collapse",), "fields": ("notas",)}),
    )


@admin.register(CurvaKr)
class CurvaKrAdmin(admin.ModelAdmin):
    list_display = ("nombre", "proyecto", "tipo_roca", "fuente", "swc", "sor",
                    "krw_max", "kro_max")
    list_filter = ("fuente", "proyecto")
    search_fields = ("nombre", "tipo_roca")
    inlines = [PuntoKrInline]


@admin.register(ParInyeccion)
class ParInyeccionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "proyecto", "k_direccional", "ancho_brazo",
                    "eficiencia_areal", "activo")
    list_filter = ("proyecto", "activo")
    autocomplete_fields = ("inyector", "productor")


@admin.register(ResultadoPozo)
class ResultadoPozoAdmin(admin.ModelAdmin):
    list_display = ("pozo", "swf", "fwf", "dfwf", "tbt_dias", "inyector_critico",
                    "calculado_en")
    readonly_fields = [f.name for f in ResultadoPozo._meta.fields if f.name != "id"]
    list_filter = ("pozo__proyecto",)


@admin.register(ParametrosEconomicos)
class ParametrosEconomicosAdmin(admin.ModelAdmin):
    list_display = ("proyecto", "marcador", "precio_manual", "qo_inicial",
                    "costo_iny_agua", "opex_fijo_mes", "tasa_descuento")


@admin.register(PrecioCrudo)
class PrecioCrudoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "precio", "moneda", "as_of", "obtenido_en", "exitoso")
    list_filter = ("codigo", "exitoso")
    readonly_fields = ("codigo", "precio", "moneda", "tipo", "as_of",
                       "obtenido_en", "exitoso", "detalle")


admin.site.site_header = "Simulador Buckley-Leverett"
admin.site.site_title = "Buckley-Leverett"
admin.site.index_title = "Administración de datos"
