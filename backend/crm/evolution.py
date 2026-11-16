"""WhatsApp real con Evolution API (contenedor `evolution` en el mismo VPS, sin exponerlo a internet).

- Django le habla a Evolution por la red interna de Docker (EVOLUTION_URL) con la API key del .env.
- Evolution avisa cada mensaje nuevo al webhook /api/wa/evolution?token=… (también por la red interna).
- Kinti responde con el mismo motor del CRM y las respuestas salen por el WhatsApp conectado.
- Filtro de seguridad: si está activo, solo entran al CRM los chats NUEVOS cuyo mensaje nombra la palabra clave
  (por defecto «kusi»), para que Kinti no le conteste a los contactos personales del número.
"""
import json
import logging
import re
import threading
import time
import urllib.error
import urllib.request

from django.conf import settings

log = logging.getLogger(__name__)
FILTRO_DEFECTO = {"activo": True, "palabra": "kusi"}


def habilitado():
    return bool(settings.EVOLUTION_URL and settings.EVOLUTION_API_KEY)


def _llamar(metodo, ruta, datos=None, timeout=15):
    req = urllib.request.Request(f"{settings.EVOLUTION_URL.rstrip('/')}{ruta}", method=metodo,
                                 data=json.dumps(datos).encode() if datos is not None else None,
                                 headers={"apikey": settings.EVOLUTION_API_KEY, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            cuerpo = r.read().decode() or "{}"
            return r.status, json.loads(cuerpo)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except ValueError:
            return e.code, {}
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, {"error": str(e)}


def _inst():
    return settings.EVOLUTION_INSTANCIA


def webhook_url():
    return f"{settings.EVOLUTION_WEBHOOK_BASE.rstrip('/')}/api/wa/evolution?token={settings.EVOLUTION_WEBHOOK_TOKEN}"


def _config_webhook():
    return {"enabled": True, "url": webhook_url(), "byEvents": False, "base64": False,
            "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"]}


def estado():
    """Estado de la conexión: sin_configurar | sin_instancia | close | connecting | open (+ número y nombre)."""
    if not habilitado():
        return {"estado": "sin_configurar"}
    cod, r = _llamar("GET", f"/instance/connectionState/{_inst()}")
    if cod == 0:
        return {"estado": "sin_servicio", "detalle": r.get("error")}
    if cod == 404:
        return {"estado": "sin_instancia"}
    st = (r.get("instance") or {}).get("state") or r.get("state") or "close"
    info = {"estado": st}
    if st == "open":
        cod2, lista = _llamar("GET", f"/instance/fetchInstances?instanceName={_inst()}")
        if cod2 == 200 and isinstance(lista, list) and lista:
            x = lista[0]
            info["numero"] = (x.get("ownerJid") or "").split("@")[0]
            info["nombre"] = x.get("profileName")
    return info


def conectar():
    """Crea la instancia si no existe, fija el webhook y devuelve el QR (base64) para escanear."""
    if not habilitado():
        return {"estado": "sin_configurar"}
    cod, r = _llamar("POST", "/instance/create", {
        "instanceName": _inst(), "integration": "WHATSAPP-BAILEYS", "qrcode": True, "groupsIgnore": True,
        "rejectCall": False, "alwaysOnline": False, "readMessages": False, "syncFullHistory": False,
        "webhook": _config_webhook()})
    qr = (r.get("qrcode") or {}).get("base64") if cod in (200, 201) else None
    _llamar("POST", f"/webhook/set/{_inst()}", {"webhook": _config_webhook()})
    if not qr:
        cod, r = _llamar("GET", f"/instance/connect/{_inst()}")
        qr = r.get("base64")
    e = estado()
    e["qr"] = qr
    return e


def desconectar():
    if not habilitado():
        return {"estado": "sin_configurar"}
    _llamar("DELETE", f"/instance/logout/{_inst()}")
    return estado()


def numero_de(jid):
    return re.sub(r"\D", "", (jid or "").split("@")[0].split(":")[0])


def _destino(jid):
    return numero_de(jid) if jid.endswith("@s.whatsapp.net") else jid


def _enviar_ya(jid, piezas):
    for p in piezas:
        if p.get("imagen"):
            cod, _ = _llamar("POST", f"/message/sendMedia/{_inst()}", {
                "number": _destino(jid), "mediatype": "image", "mimetype": "image/jpeg", "media": p["imagen"],
                "fileName": "producto.jpg", "caption": p["texto"], "delay": 900}, timeout=30)
            if cod in (200, 201):
                continue
        cod, r = _llamar("POST", f"/message/sendText/{_inst()}", {"number": _destino(jid), "text": p["texto"], "delay": 1100}, timeout=30)
        if cod not in (200, 201):
            log.warning("Evolution no envió el mensaje (%s): %s", cod, r)
        time.sleep(0.3)


def enviar(cliente, mensajes):
    """Manda por WhatsApp los mensajes de Kinti o del vendedor (en segundo plano, para no demorar la respuesta)."""
    if not (habilitado() and cliente.whatsapp_jid):
        return
    piezas = []
    for m in mensajes:
        if m.autor not in ("kinti", "vendedor"):
            continue
        p = {"texto": m.texto}
        if m.producto_id and m.producto.foto:
            p["imagen"] = f"{settings.SITIO_URL.rstrip('/')}/catalogo/{m.producto.foto}.jpg"
            p["texto"] = f"{m.texto}\n*{m.producto.nombre}* · S/ {m.producto.precio:,.0f}"
        piezas.append(p)
    if piezas:
        threading.Thread(target=_enviar_ya, args=(cliente.whatsapp_jid, piezas), daemon=True).start()


def leer_mensaje(data):
    """Extrae (jid, telefono, nombre, texto, id, de_mi) de un evento messages.upsert de Evolution."""
    key = data.get("key") or {}
    jid = key.get("remoteJid") or ""
    alt = key.get("remoteJidAlt") or key.get("senderPn") or data.get("senderPn") or ""
    tel = numero_de(jid if jid.endswith("@s.whatsapp.net") else alt) or numero_de(jid)
    msg = data.get("message") or {}
    texto = (msg.get("conversation") or (msg.get("extendedTextMessage") or {}).get("text")
             or (msg.get("imageMessage") or {}).get("caption") or (msg.get("videoMessage") or {}).get("caption") or "")
    tipo = data.get("messageType") or (next(iter(msg), "") if msg else "")
    return {"jid": jid, "telefono": tel, "nombre": (data.get("pushName") or "").strip(), "texto": texto.strip(),
            "id": key.get("id") or "", "de_mi": bool(key.get("fromMe")), "tipo": tipo}


def ignorar_jid(jid):
    return not jid or jid.endswith("@g.us") or jid.endswith("@broadcast") or jid.endswith("@newsletter") or jid == "status@broadcast"
