import json
import platform
import socket

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import busqueda, servicio
from .models import ConsultaIA

ES = {"ensure_ascii": False}


def _registrar(tipo, entrada, resultado):
    try:
        ConsultaIA.objects.create(tipo=tipo, entrada=entrada, resultado=resultado)
    except Exception:  # el registro nunca debe tumbar la respuesta
        pass


@require_GET
def salud(request):
    try:
        with connection.cursor() as c:
            c.execute("SELECT 1")
        bd = "ok"
    except Exception as e:  # pragma: no cover
        bd = "error: " + e.__class__.__name__
    m = servicio.modelos()["metricas"]
    return JsonResponse({
        "estado": "ok" if bd == "ok" else "degradado", "servicio": "SIRAC API", "version": settings.VERSION,
        "hora_servidor": timezone.localtime().isoformat(timespec="seconds"), "servidor": socket.gethostname(),
        "python": platform.python_version(), "base_de_datos": bd, "motor_bd": connection.vendor,
        "modelos": {"calificador_auc": m["clasificacion"]["metricas"]["auc_roc"],
                    "proyeccion_r2": m["regresion"]["modelos"][m["regresion"]["mejor"]]["r2"]},
    }, json_dumps_params=ES)


@require_GET
def metricas(request):
    return JsonResponse(servicio.modelos()["metricas"], json_dumps_params=ES)


@csrf_exempt
@require_POST
def calificar(request):
    try:
        datos = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)
    r = servicio.calificar(datos)
    _registrar("calificar", datos, r)
    return JsonResponse(r, json_dumps_params=ES)


@require_GET
def proyectar(request):
    try:
        r = servicio.proyectar(request.GET.get("inversion", "228"))
    except ValueError:
        return JsonResponse({"error": "inversion debe ser un número"}, status=400)
    return JsonResponse(r, json_dumps_params=ES)


@require_GET
def conversacion(request):
    return JsonResponse({"bfs": busqueda.bfs(), "dfs": busqueda.dfs()}, json_dumps_params=ES)


@require_GET
def distritos(request):
    return JsonResponse({"distritos": sorted(busqueda.DISTRITOS)}, json_dumps_params=ES)


@require_GET
def ruta(request):
    o, d = request.GET.get("origen", "Ate"), request.GET.get("destino", "Comas")
    if o not in busqueda.DISTRITOS or d not in busqueda.DISTRITOS:
        return JsonResponse({"error": "distrito desconocido"}, status=400)
    r = {"a_estrella": busqueda.a_estrella(o, d), "costo_uniforme": busqueda.a_estrella(o, d, False),
         "bfs": busqueda.bfs_ruta(o, d)}
    _registrar("ruta", {"origen": o, "destino": d}, {"km": r["a_estrella"]["km"]})
    return JsonResponse(r, json_dumps_params=ES)


@require_GET
def asignar(request):
    try:
        semilla = int(request.GET.get("semilla", "7"))
    except ValueError:
        semilla = 7
    r = busqueda.hill_climbing(busqueda.leads_demo(semilla=semilla))
    r["vendedores"] = busqueda.VENDEDORES
    return JsonResponse(r, json_dumps_params=ES)
