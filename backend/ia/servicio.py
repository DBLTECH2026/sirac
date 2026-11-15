"""Carga perezosa de los modelos entrenados. Si no existen (primer arranque), los entrena."""
import json
from functools import lru_cache

import joblib
import pandas as pd

from .ml import entrenar
from .ml.datos import preparar_leads


@lru_cache(maxsize=1)
def modelos():
    d = entrenar.DIR_MODELOS
    if not (d / "calificador_leads.joblib").exists():
        entrenar.main([])
    return {"calificador": joblib.load(d / "calificador_leads.joblib"),
            "proyeccion": joblib.load(d / "proyeccion_conversaciones.joblib"),
            "metricas": json.loads((d / "metricas.json").read_text(encoding="utf-8"))}


def calificar(datos):
    origen = datos.get("origen", "meta")
    fila = pd.DataFrame([{
        "minutos_respuesta": float(datos.get("minutos_respuesta", 5)),
        "fuera_de_horario": int(bool(datos.get("fuera_de_horario", False))),
        "origen": origen if origen in ("meta", "google", "organico", "directo") else "meta",
        "pidio_precio": int(bool(datos.get("pidio_precio", False))),
        "pidio_delivery": int(bool(datos.get("pidio_delivery", False))),
        "mensajes": int(datos.get("mensajes", 3)),
        "provincia": int(bool(datos.get("provincia", False))),
        "precio": float(datos.get("precio", 279)),
    }])
    p = float(modelos()["calificador"].predict_proba(preparar_leads(fila))[0, 1])
    etiqueta = "caliente" if p >= 0.6 else "tibio" if p >= 0.4 else "frío"
    recomendacion = {"caliente": "Derivar ya a un vendedor",
                     "tibio": "Kinti sigue la conversación y ofrece delivery",
                     "frío": "Kinti responde y deja un recordatorio"}[etiqueta]
    return {"probabilidad_compra": round(p, 4), "etiqueta": etiqueta, "recomendacion": recomendacion}


def proyectar(inversion_diaria):
    inv = max(50.0, min(float(inversion_diaria), 600.0))
    dia = float(modelos()["proyeccion"].predict([[inv]])[0])
    return {"inversion_diaria": inv, "conversaciones_dia": round(dia, 1), "conversaciones_mes": round(dia * 30),
            "modelo": modelos()["metricas"]["regresion"]["mejor"]}
