"""Pruebas del CRM: sesión por roles, Kinti (IA), embudo, entrenamiento y simulador de WhatsApp."""
import json
from decimal import Decimal

import pytest

from crm import demo, kinti
from crm.models import Cliente, Producto, RespuestaKinti

pytestmark = pytest.mark.django_db
CLAVE = "clave-de-prueba-123"


@pytest.fixture
def base(settings):
    settings.CRM_CLAVE_DEMO = CLAVE
    demo._usuarios(CLAVE, conservar=False)
    for nombre, cat, det, precio, stock, gar, foto, palabras, top, _ in demo.PRODUCTOS:
        Producto.objects.create(nombre=nombre, categoria=cat, detalle=det, precio=Decimal(precio), stock=stock,
                                garantia_meses=gar, foto=foto, palabras=palabras, mas_vendido=top)
    for tema, palabras, resp in demo.RESPUESTAS:
        RespuestaKinti.objects.create(tema=tema, palabras=palabras, respuesta=resp)


def entrar(client, correo):
    r = client.post("/api/crm/login", json.dumps({"correo": correo, "clave": CLAVE}), content_type="application/json")
    assert r.status_code == 200
    return {"HTTP_AUTHORIZATION": "Bearer " + r.json()["token"]}


def test_login_y_roles(client, base):
    assert client.get("/api/crm/yo").status_code == 401
    malo = client.post("/api/crm/login", json.dumps({"correo": "carla@kusihogar.pe", "clave": "x"}), content_type="application/json")
    assert malo.status_code == 401
    admin = entrar(client, "carla@kusihogar.pe")
    assert client.get("/api/crm/yo", **admin).json()["usuario"]["rol"] == "admin"
    ventas = entrar(client, "diego@kusihogar.pe")
    assert client.get("/api/crm/usuarios", **ventas).status_code == 403
    assert client.get("/api/crm/usuarios", **admin).status_code == 200


def test_kinti_cotiza_con_a_estrella_y_califica(base):
    c = Cliente.objects.create(nombre="Rosa Huamaní", origen="meta")
    kinti.recibir(c, "Hola, ¿cuánto está la freidora de aire?")
    kinti.recibir(c, "¿Llega a Comas?")
    c.refresh_from_db()
    textos = " ".join(c.mensajes.filter(autor="kinti").values_list("texto", flat=True))
    assert "S/ 279" in textos and "Comas" in textos
    assert c.estado_conv == "delivery_cotizado"
    assert c.delivery == kinti.cotizar_delivery("Comas")["costo"]
    assert c.monto == Decimal("279") + c.delivery
    assert c.probabilidad is not None and c.probabilidad >= kinti.UMBRAL_CALIFICADO
    assert c.etapa == "calificado" and c.vendedor is not None


def test_kinti_deriva_cuando_quiere_pagar(base):
    c = Cliente.objects.create(nombre="Gaby Torres", origen="meta")
    kinti.recibir(c, "Quiero la olla arrocera, estoy en Los Olivos. Quiero pagar hoy")
    c.refresh_from_db()
    assert c.kinti_activo is False
    assert c.estado_conv == "listo_para_pagar"
    assert c.vendedor and c.vendedor.perfil.rol == "ventas"
    assert c.eventos.filter(tipo="derivado").exists()


def test_ventas_solo_ve_sus_clientes_y_mueve_el_embudo(client, base):
    diego = entrar(client, "diego@kusihogar.pe")
    propio = client.post("/api/crm/clientes", json.dumps({"nombre": "Cliente propio", "producto_id": Producto.objects.first().id,
                                                          "distrito": "Miraflores"}), content_type="application/json", **diego).json()
    Cliente.objects.create(nombre="De otro", origen="meta")
    lista = client.get("/api/crm/clientes", **diego).json()["clientes"]
    assert [x["nombre"] for x in lista] == ["Cliente propio"]
    r = client.patch(f"/api/crm/clientes/{propio['id']}", json.dumps({"etapa": "ganado"}), content_type="application/json", **diego).json()
    assert r["etapa"] == "ganado" and r["cerrado"]
    otro = Cliente.objects.get(nombre="De otro")
    assert client.get(f"/api/crm/clientes/{otro.id}", **diego).status_code == 404


def test_reparto_hill_climbing_y_tablero(client, base):
    for n in ("A", "B", "C"):
        Cliente.objects.create(nombre=n, origen="meta")
    admin = entrar(client, "carla@kusihogar.pe")
    r = client.post("/api/crm/reasignar", "{}", content_type="application/json", **admin).json()
    assert r["asignados"] == 3 and r["costo_final"] <= r["costo_inicial"]
    t = client.get("/api/crm/tablero", {"periodo": "7d"}, **admin).json()
    assert t["actual"]["chats"] == 3 and len(t["serie"]) == 14


def test_entrenamiento_y_simulador_whatsapp(client, base):
    jorge = entrar(client, "jorge@kusihogar.pe")
    nueva = {"tema": "Instalación", "palabras": "instalan,instalacion", "respuesta": "La instalación es gratis en Lima."}
    assert client.post("/api/crm/entrenamiento", json.dumps(nueva), content_type="application/json", **jorge).status_code == 201
    p = client.post("/api/crm/entrenamiento/probar", json.dumps({"texto": "¿Lo instalan?"}), content_type="application/json", **jorge).json()
    assert "La instalación es gratis en Lima." in p["respuestas"]

    s = client.post("/api/wa/iniciar", json.dumps({"nombre": "valeria ríos"}), content_type="application/json").json()
    h = {"HTTP_X_SESION": s["sesion"]}
    assert client.post("/api/wa/mensajes", json.dumps({"texto": "Hola, ¿cuánto está la licuadora?"}), content_type="application/json", **h).status_code == 201
    ms = client.get("/api/wa/mensajes", **h).json()["mensajes"]
    assert ms[0]["autor"] == "cliente" and any("S/ 189" in m["texto"] for m in ms if m["autor"] == "kinti")
    assert client.get("/api/wa/mensajes", HTTP_X_SESION="falsa").status_code == 401
