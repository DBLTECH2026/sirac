"""API del CRM de SIRAC (/api/crm/…) y del simulador público de WhatsApp (/api/wa/…)."""
import random
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth import authenticate, get_user_model
from django.core import signing
from django.core.cache import cache
from django.db import transaction
from django.db.models import Avg, Count, Max, Q, Sum
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from ia import busqueda

from django.conf import settings

from . import demo, evolution, kinti
from .auth import cuerpo, emitir, error, requiere, responder
from .models import Ajuste, Cliente, Evento, Mensaje, Perfil, Producto, RespuestaKinti

ROLES_TODOS = ("admin", "gerente", "ventas")
JEFES = ("admin", "gerente")
ETAPAS = dict(Cliente.ETAPAS)
ORIGENES = dict(Cliente.ORIGENES)


# ------------------------------------------------------------------ serializadores
def usuario_json(u):
    p = u.perfil
    return {"id": u.id, "nombre": u.get_full_name(), "primer_nombre": u.first_name, "correo": u.username,
            "rol": p.rol, "rol_nombre": p.get_rol_display(), "cargo": p.cargo or p.get_rol_display(), "color": p.color,
            "iniciales": p.iniciales, "zona": p.zona, "especialidad": p.especialidad, "meta": float(p.meta_mensual),
            "capacidad": p.capacidad, "activo": u.is_active}


def vendedor_corto(u):
    if not u:
        return None
    return {"id": u.id, "nombre": u.get_full_name(), "primer_nombre": u.first_name, "color": u.perfil.color, "iniciales": u.perfil.iniciales}


def producto_json(p):
    if not p:
        return None
    return {"id": p.id, "nombre": p.nombre, "categoria": p.categoria, "detalle": p.detalle, "precio": float(p.precio),
            "stock": p.stock, "garantia_meses": p.garantia_meses, "foto": f"/catalogo/{p.foto}.webp" if p.foto else None,
            "palabras": p.palabras, "mas_vendido": p.mas_vendido, "activo": p.activo}


def iniciales(nombre):
    partes = (nombre or "?").split()
    return "".join(x[0] for x in partes[:2]).upper()


def mensaje_json(m):
    return {"id": m.id, "autor": m.autor, "texto": m.texto, "creado": m.creado.isoformat(),
            "usuario": vendedor_corto(m.usuario) if m.usuario_id else None, "producto": producto_json(m.producto),
            "segundos": round(m.segundos_respuesta) if m.segundos_respuesta is not None else None}


def cliente_json(c, ultimo=None):
    d = {"id": c.id, "nombre": c.nombre, "iniciales": iniciales(c.nombre), "telefono": c.telefono, "distrito": c.distrito,
         "provincia": c.provincia, "origen": c.origen, "origen_nombre": ORIGENES.get(c.origen, c.origen), "campana": c.campana,
         "producto": producto_json(c.producto), "cantidad": c.cantidad, "delivery": float(c.delivery) if c.delivery is not None else None,
         "monto": float(c.monto), "etapa": c.etapa, "etapa_nombre": ETAPAS.get(c.etapa, c.etapa), "motivo_perdida": c.motivo_perdida,
         "vendedor": vendedor_corto(c.vendedor), "kinti_activo": c.kinti_activo, "estado_conv": c.estado_conv,
         "probabilidad": c.probabilidad, "etiqueta_ia": c.etiqueta_ia, "etiquetas": c.etiquetas, "no_leidos": c.no_leidos,
         "simulador": c.simulador, "whatsapp": bool(c.whatsapp_jid), "creado": c.creado.isoformat(), "actualizado": c.actualizado.isoformat(),
         "cerrado": c.cerrado.isoformat() if c.cerrado else None}
    if ultimo is not None:
        d["ultimo"] = {"autor": ultimo.autor, "texto": ultimo.texto, "creado": ultimo.creado.isoformat(),
                       "usuario": ultimo.usuario.first_name if ultimo.usuario_id else None}
    return d


def visibles(u):
    qs = Cliente.objects.select_related("producto", "vendedor__perfil")
    return qs.filter(vendedor=u) if u.perfil.rol == "ventas" else qs


def obtener(u, cid):
    return visibles(u).filter(id=cid).first()


def evento(c, tipo, texto, u=None):
    Evento.objects.create(cliente=c, tipo=tipo, texto=texto, usuario=u)


# ------------------------------------------------------------------ sesión
@csrf_exempt
def login(request):
    if request.method != "POST":
        return error("Método no permitido", 405)
    d = cuerpo(request) or {}
    correo = (d.get("correo") or "").strip().lower()
    clave_ip = f"login:{request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))}"
    if cache.get(clave_ip, 0) >= 15:
        return error("Demasiados intentos. Espera unos minutos.", 429)
    u = authenticate(username=correo, password=d.get("clave") or "")
    if not u or not hasattr(u, "perfil"):
        cache.set(clave_ip, cache.get(clave_ip, 0) + 1, 600)
        return error("Correo o contraseña incorrectos.", 401)
    return responder({"token": emitir(u), "usuario": usuario_json(u)})


@requiere(*ROLES_TODOS)
def yo(request):
    u = request.usuario
    sin_leer = visibles(u).filter(etapa__in=kinti.ABIERTAS).aggregate(n=Sum("no_leidos"))["n"] or 0
    return responder({"usuario": usuario_json(u), "sin_leer": sin_leer})


# ------------------------------------------------------------------ clientes y chats
@requiere(*ROLES_TODOS, metodos=("GET", "POST"))
def clientes(request):
    u = request.usuario
    if request.method == "POST":
        return crear_cliente(request)
    qs = visibles(u)
    f = request.GET.get("filtro", "todos")
    if f == "sin_asignar":
        qs = qs.filter(vendedor__isnull=True, etapa__in=kinti.ABIERTAS)
    elif f == "kinti":
        qs = qs.filter(kinti_activo=True, etapa__in=kinti.ABIERTAS)
    elif f == "mios":
        qs = qs.filter(vendedor=u)
    if request.GET.get("etapa"):
        qs = qs.filter(etapa=request.GET["etapa"])
    if request.GET.get("vendedor"):
        qs = qs.filter(vendedor_id=request.GET["vendedor"])
    if request.GET.get("q"):
        q = request.GET["q"].strip()
        qs = qs.filter(Q(nombre__icontains=q) | Q(telefono__icontains=q) | Q(distrito__icontains=q) | Q(producto__nombre__icontains=q))
    if request.GET.get("vista") == "embudo":
        dias = 30
        limite = timezone.now() - timedelta(days=dias)
        qs = qs.filter(Q(etapa__in=kinti.ABIERTAS) | Q(actualizado__gte=limite))
    qs = qs.order_by("-actualizado")[: int(request.GET.get("limite", 300))]
    lista = list(qs)
    ultimos = {}
    ids = Mensaje.objects.filter(cliente__in=lista, autor__in=("cliente", "kinti", "vendedor")).values("cliente").annotate(m=Max("id")).values_list("m", flat=True)
    for m in Mensaje.objects.filter(id__in=list(ids)).select_related("usuario"):
        ultimos[m.cliente_id] = m
    base = visibles(u)
    conteos = {"todos": base.count(), "sin_asignar": base.filter(vendedor__isnull=True, etapa__in=kinti.ABIERTAS).count(),
               "kinti": base.filter(kinti_activo=True, etapa__in=kinti.ABIERTAS).count(), "mios": base.filter(vendedor=u).count()}
    return responder({"clientes": [cliente_json(c, ultimos.get(c.id)) for c in lista], "conteos": conteos,
                      "sin_responder": base.filter(no_leidos__gt=0, etapa__in=kinti.ABIERTAS).count()})


def crear_cliente(request):
    u, d = request.usuario, request.datos
    nombre = (d.get("nombre") or "").strip()[:80]
    if not nombre:
        return error("Escribe el nombre del cliente.")
    c = Cliente(nombre=nombre, telefono=(d.get("telefono") or "")[:20], origen=d.get("origen") if d.get("origen") in ORIGENES else "directo",
                campana=(d.get("campana") or "Registro manual")[:60], kinti_activo=False)
    if d.get("producto_id"):
        c.producto = Producto.objects.filter(id=d["producto_id"]).first()
    c.cantidad = max(1, int(d.get("cantidad") or 1))
    lugar = (d.get("distrito") or "").strip()
    if lugar in busqueda.DISTRITOS:
        c.distrito = lugar
        c.delivery = kinti.cotizar_delivery(lugar)["costo"]
    elif lugar:
        c.distrito, c.provincia, c.delivery = lugar[:40], True, kinti.ENVIO_PROVINCIA
    if u.perfil.rol == "ventas":
        c.vendedor = u
    elif d.get("vendedor_id"):
        c.vendedor = get_user_model().objects.filter(id=d["vendedor_id"], perfil__rol="ventas").first()
    kinti.recalcular_monto(c)
    c.save()
    kinti.calificar(c)
    c.save()
    evento(c, "creado", f"Creada a mano por {u.get_full_name()}", u)
    return responder(cliente_json(c), 201)


def ficha(c):
    d = cliente_json(c)
    d["eventos"] = [{"tipo": e.tipo, "texto": e.texto, "creado": e.creado.isoformat()} for e in c.eventos.all()[:12]]
    d["notas"] = [mensaje_json(m) for m in c.mensajes.filter(autor="nota").select_related("usuario").order_by("-creado")[:5]]
    if c.distrito in busqueda.DISTRITOS:
        r = kinti.cotizar_delivery(c.distrito)
        d["ruta"] = {"desde": kinti.ALMACEN, "km": r["km"], "costo": float(r["costo"]), "plazo": r["plazo"], "camino": r["camino"]}
    camino = busqueda.bfs(inicio=c.estado_conv, objetivo=busqueda.OBJETIVO_CONV) if c.estado_conv in busqueda.FLUJO else None
    d["conversacion"] = {"estado": c.estado_conv, "faltan": camino["acciones"] if camino else [],
                         "siguiente": camino["acciones"][0] if camino and camino["acciones"] else None}
    prob = c.probabilidad or 0
    d["recomendacion"] = ("Derivar ya a un vendedor" if prob >= 0.6 else "Kinti sigue la conversación y ofrece delivery" if prob >= 0.4
                          else "Kinti responde y deja un recordatorio")
    return d


@requiere(*ROLES_TODOS, metodos=("GET", "PATCH"))
def cliente(request, cid):
    u = request.usuario
    c = obtener(u, cid)
    if not c:
        return error("No encontramos ese cliente.", 404)
    if request.method == "GET":
        return responder(ficha(c))
    d = request.datos
    with transaction.atomic():
        if "etapa" in d and d["etapa"] in ETAPAS and d["etapa"] != c.etapa:
            previa = c.get_etapa_display()
            c.etapa = d["etapa"]
            c.motivo_perdida = (d.get("motivo") or "Sin respuesta")[:60] if c.etapa == "perdido" else ""
            c.cerrado = timezone.now() if c.etapa in ("ganado", "perdido") else None
            if c.etapa in ("ganado", "perdido"):
                c.kinti_activo = False
            if c.etapa == "ganado" and not c.vendedor and u.perfil.rol == "ventas":
                c.vendedor = u
            extra = f" · motivo: {c.motivo_perdida}" if c.etapa == "perdido" else ""
            evento(c, "etapa", f"{previa} → {c.get_etapa_display()} por {u.first_name}{extra}", u)
            if c.etapa == "ganado" and c.producto and c.producto.stock >= c.cantidad:
                Producto.objects.filter(id=c.producto_id).update(stock=c.producto.stock - c.cantidad)
        if "vendedor_id" in d and u.perfil.rol in JEFES:
            v = get_user_model().objects.filter(id=d["vendedor_id"], perfil__rol="ventas").first() if d["vendedor_id"] else None
            if v != c.vendedor:
                c.vendedor = v
                evento(c, "asignado", f"Asignado a {v.get_full_name()} por {u.first_name}" if v else f"Sin asignar ({u.first_name})", u)
        for campo in ("nombre", "telefono"):
            if d.get(campo):
                setattr(c, campo, str(d[campo])[:80 if campo == "nombre" else 20])
        if "producto_id" in d:
            c.producto = Producto.objects.filter(id=d["producto_id"]).first() if d["producto_id"] else None
        if d.get("cantidad"):
            c.cantidad = max(1, min(50, int(d["cantidad"])))
        if "distrito" in d and d["distrito"]:
            lugar = str(d["distrito"])[:40]
            if lugar in busqueda.DISTRITOS:
                c.distrito, c.provincia, c.delivery = lugar, False, kinti.cotizar_delivery(lugar)["costo"]
            else:
                c.distrito, c.provincia, c.delivery = lugar, True, kinti.ENVIO_PROVINCIA
        if "etiquetas" in d and isinstance(d["etiquetas"], list):
            c.etiquetas = [str(x)[:24] for x in d["etiquetas"]][:8]
        kinti.recalcular_monto(c)
        c.actualizado = timezone.now()
        c.save()
    return responder(ficha(c))


@requiere(*ROLES_TODOS, metodos=("GET", "POST"))
def mensajes(request, cid):
    u = request.usuario
    c = obtener(u, cid)
    if not c:
        return error("No encontramos ese chat.", 404)
    if request.method == "GET":
        desde = int(request.GET.get("desde", 0) or 0)
        qs = c.mensajes.filter(id__gt=desde).select_related("usuario", "producto")
        if request.GET.get("leido") == "1" and c.no_leidos:
            Cliente.objects.filter(id=c.id).update(no_leidos=0)
        return responder({"mensajes": [mensaje_json(m) for m in qs], "kinti_activo": c.kinti_activo, "etapa": c.etapa})
    d = request.datos
    texto = (d.get("texto") or "").strip()[:1000]
    if not texto:
        return error("Escribe un mensaje.")
    ahora = timezone.now()
    with transaction.atomic():
        if d.get("interno"):
            m = Mensaje.objects.create(cliente=c, autor="nota", usuario=u, texto=texto, creado=ahora)
        else:
            m = Mensaje.objects.create(cliente=c, autor="vendedor", usuario=u, texto=texto, creado=ahora,
                                       producto=Producto.objects.filter(id=d.get("producto_id")).first() if d.get("producto_id") else None)
            if c.kinti_activo:
                c.kinti_activo = False
                evento(c, "tomado", f"{u.get_full_name()} tomó el chat", u)
            if not c.vendedor and u.perfil.rol == "ventas":
                c.vendedor = u
            if d.get("tipo") == "cotizacion" and c.etapa in ("nuevo", "calificado"):
                c.etapa = "cotizado"
                evento(c, "etapa", f"Cotización enviada por {u.first_name} · S/ {c.monto:,.0f}", u)
            if d.get("tipo") == "pago":
                evento(c, "pago", f"Link de pago enviado por {u.first_name}", u)
        c.no_leidos = 0
        c.actualizado = ahora
        c.save()
    if m.autor == "vendedor":
        evolution.enviar(c, [m])
    return responder(mensaje_json(m), 201)


@requiere(*ROLES_TODOS, metodos=("POST",))
def accion(request, cid):
    u, d = request.usuario, request.datos
    c = obtener(u, cid)
    if not c:
        return error("No encontramos ese chat.", 404)
    que = d.get("accion")
    with transaction.atomic():
        if que == "tomar":
            c.kinti_activo = False
            if u.perfil.rol == "ventas":
                c.vendedor = u
            evento(c, "tomado", f"{u.get_full_name()} tomó el chat", u)
        elif que == "devolver":
            c.kinti_activo = True
            evento(c, "devuelto", f"{u.first_name} devolvió el chat a Kinti · IA", u)
        elif que == "simular":
            texto = (d.get("texto") or "").strip()[:500]
            if not texto:
                return error("Escribe el mensaje del cliente.")
            kinti.recibir(c, texto)
            return responder({"ok": True})
        elif que == "derivar":
            kinti.derivar(c, f"derivado por {u.first_name}", timezone.now(), u)
        else:
            return error("Acción desconocida.")
        c.actualizado = timezone.now()
        c.save()
    return responder(ficha(c))


@requiere(*JEFES, metodos=("POST",))
def reasignar(request):
    with transaction.atomic():
        r = kinti.reasignar_sin_vendedor(usuario=request.usuario)
    return responder(r)


@requiere(*ROLES_TODOS)
def vendedores(request):
    vs = kinti.vendedores_activos()
    return responder({"vendedores": [dict(usuario_json(v), carga=v.carga) for v in vs]})


@requiere(*ROLES_TODOS, metodos=("POST",))
def simular_nuevo(request):
    """Crea un chat entrante de prueba (como si llegara de un anuncio) y Kinti responde."""
    d = request.datos
    nombre = (d.get("nombre") or "").strip()[:40] or random.choice(["Valeria Ríos", "Óscar Huerta", "Mónica Salas", "Iván Torres"])
    texto = (d.get("texto") or "").strip()[:500] or "Hola, vi su anuncio de la freidora de aire. ¿Cuánto está?"
    c = Cliente.objects.create(nombre=nombre, telefono=f"+51 9{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)}",
                               origen=d.get("origen") if d.get("origen") in ORIGENES else "meta", campana="Simulación en el CRM")
    evento(c, "creado", f"Creada desde {c.get_origen_display()}")
    kinti.recibir(c, texto)
    return responder(cliente_json(c), 201)


# ------------------------------------------------------------------ catálogo y entrenamiento
@requiere(*ROLES_TODOS)
def productos(request):
    return responder({"productos": [producto_json(p) for p in Producto.objects.all()]})


@requiere(*JEFES, metodos=("PATCH",))
def producto(request, pid):
    p = Producto.objects.filter(id=pid).first()
    if not p:
        return error("No existe el producto.", 404)
    d = request.datos
    try:
        if "precio" in d:
            p.precio = max(Decimal("1"), Decimal(str(d["precio"])))
        if "stock" in d:
            p.stock = max(0, int(d["stock"]))
    except (InvalidOperation, ValueError):
        return error("Precio o stock inválido.")
    for campo in ("activo", "mas_vendido"):
        if campo in d:
            setattr(p, campo, bool(d[campo]))
    p.save()
    return responder(producto_json(p))


def respuesta_json(r):
    return {"id": r.id, "tema": r.tema, "palabras": r.palabras, "respuesta": r.respuesta, "activa": r.activa, "usos": r.usos,
            "actualizado": r.actualizado.isoformat()}


@requiere(*JEFES, metodos=("GET", "POST"))
def entrenamiento(request):
    if request.method == "POST":
        d = request.datos
        if not (d.get("tema") and d.get("palabras") and d.get("respuesta")):
            return error("Completa el tema, las palabras clave y la respuesta.")
        r = RespuestaKinti.objects.create(tema=d["tema"][:60], palabras=d["palabras"][:250], respuesta=d["respuesta"][:1000])
        return responder(respuesta_json(r), 201)
    total = Mensaje.objects.filter(autor="kinti").count()
    seg = Mensaje.objects.filter(autor="kinti", segundos_respuesta__isnull=False).aggregate(s=Avg("segundos_respuesta"))["s"] or 0
    derivados = Evento.objects.filter(tipo="derivado").values("cliente").distinct().count()
    chats = Cliente.objects.count() or 1
    return responder({"respuestas": [respuesta_json(r) for r in RespuestaKinti.objects.all()],
                      "estadisticas": {"mensajes": total, "segundos": round(seg, 1), "chats": chats,
                                       "sin_ayuda": round(1 - derivados / chats, 3), "estados": list(busqueda.FLUJO)}})


@requiere(*JEFES, metodos=("PATCH", "DELETE"))
def respuesta(request, rid):
    r = RespuestaKinti.objects.filter(id=rid).first()
    if not r:
        return error("No existe la respuesta.", 404)
    if request.method == "DELETE":
        r.delete()
        return responder({"ok": True})
    d = request.datos
    for campo, largo in (("tema", 60), ("palabras", 250), ("respuesta", 1000)):
        if d.get(campo):
            setattr(r, campo, str(d[campo])[:largo])
    if "activa" in d:
        r.activa = bool(d["activa"])
    r.save()
    return responder(respuesta_json(r))


@requiere(*JEFES, metodos=("POST",))
def probar_kinti(request):
    texto = (request.datos.get("texto") or "").strip()[:500]
    if not texto:
        return error("Escribe un mensaje de prueba.")
    falso = Cliente(nombre="", estado_conv="inicio")
    with transaction.atomic():
        partes = kinti.responder(falso, texto, guardar=False)
        transaction.set_rollback(True)
    t = kinti.normalizar(texto)
    entrenada = kinti.respuesta_entrenada(t)
    return responder({"respuestas": partes, "intenciones": sorted(kinti.intenciones(t)),
                      "producto": falso.producto.nombre if falso.producto_id else None,
                      "distrito": falso.distrito or None, "respuesta_entrenada": entrenada.tema if entrenada else None,
                      "estado": falso.estado_conv})


# ------------------------------------------------------------------ usuarios y demo
@requiere("admin", metodos=("GET", "POST"))
def usuarios(request):
    User = get_user_model()
    if request.method == "POST":
        d = request.datos
        correo = (d.get("correo") or "").strip().lower()
        nombre = (d.get("nombre") or "").strip()
        if not correo or "@" not in correo or not nombre or len(d.get("clave") or "") < 8:
            return error("Completa nombre, correo y una contraseña de 8 caracteres o más.")
        if User.objects.filter(username=correo).exists():
            return error("Ya existe un usuario con ese correo.")
        rol = d.get("rol") if d.get("rol") in dict(Perfil.ROLES) else "ventas"
        partes = nombre.split()
        with transaction.atomic():
            nu = User.objects.create_user(username=correo, email=correo, password=d["clave"], first_name=partes[0], last_name=" ".join(partes[1:]))
            Perfil.objects.create(usuario=nu, rol=rol, cargo=d.get("cargo") or dict(Perfil.ROLES)[rol], zona=d.get("zona") or "Lima",
                                  especialidad=d.get("especialidad") or "cocina", color=random.choice(["#0EB155", "#16B6D8", "#14213A", "#B45309"]),
                                  meta_mensual=Decimal(str(d.get("meta") or 0)))
        return responder(usuario_json(nu), 201)
    lista = User.objects.filter(perfil__isnull=False).select_related("perfil").order_by("id")
    return responder({"usuarios": [usuario_json(x) for x in lista]})


@requiere("admin", metodos=("PATCH",))
def usuario(request, uid):
    x = get_user_model().objects.filter(id=uid, perfil__isnull=False).select_related("perfil").first()
    if not x:
        return error("No existe el usuario.", 404)
    d = request.datos
    if x.id == request.usuario.id and ("activo" in d or "rol" in d):
        return error("No puedes desactivarte ni cambiar tu propio rol.")
    if "activo" in d:
        x.is_active = bool(d["activo"])
    if d.get("clave"):
        if len(d["clave"]) < 8:
            return error("La contraseña debe tener 8 caracteres o más.")
        x.set_password(d["clave"])
    x.save()
    p = x.perfil
    if d.get("rol") in dict(Perfil.ROLES):
        p.rol = d["rol"]
    for campo in ("cargo", "zona", "especialidad"):
        if d.get(campo):
            setattr(p, campo, d[campo])
    if "meta" in d:
        p.meta_mensual = Decimal(str(d["meta"] or 0))
    p.save()
    return responder(usuario_json(x))


@requiere("admin", metodos=("POST",))
def reiniciar_demo(request):
    r = demo.cargar(reiniciar=True, conservar_usuarios=True)
    return responder(r)


# ------------------------------------------------------------------ dashboard
def _dia(dt):
    return timezone.localtime(dt).date()


@requiere(*ROLES_TODOS)
def tablero(request):
    u = request.usuario
    ahora = timezone.now()
    periodo = request.GET.get("periodo", "30d")
    dias = {"hoy": 1, "7d": 7, "30d": 30}.get(periodo, 30)
    hoy0 = timezone.localtime(ahora).replace(hour=0, minute=0, second=0, microsecond=0)
    ini = hoy0 - timedelta(days=dias - 1)
    prev = ini - timedelta(days=dias)
    qs = visibles(u)

    def kpis(desde, hasta):
        chats = qs.filter(creado__gte=desde, creado__lt=hasta)
        ganados = qs.filter(etapa="ganado", cerrado__gte=desde, cerrado__lt=hasta)
        ventas = ganados.count()
        ingresos = float(ganados.aggregate(s=Sum("monto"))["s"] or 0)
        n = chats.count()
        calif = chats.filter(Q(probabilidad__gte=kinti.UMBRAL_CALIFICADO) | Q(etapa__in=("calificado", "cotizado", "ganado"))).count()
        return {"chats": n, "calificados": calif, "ventas": ventas, "ingresos": round(ingresos, 2),
                "conversion": round(ventas / n, 4) if n else 0, "ticket": round(ingresos / ventas, 2) if ventas else 0}

    actual, anterior = kpis(ini, ahora + timedelta(minutes=1)), kpis(prev, ini)

    n_serie = max(dias, 14)
    s_ini = hoy0 - timedelta(days=n_serie - 1)
    por_dia = defaultdict(lambda: {"ingresos": 0.0, "ventas": 0})
    for monto, cerrado in qs.filter(etapa="ganado", cerrado__gte=s_ini).values_list("monto", "cerrado"):
        k = _dia(cerrado)
        por_dia[k]["ingresos"] += float(monto)
        por_dia[k]["ventas"] += 1
    serie = []
    for i in range(n_serie):
        dia = (s_ini + timedelta(days=i)).date()
        serie.append({"fecha": dia.isoformat(), "dia": dia.day, "semana": dia.weekday(), **por_dia[dia]})

    del_periodo = qs.filter(creado__gte=ini)
    total = del_periodo.count()
    derivados = Evento.objects.filter(tipo="derivado", cliente__in=del_periodo).values("cliente").distinct().count()
    seg_k = Mensaje.objects.filter(cliente__in=del_periodo, autor="kinti", segundos_respuesta__isnull=False).aggregate(s=Avg("segundos_respuesta"))["s"]
    esperas = []
    for c in del_periodo.filter(eventos__tipo="derivado").distinct()[:150]:
        d = c.eventos.filter(tipo="derivado").order_by("creado").first()
        r = c.mensajes.filter(autor="vendedor", creado__gte=d.creado).order_by("creado").first() if d else None
        if r:
            esperas.append((r.creado - d.creado).total_seconds() / 60)
    kinti_d = {"chats": total, "derivados": derivados, "sin_ayuda": total - derivados,
               "pct_sin_ayuda": round((total - derivados) / total, 3) if total else 0,
               "segundos": round(seg_k or 0, 1), "minutos_equipo": round(sum(esperas) / len(esperas), 1) if esperas else None,
               "atendiendo": qs.filter(kinti_activo=True, etapa__in=kinti.ABIERTAS).count()}

    ranking = []
    vend = get_user_model().objects.filter(perfil__rol="ventas", is_active=True).select_related("perfil")
    if u.perfil.rol == "ventas":
        vend = vend.filter(id=u.id)
    for v in vend:
        g = Cliente.objects.filter(vendedor=v, etapa="ganado", cerrado__gte=ini)
        ing = float(g.aggregate(s=Sum("monto"))["s"] or 0)
        meta = float(v.perfil.meta_mensual) * dias / 30
        ranking.append({**vendedor_corto(v), "cargo": v.perfil.cargo, "ventas": g.count(), "ingresos": round(ing, 2),
                        "meta": round(meta, 2), "avance": round(ing / meta, 3) if meta else 0,
                        "abiertos": Cliente.objects.filter(vendedor=v, etapa__in=kinti.ABIERTAS).count()})
    ranking.sort(key=lambda r: -r["ingresos"])

    top = (qs.filter(etapa="ganado", cerrado__gte=ini, producto__isnull=False).values("producto")
           .annotate(ingresos=Sum("monto"), unidades=Sum("cantidad")).order_by("-ingresos")[:5])
    prods = {p.id: p for p in Producto.objects.filter(id__in=[t["producto"] for t in top])}
    top_l = [{"producto": producto_json(prods[t["producto"]]), "ingresos": float(t["ingresos"]), "unidades": t["unidades"],
              "pct": round(float(t["ingresos"]) / actual["ingresos"], 3) if actual["ingresos"] else 0} for t in top]

    embudo = []
    for k, nombre in Cliente.ETAPAS:
        e = qs.filter(etapa=k)
        if k in ("ganado", "perdido"):
            e = e.filter(cerrado__gte=ini)
        a = e.aggregate(n=Count("id"), s=Sum("monto"))
        embudo.append({"etapa": k, "nombre": nombre, "n": a["n"], "monto": float(a["s"] or 0)})

    origenes = [{"origen": o["origen"], "nombre": ORIGENES.get(o["origen"]), "chats": o["n"],
                 "ventas": o["v"]} for o in del_periodo.values("origen").annotate(n=Count("id"), v=Count("id", filter=Q(etapa="ganado"))).order_by("-n")]

    return responder({"periodo": periodo, "dias": dias, "desde": ini.date().isoformat(), "actual": actual, "anterior": anterior,
                      "serie": serie, "kinti": kinti_d, "ranking": ranking, "top": top_l, "embudo": embudo, "origenes": origenes})


# ------------------------------------------------------------------ simulador público de WhatsApp
SAL_WA = "sirac-wa"


def _ip(request):
    return (request.META.get("HTTP_X_FORWARDED_FOR") or request.META.get("REMOTE_ADDR") or "").split(",")[0].strip()


def _cliente_wa(request):
    try:
        d = signing.loads(request.headers.get("X-Sesion", ""), salt=SAL_WA, max_age=60 * 60 * 24)
    except signing.BadSignature:
        return None
    return Cliente.objects.filter(id=d.get("c"), simulador=True).first()


@csrf_exempt
def wa_iniciar(request):
    if request.method != "POST":
        return error("Método no permitido", 405)
    clave = f"wa:{_ip(request)}"
    if cache.get(clave, 0) >= 20:
        return error("Ya abriste muchas conversaciones. Prueba en un rato.", 429)
    d = cuerpo(request) or {}
    nombre = " ".join((d.get("nombre") or "").split())[:40]
    if len(nombre) < 2:
        return error("Escribe tu nombre.")
    cache.set(clave, cache.get(clave, 0) + 1, 3600)
    c = Cliente.objects.create(nombre=nombre.title(), telefono=f"+51 9{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)}",
                               origen="meta", campana="Simulador de WhatsApp", simulador=True)
    evento(c, "creado", "Creada desde el simulador de WhatsApp (anuncio de Meta)")
    return responder({"sesion": signing.dumps({"c": c.id}, salt=SAL_WA), "cliente": {"id": c.id, "nombre": c.nombre}}, 201)


@csrf_exempt
def wa_mensajes(request):
    c = _cliente_wa(request)
    if not c:
        return error("La conversación venció. Vuelve a empezar.", 401)
    if request.method == "GET":
        desde = int(request.GET.get("desde", 0) or 0)
        ms = c.mensajes.filter(id__gt=desde, autor__in=("cliente", "kinti", "vendedor")).select_related("usuario", "producto")
        return responder({"mensajes": [mensaje_json(m) for m in ms], "kinti_activo": c.kinti_activo,
                          "vendedor": c.vendedor.first_name if c.vendedor_id else None})
    if request.method != "POST":
        return error("Método no permitido", 405)
    texto = ((cuerpo(request) or {}).get("texto") or "").strip()[:500]
    if not texto:
        return error("Escribe un mensaje.")
    if c.mensajes.filter(autor="cliente").count() >= 60:
        return error("Esta conversación de prueba llegó a su límite.", 429)
    with transaction.atomic():
        kinti.recibir(c, texto)
    return responder({"ok": True}, 201)


# ------------------------------------------------------------------ WhatsApp real (Evolution API)
@requiere(*JEFES, metodos=("GET", "POST"))
def whatsapp(request):
    if request.method == "POST":
        if request.usuario.perfil.rol != "admin":
            return error("Solo la administradora conecta o desconecta el WhatsApp.", 403)
        d = request.datos
        if d.get("accion") == "conectar":
            r = evolution.conectar()
        elif d.get("accion") == "desconectar":
            r = evolution.desconectar()
        elif d.get("accion") == "filtro":
            palabra = kinti.normalizar(d.get("palabra") or "kusi")[:30] or "kusi"
            Ajuste.guardar("whatsapp_filtro", {"activo": bool(d.get("activo")), "palabra": palabra})
            r = evolution.estado()
        else:
            return error("Acción desconocida.")
    else:
        r = evolution.estado()
    r["filtro"] = Ajuste.leer("whatsapp_filtro", evolution.FILTRO_DEFECTO)
    r["chats"] = Cliente.objects.exclude(whatsapp_jid="").count()
    return responder(r)


TIPOS = {"audioMessage": "un audio", "imageMessage": "una imagen", "videoMessage": "un video", "stickerMessage": "un sticker",
         "documentMessage": "un documento", "locationMessage": "una ubicación", "contactMessage": "un contacto"}


@csrf_exempt
def wa_evolution(request):
    """Webhook que llama Evolution API (red interna de Docker) por cada mensaje de WhatsApp."""
    if request.method != "POST":
        return error("Método no permitido", 405)
    if not settings.EVOLUTION_WEBHOOK_TOKEN or request.GET.get("token") != settings.EVOLUTION_WEBHOOK_TOKEN:
        return error("No autorizado", 403)
    d = cuerpo(request) or {}
    if (d.get("event") or "").lower().replace("_", ".") != "messages.upsert":
        return responder({"ok": True})
    data = d.get("data") or {}
    if isinstance(data, list):
        data = data[0] if data else {}
    m = evolution.leer_mensaje(data)
    if evolution.ignorar_jid(m["jid"]) or (m["id"] and Mensaje.objects.filter(externo_id=m["id"]).exists()):
        return responder({"ok": True})
    ahora = timezone.now()
    c = Cliente.objects.filter(whatsapp_jid=m["jid"]).first()

    if m["de_mi"]:
        # Eco de lo que mandó el CRM, o una respuesta escrita directo en el celular
        if not c or not m["texto"]:
            return responder({"ok": True})
        recientes = c.mensajes.filter(autor__in=("kinti", "vendedor"), creado__gte=ahora - timedelta(minutes=10))
        if any(m["texto"] == x.texto or m["texto"].startswith(x.texto[:40]) for x in recientes):
            return responder({"ok": True})
        with transaction.atomic():
            Mensaje.objects.create(cliente=c, autor="vendedor", texto=m["texto"], externo_id=m["id"], creado=ahora)
            if c.kinti_activo:
                c.kinti_activo = False
                evento(c, "tomado", "Respondido desde el celular: Kinti · IA se pausa")
            c.actualizado = ahora
            c.save()
        return responder({"ok": True})

    if not c:
        f = Ajuste.leer("whatsapp_filtro", evolution.FILTRO_DEFECTO)
        if f["activo"] and not kinti.contiene(kinti.normalizar(m["texto"]), kinti.normalizar(f["palabra"])):
            return responder({"ok": True, "ignorado": "no menciona la palabra clave"})
        c = Cliente.objects.create(nombre=(m["nombre"] or f"WhatsApp {m['telefono'][-4:]}")[:80], telefono=f"+{m['telefono']}"[:20],
                                   origen="directo", campana="WhatsApp real (Evolution API)", whatsapp_jid=m["jid"])
        evento(c, "creado", "Llegó por WhatsApp (Evolution API)")
    with transaction.atomic():
        if m["texto"]:
            nuevos = kinti.recibir(c, m["texto"], externo_id=m["id"])
        else:
            Mensaje.objects.create(cliente=c, autor="cliente", texto=f"(Envió {TIPOS.get(m['tipo'], 'un archivo')})", externo_id=m["id"], creado=ahora)
            c.no_leidos += 1
            c.actualizado = ahora
            nuevos = []
            if c.kinti_activo and c.etapa not in ("ganado", "perdido"):
                nuevos = [Mensaje.objects.create(cliente=c, autor="kinti", creado=ahora, segundos_respuesta=1,
                                                 texto="Por ahora leo solo mensajes de texto. ¿Me lo escribes, por favor?")]
            c.save()
    evolution.enviar(c, nuevos)
    return responder({"ok": True, "cliente": c.id, "respuestas": len(nuevos)})
