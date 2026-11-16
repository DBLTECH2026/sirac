"""Sesión del CRM con token firmado (Bearer). No usa cookies: el front-end guarda el token y lo envía en cada pedido."""
import json
from functools import wraps

from django.contrib.auth import get_user_model
from django.core import signing
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

SAL = "sirac-crm-sesion"
DURACION = 60 * 60 * 12  # 12 horas
ES = {"ensure_ascii": False}


def emitir(usuario):
    return signing.dumps({"u": usuario.id}, salt=SAL, compress=True)


def usuario_de(request):
    h = request.headers.get("Authorization", "")
    if not h.startswith("Bearer "):
        return None
    try:
        datos = signing.loads(h[7:], salt=SAL, max_age=DURACION)
    except signing.BadSignature:
        return None
    return get_user_model().objects.select_related("perfil").filter(id=datos.get("u"), is_active=True, perfil__isnull=False).first()


def responder(datos, status=200):
    return JsonResponse(datos, status=status, safe=not isinstance(datos, list), json_dumps_params=ES)


def error(mensaje, status=400):
    return responder({"error": mensaje}, status)


def cuerpo(request):
    try:
        return json.loads(request.body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def requiere(*roles, metodos=("GET",)):
    """Exige sesión (y rol, si se indica) y limita los métodos HTTP. Deja el usuario en request.usuario."""
    def deco(vista):
        @csrf_exempt
        @wraps(vista)
        def envuelta(request, *args, **kwargs):
            if request.method not in metodos:
                return error("Método no permitido", 405)
            u = usuario_de(request)
            if not u:
                return error("Tu sesión venció. Vuelve a iniciar sesión.", 401)
            if roles and u.perfil.rol not in roles:
                return error("Tu rol no tiene permiso para esto.", 403)
            request.usuario = u
            if request.method in ("POST", "PATCH", "PUT"):
                request.datos = cuerpo(request)
                if request.datos is None:
                    return error("JSON inválido")
            return vista(request, *args, **kwargs)
        return envuelta
    return deco
