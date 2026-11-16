from django.urls import path

from . import views

urlpatterns = [
    path("crm/login", views.login),
    path("crm/yo", views.yo),
    path("crm/tablero", views.tablero),
    path("crm/clientes", views.clientes),
    path("crm/clientes/simular", views.simular_nuevo),
    path("crm/clientes/<int:cid>", views.cliente),
    path("crm/clientes/<int:cid>/mensajes", views.mensajes),
    path("crm/clientes/<int:cid>/accion", views.accion),
    path("crm/reasignar", views.reasignar),
    path("crm/vendedores", views.vendedores),
    path("crm/productos", views.productos),
    path("crm/productos/<int:pid>", views.producto),
    path("crm/entrenamiento", views.entrenamiento),
    path("crm/entrenamiento/probar", views.probar_kinti),
    path("crm/entrenamiento/<int:rid>", views.respuesta),
    path("crm/usuarios", views.usuarios),
    path("crm/usuarios/<int:uid>", views.usuario),
    path("crm/demo/reiniciar", views.reiniciar_demo),
    path("crm/whatsapp", views.whatsapp),
    path("wa/evolution", views.wa_evolution),
    path("wa/iniciar", views.wa_iniciar),
    path("wa/mensajes", views.wa_mensajes),
]
