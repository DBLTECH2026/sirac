"""Webhook de Evolution API: filtro de palabra clave, respuesta de Kinti, eco y envío por WhatsApp."""
import json
from decimal import Decimal

import pytest

from crm import demo, evolution
from crm.models import Cliente, Producto

pytestmark = pytest.mark.django_db
TOKEN = "token-webhook-prueba"


@pytest.fixture
def base(settings, monkeypatch):
    settings.EVOLUTION_URL = "http://evolution:8080"
    settings.EVOLUTION_API_KEY = "clave"
    settings.EVOLUTION_WEBHOOK_TOKEN = TOKEN
    demo._usuarios("clave-de-prueba-123", conservar=False)
    for nombre, cat, det, precio, stock, gar, foto, palabras, top, _ in demo.PRODUCTOS:
        Producto.objects.create(nombre=nombre, categoria=cat, detalle=det, precio=Decimal(precio), stock=stock,
                                garantia_meses=gar, foto=foto, palabras=palabras, mas_vendido=top)
    enviados = []
    monkeypatch.setattr(evolution, "_enviar_ya", lambda jid, piezas: enviados.append((jid, piezas)))
    monkeypatch.setattr(evolution.threading, "Thread", lambda target, args, daemon: type("T", (), {"start": lambda s: target(*args)})())
    return enviados


def evento(texto, de_mi=False, id_="ABC1", jid="51987654321@s.whatsapp.net"):
    return json.dumps({"event": "messages.upsert", "instance": "sirac", "data": {
        "key": {"remoteJid": jid, "fromMe": de_mi, "id": id_}, "pushName": "Luis Prueba",
        "message": {"conversation": texto}, "messageType": "conversation"}})


def test_webhook_exige_token(client, base):
    assert client.post("/api/wa/evolution?token=malo", evento("Hola Kusi"), content_type="application/json").status_code == 403


def test_filtro_ignora_chats_personales(client, base):
    r = client.post(f"/api/wa/evolution?token={TOKEN}", evento("Hola, ¿cómo estás?"), content_type="application/json").json()
    assert r.get("ignorado") and not Cliente.objects.exists() and base == []


def test_kinti_responde_por_whatsapp_y_no_duplica(client, base):
    url = f"/api/wa/evolution?token={TOKEN}"
    client.post(url, evento("Hola Kusi, ¿cuánto está la freidora de aire?"), content_type="application/json")
    c = Cliente.objects.get(whatsapp_jid="51987654321@s.whatsapp.net")
    assert c.nombre == "Luis Prueba" and c.telefono == "+51987654321"
    jid, piezas = base[0]
    assert jid == c.whatsapp_jid and any("S/ 279" in p["texto"] for p in piezas)
    assert any(p.get("imagen", "").endswith("/catalogo/freidora-aire.jpg") for p in piezas)
    # Evolution reenvía el mismo evento: no se duplica
    client.post(url, evento("Hola Kusi, ¿cuánto está la freidora de aire?"), content_type="application/json")
    assert c.mensajes.filter(autor="cliente").count() == 1
    # Eco de lo que mandó Kinti (fromMe) no se guarda; un mensaje escrito en el celular pausa a Kinti
    eco = c.mensajes.filter(autor="kinti").first().texto
    client.post(url, evento(eco, de_mi=True, id_="ECO1"), content_type="application/json")
    client.post(url, evento("Hola, te llamo en 5 minutos", de_mi=True, id_="CEL1"), content_type="application/json")
    c.refresh_from_db()
    assert c.mensajes.filter(autor="vendedor").count() == 1 and c.kinti_activo is False
