"""Kinti · IA: el asistente que atiende los chats del CRM.

Usa lo que ya está en producción en la app `ia`:
- El grafo de la conversación (ia.busqueda.FLUJO) como máquina de estados: Kinti solo avanza por transiciones válidas.
- A* sobre el mapa de Lima para cotizar el delivery desde el almacén de Mesa Redonda (Cercado de Lima).
- La regresión logística (ia.servicio.calificar) para calcular la probabilidad de compra en cada mensaje.
- El costo del reparto de Hill climbing (ia.busqueda) para elegir al vendedor cuando deriva un chat.
"""
import re
import unicodedata
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone

from ia import busqueda, servicio

from .models import Cliente, Evento, Mensaje, Producto, RespuestaKinti

ALMACEN = "Cercado de Lima"
ENVIO_PROVINCIA = Decimal("15")
UMBRAL_CALIFICADO = 0.80
ABIERTAS = ("nuevo", "calificado", "cotizado")

ALIAS = {"sjl": "San Juan de Lurigancho", "ves": "Villa El Salvador", "surco": "Santiago de Surco",
         "smp": "San Martín de Porres", "sjm": "San Juan de Miraflores", "cercado": "Cercado de Lima",
         "centro de lima": "Cercado de Lima", "lima centro": "Cercado de Lima", "mesa redonda": "Cercado de Lima"}
PROVINCIAS = ["arequipa", "trujillo", "cusco", "piura", "chiclayo", "ica", "huancayo", "tacna", "puno", "iquitos",
              "chimbote", "huanuco", "cajamarca", "ayacucho", "tarapoto", "juliaca", "huaraz", "tumbes", "provincia"]

INTENCIONES = {
    "saludo": ["hola", "buenas", "buenos dias", "buen dia", "buenas tardes", "buenas noches", "alo"],
    "precio": ["precio", "cuanto", "cuesta", "costo", "vale", "a como"],
    "delivery": ["delivery", "envio", "envian", "llega", "llegan", "mandan", "despacho", "enviar", "reparto", "envias"],
    "compra": ["quiero pagar", "pago hoy", "comprar", "compro", "lo llevo", "la llevo", "me lo llevo", "me la llevo",
               "separar", "separo", "lo quiero", "la quiero", "hago el pedido", "confirmo", "te yapeo", "yapeo", "quiero pedir"],
    "humano": ["persona", "asesor", "asesora", "humano", "vendedor", "vendedora", "alguien del equipo", "llamame", "llamada"],
    "catalogo": ["catalogo", "que tienen", "que venden", "productos", "ofertas", "promociones", "modelos", "que mas tienen"],
    "objecion": ["caro", "descuento", "rebaja", "muy alto", "algo menos", "precio especial"],
    "gracias": ["gracias", "muchas gracias", "ok gracias"],
}
NUMEROS = {"un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6}


def normalizar(texto):
    t = unicodedata.normalize("NFD", (texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9ñ ]", " ", t)).strip()


def contiene(t, frase):
    return re.search(r"(?<![a-z0-9])" + re.escape(frase) + r"(?![a-z0-9])", t) is not None


def intenciones(t):
    return {k for k, frases in INTENCIONES.items() if any(contiene(t, f) for f in frases)}


def soles(valor):
    v = Decimal(valor)
    return f"S/ {v:,.0f}" if v == v.to_integral() else f"S/ {v:,.2f}"


def articulo(p, mayuscula=True):
    """«La freidora», «El termo»: femenino si la primera palabra termina en -a o es «sartén»."""
    w = normalizar(p.nombre).split(" ")[0]
    a = "la" if w.endswith("a") or w in ("sarten",) else "el"
    return a.capitalize() if mayuscula else a


def con_articulo(p):
    return f"{articulo(p)} {p.nombre[0].lower()}{p.nombre[1:]}"


def detectar_producto(t):
    mejor, puntos = None, 0
    for p in Producto.objects.filter(activo=True):
        n = sum(1 for w in p.palabras.split(",") if w.strip() and contiene(t, normalizar(w)))
        if n > puntos:
            mejor, puntos = p, n
    return mejor


def detectar_cantidad(t, producto=None):
    if producto:
        for w in producto.palabras.split(","):
            w = normalizar(w).split(" ")[0] if w.strip() else ""
            if w:
                m = re.search(r"(?<![a-z0-9])(\d{1,2}|dos|tres|cuatro|cinco|seis)\s+" + re.escape(w) + r"s?(?![a-z0-9])", t)
                if m:
                    return NUMEROS.get(m.group(1)) or int(m.group(1))
    m = re.search(r"(?<![a-z0-9])(\d{1,2}|un|una|dos|tres|cuatro|cinco|seis)\s*(unidades|unidad|de esas|de esos)", t) or \
        re.search(r"(?<![a-z0-9])x\s*(\d{1,2})(?![a-z0-9])", t) or re.search(r"(?<![a-z0-9])(\d{1,2})\s*x(?![a-z0-9])", t)
    if not m:
        return None
    v = m.group(1)
    n = NUMEROS.get(v) or int(v)
    return n if 1 <= n <= 50 else None


def detectar_lugar(t):
    """Devuelve (distrito_de_lima, None) o (None, ciudad_de_provincia) o (None, None)."""
    for alias, distrito in ALIAS.items():
        if contiene(t, alias):
            return distrito, None
    for d in sorted(busqueda.DISTRITOS, key=len, reverse=True):
        if contiene(t, normalizar(d)):
            return d, None
    for c in PROVINCIAS:
        if contiene(t, c):
            return None, c.title() if c != "provincia" else "provincia"
    return None, None


def cotizar_delivery(distrito):
    """A* desde el almacén: el costo crece con los km reales de la ruta (mínimo S/ 6)."""
    ruta = busqueda.a_estrella(ALMACEN, distrito)
    km = ruta["km"] if ruta else 15
    costo = max(6, round(4 + 0.35 * km))
    return {"km": km, "costo": Decimal(costo), "plazo": "24 h" if km <= 20 else "48 h", "camino": ruta["camino"] if ruta else []}


def recalcular_monto(c):
    base = (c.producto.precio * c.cantidad) if c.producto else Decimal("0")
    c.monto = base + (c.delivery or 0)


def avanzar(c, *destinos):
    """Recorre el grafo de la conversación: solo pasa a un estado si existe la transición desde el estado actual."""
    for destino in destinos:
        for _accion, sig in busqueda.FLUJO.get(c.estado_conv, []):
            if sig == destino:
                c.estado_conv = destino
                break


def ir_a(c, destino):
    """Lleva la conversación hasta `destino` por el camino más corto del grafo (BFS de ia.busqueda)."""
    if c.estado_conv == destino:
        return
    r = busqueda.bfs(inicio=c.estado_conv, objetivo=destino)
    if r:
        c.estado_conv = destino


# ------------------------------------------------------------------ IA: calificación y reparto
def calificar(c, ahora=None):
    ahora = ahora or timezone.now()
    primero = c.mensajes.filter(autor="cliente").order_by("creado").first()
    hora = timezone.localtime(primero.creado if primero else ahora).hour
    r = servicio.calificar({
        "minutos_respuesta": 0.1, "fuera_de_horario": not (9 <= hora < 19), "origen": c.origen,
        "pidio_precio": c.pidio_precio, "pidio_delivery": c.pidio_delivery,
        "mensajes": c.mensajes.filter(autor="cliente").count(), "provincia": c.provincia,
        "precio": float(c.producto.precio) if c.producto else 279,
    })
    c.probabilidad, c.etiqueta_ia = r["probabilidad_compra"], r["etiqueta"]
    return r


def vendedores_activos():
    return get_user_model().objects.filter(is_active=True, perfil__rol="ventas").select_related("perfil").annotate(
        carga=Count("clientes", filter=Q(clientes__etapa__in=ABIERTAS))).order_by("id")


def elegir_vendedor(c):
    """Mismo costo que el Hill climbing del Avance 3: espera por urgencia + zona + especialidad + exceso de capacidad."""
    urgencia = 3 if (c.probabilidad or 0) >= 0.8 else 2 if (c.probabilidad or 0) >= 0.6 else 1
    zona = "Provincia" if c.provincia else "Lima"
    categoria = c.producto.categoria if c.producto else "cocina"
    mejor, mejor_costo = None, None
    desde = c.creado - timedelta(hours=24)
    for v in vendedores_activos():
        # carga = chats abiertos + chats que recibió en las últimas 24 h (reparte el trabajo del día)
        recientes = Cliente.objects.filter(vendedor=v, creado__gte=desde, creado__lte=c.creado).exclude(etapa__in=ABIERTAS).count()
        carga = v.carga + recientes + 1
        costo = urgencia * carga * busqueda.MIN_POR_CLIENTE / 10
        costo += 8 if v.perfil.zona != zona else 0
        costo += 3 if v.perfil.especialidad != categoria else 0
        costo += 10 * max(0, carga - v.perfil.capacidad)
        if mejor_costo is None or costo < mejor_costo:
            mejor, mejor_costo = v, costo
    return mejor


def reasignar_sin_vendedor(ahora=None, usuario=None):
    """Reparte con Hill climbing (ia.busqueda.hill_climbing) todos los chats abiertos que no tienen vendedor."""
    ahora = ahora or timezone.now()
    pendientes = list(Cliente.objects.filter(vendedor__isnull=True, etapa__in=ABIERTAS).select_related("producto"))
    vend = list(vendedores_activos())
    if not pendientes or not vend:
        return {"asignados": 0, "costo_inicial": 0, "costo_final": 0, "reparto": []}
    leads = [{"id": c.id, "zona": "Provincia" if c.provincia else "Lima",
              "categoria": c.producto.categoria if c.producto else "cocina",
              "urgencia": 3 if (c.probabilidad or 0) >= 0.8 else 2 if (c.probabilidad or 0) >= 0.6 else 1} for c in pendientes]
    vs = [{"nombre": str(i), "zona": v.perfil.zona, "especialidad": v.perfil.especialidad, "carga": v.carga,
           "capacidad": v.perfil.capacidad} for i, v in enumerate(vend)]
    r = busqueda.hill_climbing(leads, vs)
    reparto = []
    for c, a in zip(pendientes, r["asignacion"]):
        v = vend[int(a["vendedor"])]
        c.vendedor = v
        c.actualizado = ahora
        c.save(update_fields=["vendedor", "actualizado"])
        Evento.objects.create(cliente=c, tipo="asignado", texto=f"Asignado a {v.get_full_name()} por Hill climbing", usuario=usuario, creado=ahora)
        reparto.append({"cliente": c.nombre, "vendedor": v.get_full_name()})
    return {"asignados": len(reparto), "costo_inicial": r["costo_inicial"], "costo_final": r["costo_final"], "reparto": reparto}


def derivar(c, motivo, ahora, usuario=None):
    if not c.vendedor:
        c.vendedor = elegir_vendedor(c)
    c.kinti_activo = False
    if c.etapa == "nuevo":
        c.etapa = "calificado"
    nombre = c.vendedor.get_full_name() if c.vendedor else "el equipo"
    Mensaje.objects.create(cliente=c, autor="sistema", texto=f"Kinti · IA derivó a {nombre} · {motivo}", creado=ahora)
    Evento.objects.create(cliente=c, tipo="derivado", texto=f"Derivada a {nombre} por Kinti · IA ({motivo})", usuario=usuario, creado=ahora)
    return c.vendedor


# ------------------------------------------------------------------ Respuesta
def respuesta_entrenada(t):
    mejor, puntos = None, 0
    for r in RespuestaKinti.objects.filter(activa=True):
        n = sum(1 for w in r.palabras.split(",") if w.strip() and contiene(t, normalizar(w)))
        if n > puntos:
            mejor, puntos = r, n
    return mejor


def responder(c, texto, ahora=None, segundos=None, guardar=True):
    """Procesa el mensaje del cliente (ya guardado) y crea las respuestas de Kinti. Devuelve la lista de mensajes de Kinti.

    Con guardar=False solo devuelve los textos (para la prueba de Entrenamiento) y no toca la base de datos.
    """
    ahora = ahora or timezone.now()
    t = normalizar(texto)
    quiere = intenciones(t)
    partes, tarjeta, derivar_por = [], None, None
    primer_nombre = c.nombre.split()[0] if c.nombre else ""

    # 1) Saludo inicial (inicio → saludo)
    if c.estado_conv == "inicio":
        avanzar(c, "saludo")
        partes.append(f"¡Hola{', ' + primer_nombre if primer_nombre else ''}! Soy Kinti, asistente virtual de Kusi Hogar. "
                      "Te respondo al toque y, si quieres, te paso con una persona del equipo.")

    # 2) Lo que el cliente menciona: producto, cantidad y lugar
    producto = detectar_producto(t)
    cantidad = detectar_cantidad(t, producto or c.producto)
    distrito, ciudad = detectar_lugar(t)
    nuevo_producto = producto is not None and producto != c.producto
    if producto:
        c.producto = producto
    if cantidad:
        c.cantidad = cantidad
    if distrito:
        c.distrito, c.provincia = distrito, False
    elif ciudad:
        c.provincia = True
        if ciudad != "provincia":
            c.distrito = ciudad

    # 3) Entrenamiento (respuestas que cargó el equipo); se agrega después del precio y el delivery
    entrenada = respuesta_entrenada(t)

    # 4) Catálogo
    if "catalogo" in quiere and not producto:
        top = list(Producto.objects.filter(activo=True, mas_vendido=True)[:3]) or list(Producto.objects.filter(activo=True)[:3])
        lista = ", ".join(f"{p.nombre} ({soles(p.precio)})" for p in top)
        partes.append(f"Te dejo lo más vendido: {lista}. ¿Cuál te interesa?")
        avanzar(c, "consulta_general", "catalogo_enviado")

    # 5) Producto y precio (… → producto_identificado → precio_informado)
    ya_dio_precio = c.pidio_precio and not nuevo_producto
    repetir = "precio" in quiere and not (ya_dio_precio and ("delivery" in quiere or distrito or ciudad))
    if c.producto and (nuevo_producto or repetir):
        if c.estado_conv in ("saludo", "consulta_general", "catalogo_enviado"):
            ir_a(c, "producto_identificado")
        p = c.producto
        if p.stock == 0 and "Sin stock" in c.etiquetas:
            partes.append(f"Cuesta {soles(p.precio)}. Apenas llegue el stock te aviso por aquí.")
        elif p.stock == 0:
            fem = articulo(p) == "La"
            partes.append(f"{con_articulo(p)} ({soles(p.precio)}) está {'agotada' if fem else 'agotado'} por ahora; llega la próxima semana. "
                          f"Si quieres, te {'la' if fem else 'lo'} separo.")
            if "Sin stock" not in c.etiquetas:
                c.etiquetas = c.etiquetas + ["Sin stock"]
        else:
            extra = f" ({c.cantidad} unidades: {soles(p.precio * c.cantidad)})" if c.cantidad > 1 else ""
            partes.append(f"{con_articulo(p)} está a {soles(p.precio)}{extra} y tiene {p.garantia_meses} meses de garantía. Te dejo la ficha:")
            tarjeta = p
        c.pidio_precio = True
        avanzar(c, "stock_verificado", "precio_informado")
        if guardar:
            Evento.objects.create(cliente=c, tipo="precio", texto=f"Precio enviado · {soles(p.precio)} por Kinti · IA", creado=ahora)
    elif "precio" in quiere and not c.producto:
        partes.append("¿De qué producto quieres el precio? Tenemos freidoras de aire, licuadoras, ollas arroceras, baterías de ollas y más.")
        avanzar(c, "consulta_general")

    # 6) Objeción de precio → promoción
    if "objecion" in quiere and c.producto:
        avanzar(c, "objecion_precio")
        partes.append("Te entiendo. Si confirmas hoy, el delivery en Lima te sale a mitad de precio y mantienes la garantía completa.")
        avanzar(c, "precio_informado")
        if c.delivery:
            c.delivery = (c.delivery / 2).quantize(Decimal("1"))

    # 7) Delivery con A* (precio_informado → delivery_cotizado)
    if "delivery" in quiere or distrito or ciudad:
        c.pidio_delivery = True
        if c.provincia:
            c.delivery = ENVIO_PROVINCIA
            lugar = c.distrito if c.distrito and c.distrito != "provincia" else "provincia"
            msg = f"Sí, enviamos a {lugar} por agencia (Shalom) en 2 a 3 días; el envío cuesta {soles(ENVIO_PROVINCIA)}."
        elif c.distrito in busqueda.DISTRITOS:
            d = cotizar_delivery(c.distrito)
            c.delivery = d["costo"]
            msg = f"Sí, llega a {c.distrito} en {d['plazo']}. El delivery cuesta {soles(d['costo'])}."
        else:
            msg = "¿A qué distrito te lo enviamos? Así te digo el costo y el tiempo de entrega."
        if c.producto and c.delivery is not None:
            recalcular_monto(c)
            msg = msg.rstrip(".") + f": en total serían {soles(c.monto)}."
            if c.estado_conv in ("producto_identificado", "stock_verificado"):
                avanzar(c, "precio_informado")
            avanzar(c, "delivery_cotizado")
        partes.append(msg)

    if entrenada and not (tarjeta and normalizar(entrenada.tema).startswith("garantia")):
        partes.append(entrenada.respuesta)
        if guardar:
            RespuestaKinti.objects.filter(id=entrenada.id).update(usos=entrenada.usos + 1)

    # 8) Quiere pagar o pide una persona → deriva al vendedor (datos_cliente → listo_para_pagar)
    if "compra" in quiere:
        if c.producto:
            ir_a(c, "datos_cliente")
            avanzar(c, "listo_para_pagar")
            derivar_por = "quiere pagar"
        else:
            partes.append("¡Genial! ¿Qué producto quieres llevar? Te paso precio y delivery al toque.")
    if "humano" in quiere and not derivar_por:
        derivar_por = "pidió hablar con una persona"

    if "gracias" in quiere and not partes and not derivar_por:
        partes.append("¡Gracias a ti! Cualquier consulta me escribes por aquí.")
    if not partes and not derivar_por:
        if c.producto:
            partes.append("¿Te cotizo el delivery a tu distrito o prefieres que te pase con un asesor para el pago?")
        else:
            partes.append("¿Me cuentas qué producto buscas? Así te paso el precio y el delivery al toque.")
            avanzar(c, "consulta_general")

    recalcular_monto(c)
    if not guardar:
        if derivar_por:
            partes.append(f"(Derivaría el chat a un vendedor: {derivar_por})")
        return partes

    # 9) IA: probabilidad de compra con la regresión logística
    calificar(c, ahora)
    if c.etapa == "nuevo" and c.producto and (c.probabilidad or 0) >= UMBRAL_CALIFICADO:
        c.etapa = "calificado"
        Evento.objects.create(cliente=c, tipo="etapa", texto=f"Calificado por IA · {round(c.probabilidad * 100)} % de probabilidad de compra", creado=ahora)
        if not c.vendedor:
            c.vendedor = elegir_vendedor(c)
            if c.vendedor:
                Evento.objects.create(cliente=c, tipo="asignado", texto=f"Asignado a {c.vendedor.get_full_name()} por Kinti · IA", creado=ahora)

    creados, paso = [], 0
    seg = segundos if segundos is not None else max(0.4, (timezone.now() - ahora).total_seconds())
    for i, texto_k in enumerate(partes):
        paso += 1
        m = Mensaje.objects.create(cliente=c, autor="kinti", texto=texto_k, segundos_respuesta=seg if i == 0 else None,
                                   producto=tarjeta if (tarjeta and texto_k.endswith("Te dejo la ficha:")) else None,
                                   creado=ahora + timedelta(seconds=seg + paso - 1))
        creados.append(m)
    if derivar_por:
        cuando = ahora + timedelta(seconds=seg + paso)
        v = derivar(c, derivar_por, cuando)
        nombre = v.first_name if v else "un asesor"
        m = Mensaje.objects.create(cliente=c, autor="kinti", creado=cuando,
                                   texto=f"Perfecto. Te paso con {nombre} del equipo para {'el pago y confirmar la dirección' if derivar_por == 'quiere pagar' else 'que te atienda'}. Te escribe en unos minutos.")
        creados.append(m)
    c.actualizado = creados[-1].creado if creados else ahora
    c.save()
    return creados


def recibir(c, texto, ahora=None, segundos=None, externo_id=""):
    """Guarda el mensaje del cliente y, si Kinti está a cargo, responde."""
    ahora = ahora or timezone.now()
    Mensaje.objects.create(cliente=c, autor="cliente", texto=texto, creado=ahora, externo_id=externo_id)
    c.no_leidos += 1
    c.actualizado = ahora
    if c.kinti_activo and c.etapa not in ("ganado", "perdido"):
        return responder(c, texto, ahora=ahora, segundos=segundos)
    if c.pidio_precio is False and "precio" in intenciones(normalizar(texto)):
        c.pidio_precio = True
    calificar(c, ahora)
    c.save()
    return []
