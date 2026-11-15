import json

import pytest

pytestmark = pytest.mark.django_db


def test_salud(client):
    r = client.get("/api/salud")
    assert r.status_code == 200
    assert r.json()["estado"] == "ok"


def test_calificar_cliente(client):
    caliente = {"minutos_respuesta": 1, "pidio_precio": True, "pidio_delivery": True, "mensajes": 9,
                "origen": "directo", "precio": 279}
    frio = {"minutos_respuesta": 720, "fuera_de_horario": True, "pidio_precio": False, "pidio_delivery": False,
            "mensajes": 1, "precio": 459}
    a = client.post("/api/ia/calificar", json.dumps(caliente), content_type="application/json").json()
    b = client.post("/api/ia/calificar", json.dumps(frio), content_type="application/json").json()
    assert 0 <= b["probabilidad_compra"] < a["probabilidad_compra"] <= 1


def test_ruta_y_asignacion(client):
    r = client.get("/api/busqueda/ruta", {"origen": "Ate", "destino": "Comas"}).json()
    assert r["a_estrella"]["camino"][0] == "Ate" and r["a_estrella"]["camino"][-1] == "Comas"
    h = client.get("/api/busqueda/asignar").json()
    assert h["costo_final"] < h["costo_inicial"]
    assert client.get("/api/busqueda/ruta", {"origen": "Marte"}).status_code == 400
