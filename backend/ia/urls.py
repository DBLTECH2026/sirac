from django.urls import path

from . import views

urlpatterns = [
    path("salud", views.salud),
    path("ia/metricas", views.metricas),
    path("ia/calificar", views.calificar),
    path("ia/proyectar", views.proyectar),
    path("busqueda/conversacion", views.conversacion),
    path("busqueda/distritos", views.distritos),
    path("busqueda/ruta", views.ruta),
    path("busqueda/asignar", views.asignar),
]
