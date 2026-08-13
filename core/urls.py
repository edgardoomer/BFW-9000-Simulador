from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.inicio, name="inicio"),

    # Proyectos
    path("proyectos/", views.proyectos, name="proyectos"),
    path("proyectos/nuevo/", views.proyecto_form, name="proyecto_nuevo"),
    path("proyectos/<int:pk>/editar/", views.proyecto_form, name="proyecto_editar"),
    path("proyectos/<int:pk>/eliminar/", views.proyecto_eliminar, name="proyecto_eliminar"),
    path("proyectos/ejemplos/", views.cargar_ejemplos, name="cargar_ejemplos"),

    # Estudio
    path("estudio/<int:pk>/", views.estudio, name="estudio"),

    # Calculos por pozo
    path("calculos/<int:pk>/", views.calculos, name="calculos"),
    path("calculos/<int:pk>/pozo/<int:pozo_id>/", views.calculos, name="calculos_pozo"),

    # Economia
    path("economia/<int:pk>/", views.economia, name="economia"),

    # Referencia
    path("metodo/", views.metodo, name="metodo"),
    path("contacto/", views.contacto, name="contacto"),

    # API
    path("api/proyecto/<int:pk>/pozo/", views.api_pozo_crear, name="api_pozo_crear"),
    path("api/pozo/<int:pk>/", views.api_pozo_guardar, name="api_pozo_guardar"),
    path("api/pozo/<int:pk>/borrar/", views.api_pozo_borrar, name="api_pozo_borrar"),
    path("api/proyecto/<int:pk>/par/", views.api_par_crear, name="api_par_crear"),
    path("api/par/<int:pk>/", views.api_par_guardar, name="api_par_guardar"),
    path("api/par/<int:pk>/borrar/", views.api_par_borrar, name="api_par_borrar"),
    path("api/curva/<int:pk>/", views.api_curva, name="api_curva"),
    path("api/curva/<int:pk>/guardar/", views.api_curva_guardar, name="api_curva_guardar"),
]
