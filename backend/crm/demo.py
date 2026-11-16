"""Datos de demostración del CRM: Kusi Hogar S.A.C. (empresa FICTICIA, importadora de electrohogar en Mesa Redonda).

Las conversaciones no están escritas a mano de punta a punta: los mensajes de los clientes pasan por el motor real de
Kinti (crm.kinti), así que las respuestas, la calificación con la regresión logística, el delivery con A* y el reparto
son exactamente los que da la IA en producción.
"""
import random
import secrets
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from . import kinti
from .models import Cliente, Evento, Mensaje, Perfil, Producto, RespuestaKinti

USUARIOS = [
    # correo, nombre, apellido, rol, cargo, zona, especialidad, color, meta mensual, capacidad
    ("carla@kusihogar.pe", "Carla", "Mendoza", "admin", "Administradora", "Lima", "hogar", "#1E2E4E", 0, 12),
    ("jorge@kusihogar.pe", "Jorge", "Salas", "gerente", "Gerente comercial", "Lima", "hogar", "#0B6E85", 0, 12),
    ("diego@kusihogar.pe", "Diego", "Quispe", "ventas", "Ventas · Lima", "Lima", "cocina", "#0EB155", 8000, 14),
    ("milagros@kusihogar.pe", "Milagros", "Rojas", "ventas", "Ventas · Lima", "Lima", "hogar", "#16B6D8", 5000, 14),
    ("kevin@kusihogar.pe", "Kevin", "Huamán", "ventas", "Ventas · Provincias", "Provincia", "menaje", "#14213A", 3000, 10),
]

PRODUCTOS = [
    # nombre, categoría, detalle, precio, stock, garantía, foto, palabras, más vendido, nombre corto
    ("Freidora de aire 5 L", "cocina", "Cocina eléctrica", 279, 18, 12, "freidora-aire", "freidora,freidora de aire,air fryer,airfryer,freidoras", True, "freidora de aire"),
    ("Aspiradora sin bolsa 2000 W", "hogar", "Limpieza", 459, 7, 12, "aspiradora", "aspiradora,aspiradora sin bolsa", True, "aspiradora"),
    ("Batería de ollas 9 piezas", "menaje", "Acero inoxidable", 349, 12, 24, "bateria-ollas", "bateria,bateria de ollas,juego de ollas,ollas", True, "batería de ollas"),
    ("Batidora de pedestal 5 L", "cocina", "Repostería", 399, 6, 12, "batidora", "batidora,batidora de pedestal", False, "batidora de pedestal"),
    ("Olla arrocera 1.8 L", "cocina", "Cocina eléctrica", 129, 25, 12, "olla-arrocera", "arrocera,olla arrocera", False, "olla arrocera"),
    ("Licuadora 1.5 L 700 W", "cocina", "Cocina eléctrica", 189, 15, 12, "licuadora", "licuadora", False, "licuadora"),
    ("Termo acero 1 L", "menaje", "Colores surtidos", 59, 40, 6, "termo", "termo,termos", False, "termo"),
    ("Hervidor eléctrico 1.7 L", "cocina", "Cocina eléctrica", 99, 20, 12, "hervidor", "hervidor,tetera,hervidor electrico", False, "hervidor"),
    ("Sartén antiadherente 28 cm", "menaje", "Menaje", 79, 30, 6, "sarten", "sarten,sartenes", False, "sartén"),
    ("Ventilador de torre", "hogar", "Hogar", 219, 0, 12, "ventilador-torre", "ventilador,ventilador de torre", False, "ventilador de torre"),
]

RESPUESTAS = [
    ("Garantía", "garantia,falla,se malogra,malogro,defecto",
     "Todos nuestros productos tienen garantía de 6 a 24 meses según el modelo. Si algo falla, lo cambiamos en tienda o lo recogemos sin costo en Lima."),
    ("Tienda y horario", "tienda,direccion,ubicacion,donde estan,donde queda,horario,atienden,local",
     "Nuestra tienda está en Mesa Redonda (Cercado de Lima) y atiende de lunes a sábado de 9 a. m. a 7 p. m. Por aquí te respondo las 24 horas."),
    ("Formas de pago", "yape,plin,tarjeta,transferencia,formas de pago,metodos de pago,como pago,contraentrega,contra entrega",
     "Puedes pagar con Yape, Plin, transferencia o tarjeta (te enviamos un link de pago). En Lima también aceptamos pago contraentrega."),
    ("Venta por mayor", "por mayor,mayorista,al por mayor,docena,revender,reventa",
     "Sí vendemos por mayor: desde 6 unidades del mismo producto tienes precio especial. Un asesor te prepara la cotización."),
    ("Cambios y devoluciones", "cambio,devolucion,devolver,cambiar",
     "Tienes 7 días para cambios con la caja y el comprobante. Si llegó dañado, lo cambiamos sin costo."),
    ("Boleta o factura", "factura,ruc,boleta,comprobante",
     "Emitimos boleta o factura electrónica. Para factura solo envíanos tu RUC."),
]

NOMBRES = ["Ana", "Luis", "María", "José", "Rocío", "Jorge", "Patricia", "Miguel", "Carmen", "César", "Lucía", "Javier", "Silvia",
           "Ricardo", "Milagros", "Fernando", "Gladys", "Víctor", "Rosa", "Hugo", "Karina", "Pablo", "Diana", "Raúl", "Yesenia",
           "Marco", "Flor", "Alberto", "Sandra", "Eduardo", "Pilar", "Wilmer", "Liliana", "Renzo", "Maribel", "Gustavo"]
APELLIDOS = ["Quispe", "Flores", "Sánchez", "Rojas", "Huamán", "Mendoza", "Chávez", "Torres", "Ramos", "Vargas", "Castillo",
             "Paredes", "Gutiérrez", "Espinoza", "Salazar", "Cárdenas", "Rivera", "Mamani", "Alvarado", "Díaz", "Romero", "Herrera"]
DISTRITOS_LIMA = ["San Juan de Lurigancho", "Comas", "Los Olivos", "San Martín de Porres", "Ate", "Villa El Salvador", "Santiago de Surco",
                  "Callao", "Chorrillos", "La Victoria", "San Juan de Miraflores", "Independencia", "Miraflores", "La Molina",
                  "Santa Anita", "Breña", "Rímac", "San Borja", "Jesús María", "Lince", "Surquillo"]
CIUDADES = ["Arequipa", "Trujillo", "Piura", "Chiclayo", "Cusco", "Huancayo", "Ica"]
CAMPANAS = {"meta": ["Freidoras de aire", "Cocina práctica", "Hogar limpio", "Instagram · menaje"],
            "google": ["Búsqueda Google", "Google Shopping"], "organico": ["Instagram orgánico", "TikTok"], "directo": ["Recomendación"]}

GUIONES = {
    "compra": [["Hola, vi su anuncio de la {p}. ¿Cuánto está?", "¿Hacen delivery a {d}?", "Ya, quiero pagar hoy"],
               ["Buenas, ¿precio de la {p}?", "Ok, la quiero. Estoy en {d}"],
               ["Hola, ¿tienen catálogo?", "¿Cuánto cuesta la {p}?", "¿Llega a {d}? Lo llevo"]],
    "interes": [["Hola, ¿cuánto está la {p}?", "¿Y el delivery a {d}?"],
                ["¿Precio de la {p}? Estoy en {d}"]],
    "provincia": [["Hola, ¿envían a {c}?", "Me interesa la {p}, ¿cuánto sale?", "Ya, la quiero"],
                  ["Buenas, ¿la {p} llega a {c}?"]],
    "humano": [["Hola", "Quiero info de la {p}, ¿me atiende un asesor?"]],
    "objecion": [["Precio de la {p}", "Está algo caro, ¿algún descuento?"]],
    "frio": [["Hola", "Info"], ["¿Dónde está su tienda?"], ["Hola, ¿qué ofertas tienen?"]],
}

HOY = [
    # nombre, lugar, origen, campaña, minutos atrás, mensajes del cliente, vendedor (texto, tipo, minutos después), cierre
    ("Martín Ríos", "San Juan de Lurigancho", "meta", "Freidoras de aire", 4,
     ["Hola, soy Martín. Me interesa la freidora de aire, ¿cuánto está?"], None, None),
    ("Kelly Ramos", "San Borja", "organico", "Instagram orgánico", 11, ["Hola, ¿qué productos tienen en oferta?"], None, None),
    ("Ana Torres", "Rímac", "directo", "Recomendación", 23, ["Buenas, ¿dónde está su tienda?", "¿Y el hervidor cuánto cuesta?"], None, None),
    ("Rosa Huamaní", "Comas", "meta", "Freidoras de aire", 38,
     ["Hola, vi su anuncio de la freidora de aire. ¿Cuánto está y tiene garantía?", "Ya, me gusta. ¿Llega a Comas? Quiero pagar hoy"],
     ("Hola Rosa, soy {v}. Te envío el link de pago por {monto} (freidora + delivery).", "pago", 6), None),
    ("Óscar Medina", "Piura", "meta", "Cocina práctica", 52, ["Hola, ¿la licuadora llega a Piura?"], None, None),
    ("Elena Quispe", "Villa El Salvador", "meta", "Instagram · menaje", 64, ["Hola", "¿Me atiende una persona? Quiero 3 termos color verde"], None, None),
    ("Andrea Salazar", "Miraflores", "organico", "Instagram orgánico", 80,
     ["Hola, ¿la batidora de pedestal viene con garantía?", "¿Cuánto cuesta y llega a Miraflores?"],
     ("Hola Andrea, soy {v}. Te envío la cotización: batidora de pedestal 5 L + delivery a Miraflores = {monto}.", "cotizacion", 12), None),
    ("Pedro Cárdenas", "Callao", "meta", "Cocina práctica", 96, ["Buenas, precio de la licuadora", "¿Hacen delivery al Callao?"], None, None),
    ("Gaby Torres", "Los Olivos", "meta", "Cocina práctica", 185, ["Hola, quiero la olla arrocera", "Estoy en Los Olivos, la quiero hoy"],
     ("Hola Gaby, soy {v}. Te envío el link de pago por {monto}.", "pago", 5), ("ganado", 40)),
    ("Carlos Mamani", "Trujillo", "meta", "Freidoras de aire", 210, ["Si llevo 2 freidoras, ¿me hacen precio?", "Es para Trujillo"],
     ("Hola Carlos, soy {v}. Por 2 freidoras con envío por Shalom te queda en {monto}. Te dejo la cotización.", "cotizacion", 18), None),
    ("Lucía Fernández", "Santiago de Surco", "google", "Búsqueda Google", 300, ["Hola, precio de la aspiradora sin bolsa", "¿Llega a Surco? La quiero"],
     ("Hola Lucía, soy {v}. Te envío el link de pago por {monto}.", "pago", 7), ("ganado", 35)),
    ("Raúl Benites", "Chorrillos", "google", "Google Shopping", 345, ["Buenos días, la aspiradora cuánto cuesta", "¿Delivery a Chorrillos? Quiero pagar"],
     ("Hola Raúl, soy {v}. Te envío el link de pago por {monto}.", "pago", 4), ("ganado", 30)),
    ("Sofía Vargas", "La Molina", "meta", "Instagram · menaje", 24 * 60 + 70,
     ["Hola, me interesa la batería de ollas", "¿Cuánto sería con delivery a La Molina?"], None, None),
    ("Luis Ramos", "Ate", "google", "Búsqueda Google", 26 * 60, ["Hola, ¿tienen ventilador de torre?", "¿Cuánto cuesta?"], None, ("perdido", 90, "Sin stock")),
    ("Jhon Paredes", "Arequipa", "google", "Búsqueda Google", 3 * 24 * 60 + 150, ["Hola, ¿envían a Arequipa?", "Me interesa la batería de ollas, ¿cuánto sale?"],
     ("Hola Jhon, soy {v}. Te cotizo la batería con envío por Shalom: {monto}.", "cotizacion", 20), None),
]


def _clave():
    return settings.CRM_CLAVE_DEMO or secrets.token_urlsafe(10)


def _usuarios(clave, conservar):
    User = get_user_model()
    creados = 0
    for correo, nombre, apellido, rol, cargo, zona, esp, color, meta, cap in USUARIOS:
        u = User.objects.filter(username=correo).first()
        if u and conservar:
            continue
        if not u:
            u = User(username=correo, email=correo)
            creados += 1
        u.first_name, u.last_name, u.is_active = nombre, apellido, True
        u.set_password(clave)
        u.save()
        Perfil.objects.update_or_create(usuario=u, defaults=dict(rol=rol, cargo=cargo, zona=zona, especialidad=esp, color=color,
                                                                  meta_mensual=Decimal(meta), capacidad=cap))
    return creados


def _crear_chat(nombre, lugar, origen, campana, inicio, mensajes, rnd):
    c = Cliente.objects.create(nombre=nombre, telefono=f"+51 9{rnd.randint(10, 99)} {rnd.randint(100, 999)} {rnd.randint(100, 999)}",
                               origen=origen, campana=campana, creado=inicio, actualizado=inicio)
    Evento.objects.create(cliente=c, tipo="creado", texto=f"Creada desde {c.get_origen_display()} · {campana}", creado=inicio)
    t = inicio
    for i, texto in enumerate(mensajes):
        kinti.recibir(c, texto, ahora=t, segundos=rnd.choice([3, 4, 5, 6, 7, 8]))
        t = c.actualizado + timedelta(minutes=rnd.randint(1, 5))
    if lugar and not c.distrito:
        c.distrito = lugar
        c.save(update_fields=["distrito"])
    return c


def _vendedor_dice(c, texto, t, tipo=None):
    if not c.vendedor:
        c.vendedor = kinti.elegir_vendedor(c)
    v = c.vendedor
    texto = texto.replace("{v}", v.first_name).replace("{monto}", kinti.soles(c.monto))
    Mensaje.objects.create(cliente=c, autor="vendedor", usuario=v, texto=texto, creado=t)
    if c.kinti_activo:
        c.kinti_activo = False
        Evento.objects.create(cliente=c, tipo="tomado", texto=f"{v.get_full_name()} tomó el chat", usuario=v, creado=t)
    if tipo == "cotizacion" and c.etapa in ("nuevo", "calificado"):
        c.etapa = "cotizado"
        Evento.objects.create(cliente=c, tipo="etapa", texto=f"Cotización enviada por {v.first_name} · {kinti.soles(c.monto)}", usuario=v, creado=t)
    if tipo == "pago":
        Evento.objects.create(cliente=c, tipo="pago", texto=f"Link de pago enviado por {v.first_name}", usuario=v, creado=t)
    c.no_leidos, c.actualizado = 0, t
    c.save()


def _cerrar(c, etapa, t, motivo=""):
    t = min(t, timezone.now() - timedelta(minutes=3))  # nunca en el futuro
    previa = c.get_etapa_display()
    if etapa == "ganado" and not c.vendedor:
        c.vendedor = kinti.elegir_vendedor(c)
    c.etapa, c.cerrado, c.motivo_perdida, c.kinti_activo = etapa, t, motivo, False
    quien = c.vendedor.first_name if c.vendedor else "el equipo"
    if etapa == "ganado":
        Mensaje.objects.create(cliente=c, autor="vendedor", usuario=c.vendedor, creado=t,
                               texto=f"¡Pago recibido, {c.nombre.split()[0]}! Tu pedido sale hoy. Gracias por comprar en Kusi Hogar.")
    extra = f" · motivo: {motivo}" if motivo else ""
    Evento.objects.create(cliente=c, tipo="etapa", texto=f"{previa} → {c.get_etapa_display()} por {quien}{extra}", usuario=c.vendedor, creado=t)
    c.actualizado = max(c.actualizado, t)
    c.no_leidos = 0
    c.save()


def _historial(rnd, ahora, productos, cortos):
    """Unos 150 chats de los últimos 29 días (más los sábados) para que el dashboard tenga historia."""
    pesos = [30, 12, 12, 7, 12, 9, 6, 6, 4, 2]
    hoy = timezone.localtime(ahora).date()
    for atras in range(29, 0, -1):
        dia = hoy - timedelta(days=atras)
        n = {5: 9, 6: 7}.get(dia.weekday(), 5) + rnd.randint(-1, 2)
        for _ in range(n):
            hora = rnd.choice([9, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20, 21, 22])
            inicio = timezone.make_aware(datetime.combine(dia, time(hora, rnd.randint(0, 59))))
            origen = rnd.choices(["meta", "google", "organico", "directo"], [55, 25, 12, 8])[0]
            i = rnd.choices(range(len(productos)), pesos)[0]
            tipo = rnd.choices(["compra", "interes", "provincia", "humano", "objecion", "frio"], [17, 20, 13, 8, 14, 28])[0]
            if productos[i].stock == 0:
                tipo = "interes"
            d, ciudad = rnd.choice(DISTRITOS_LIMA), rnd.choice(CIUDADES)
            if d not in kinti.busqueda.DISTRITOS:
                d = "Cercado de Lima"
            guion = [m.format(p=cortos[i], d=d, c=ciudad) for m in rnd.choice(GUIONES[tipo])]
            nombre = f"{rnd.choice(NOMBRES)} {rnd.choice(APELLIDOS)}"
            c = _crear_chat(nombre, ciudad if tipo == "provincia" else d, origen, rnd.choice(CAMPANAS[origen]), inicio, guion, rnd)
            t = c.actualizado + timedelta(minutes=rnd.randint(2, 35))
            if c.producto and c.producto.stock == 0:
                _cerrar(c, "perdido", t + timedelta(hours=2), "Sin stock")
                continue
            if tipo in ("compra", "provincia") and c.producto:
                _vendedor_dice(c, "Hola " + c.nombre.split()[0] + ", soy {v}. Te envío el link de pago por {monto}.", t, "pago")
                r = rnd.random()
                if r < 0.6:
                    _cerrar(c, "ganado", t + timedelta(minutes=rnd.randint(15, 300)))
                elif r < 0.86 or atras > 4:
                    _cerrar(c, "perdido", t + timedelta(days=1), rnd.choice(["Sin respuesta", "Compró en otro lado"]))
            elif tipo in ("interes", "humano") and (c.producto or tipo == "humano"):
                if c.producto:
                    _vendedor_dice(c, "Hola " + c.nombre.split()[0] + ", soy {v}. Te envío la cotización con delivery: {monto}. ¿Te la separo?", t, "cotizacion")
                else:
                    _vendedor_dice(c, "Hola " + c.nombre.split()[0] + ", soy {v}. ¿En qué te ayudo?", t)
                r = rnd.random()
                if r < 0.3 and c.producto:
                    _cerrar(c, "ganado", t + timedelta(hours=rnd.randint(1, 20)))
                elif r < 0.8 or atras > 5:
                    _cerrar(c, "perdido", t + timedelta(days=1), rnd.choice(["Precio", "Sin respuesta", "Compró en otro lado"]))
            elif atras > 3 or rnd.random() < 0.6:
                _cerrar(c, "perdido", t + timedelta(days=1), rnd.choice(["Sin respuesta", "Precio"]) if c.producto else "Sin respuesta")
            if c.etapa in ("ganado", "perdido") or atras > 1:
                Cliente.objects.filter(id=c.id).update(no_leidos=0)


def _hoy(rnd, ahora):
    for nombre, lugar, origen, campana, hace, mensajes, vend, cierre in HOY:
        inicio = ahora - timedelta(minutes=hace)
        c = _crear_chat(nombre, lugar, origen, campana, inicio, mensajes, rnd)
        if vend:
            texto, tipo, despues = vend
            _vendedor_dice(c, texto, c.actualizado + timedelta(minutes=despues), tipo)
        if cierre:
            _cerrar(c, cierre[0], c.actualizado + timedelta(minutes=cierre[1]), cierre[2] if len(cierre) > 2 else "")
        if c.etapa in ("ganado", "perdido"):
            Cliente.objects.filter(id=c.id).update(no_leidos=0)
    # notas internas de ejemplo
    rosa = Cliente.objects.filter(nombre="Rosa Huamaní").first()
    if rosa and rosa.vendedor:
        Mensaje.objects.create(cliente=rosa, autor="nota", usuario=rosa.vendedor, creado=rosa.actualizado,
                               texto="Confirmar dirección antes de despachar. Llamarla después de las 6 p. m.")
        Cliente.objects.filter(id=rosa.id).update(etiquetas=["Freidora", "Delivery Comas", "Paga hoy", "Primera compra"])


@transaction.atomic
def cargar(reiniciar=False, conservar_usuarios=False):
    """Carga la demo. Sin `reiniciar` solo actúa si no hay clientes. Devuelve un resumen."""
    if not reiniciar and Cliente.objects.filter(whatsapp_jid="").exists():
        return {"cargado": False, "motivo": "ya hay datos"}
    clave = _clave()
    if reiniciar:
        Cliente.objects.filter(whatsapp_jid="").delete()  # los chats reales de WhatsApp se conservan
        Producto.objects.all().delete()
        RespuestaKinti.objects.all().delete()
    nuevos = _usuarios(clave, conservar=conservar_usuarios or reiniciar)
    productos, cortos = [], []
    for nombre, cat, det, precio, stock, gar, foto, palabras, top, corto in PRODUCTOS:
        productos.append(Producto.objects.create(nombre=nombre, categoria=cat, detalle=det, precio=Decimal(precio), stock=stock,
                                                 garantia_meses=gar, foto=foto, palabras=palabras, mas_vendido=top))
        cortos.append(corto)
    for tema, palabras, resp in RESPUESTAS:
        RespuestaKinti.objects.create(tema=tema, palabras=palabras, respuesta=resp)
    rnd = random.Random(2026)
    ahora = timezone.now()
    _historial(rnd, ahora, productos, cortos)
    _hoy(rnd, ahora)
    return {"cargado": True, "clientes": Cliente.objects.count(), "mensajes": Mensaje.objects.count(),
            "usuarios_creados": nuevos,
            "clave_generada": clave if nuevos and not settings.CRM_CLAVE_DEMO else None}
