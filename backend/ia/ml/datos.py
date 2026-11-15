"""Datos SIMULADOS de Kusi Hogar S.A.C. (caso hipotético del proyecto SIRAC).

No son datos reales de ninguna empresa: se generan con reglas explícitas y una semilla fija para que
cualquier persona pueda reproducir exactamente los mismos resultados.
"""
import numpy as np
import pandas as pd

CATALOGO = [
    ("Freidora de aire 5 L", "cocina", 279), ("Olla arrocera 1.8 L", "cocina", 129), ("Licuadora 1.5 L", "cocina", 189),
    ("Batidora de pedestal 5 L", "cocina", 399), ("Hervidor eléctrico 1.7 L", "cocina", 99),
    ("Batería de ollas 9 piezas", "menaje", 349), ("Sartén antiadherente 28 cm", "menaje", 79),
    ("Termo de acero 1 L", "menaje", 59), ("Aspiradora sin bolsa 2000 W", "hogar", 459), ("Ventilador de torre", "hogar", 219),
]
ORIGENES = ["meta", "google", "organico", "directo"]


def campanas(dias=180, semilla=2026):
    """Inversión diaria en anuncios (S/) y conversaciones de WhatsApp recibidas ese día.

    Regla de simulación: rendimientos decrecientes -> conversaciones = 30·ln(inversión) − 125 + 3·fin_de_semana + ruido.
    """
    rng = np.random.default_rng(semilla)
    inversion = rng.uniform(80, 420, dias).round(2)
    fin_de_semana = (np.arange(dias) % 7 >= 5).astype(int)
    conv = 30 * np.log(inversion) - 125 + 3 * fin_de_semana + rng.normal(0, 3.5, dias)
    return pd.DataFrame({"dia": np.arange(1, dias + 1), "inversion": inversion, "fin_de_semana": fin_de_semana,
                         "conversaciones": np.clip(conv, 0, None).round().astype(int)})


def leads(n=6800, semilla=2026):
    """Conversaciones (clientes potenciales) con el resultado final: compra = 1 o 0.

    Regla de simulación (modelo logístico verdadero): la probabilidad de compra sube si el cliente pide delivery,
    pregunta el precio o escribe más mensajes, y baja cuanto más tarda la primera respuesta.
    """
    rng = np.random.default_rng(semilla)
    fuera = rng.random(n) < 0.35
    minutos = np.where(fuera, rng.uniform(480, 900, n), rng.exponential(47, n)).round(1)
    origen = rng.choice(ORIGENES, n, p=[0.6, 0.2, 0.1, 0.1])
    pidio_precio = (rng.random(n) < 0.7).astype(int)
    pidio_delivery = (rng.random(n) < 0.45).astype(int)
    mensajes = rng.poisson(6, n) + 1
    provincia = (rng.random(n) < 0.2).astype(int)
    idx = rng.integers(0, len(CATALOGO), n)
    precio = np.array([CATALOGO[i][2] for i in idx])
    categoria = np.array([CATALOGO[i][1] for i in idx])
    logit = (-1.85 + 1.1 * pidio_delivery + 0.5 * pidio_precio + 0.07 * np.minimum(mensajes, 15)
             - 0.55 * np.log1p(minutos / 5) + 0.4 * (origen == "google") + 0.6 * (origen == "directo")
             + 0.2 * (origen == "organico") - 0.3 * provincia - 0.002 * (precio - 250))
    compra = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    return pd.DataFrame({"minutos_respuesta": minutos, "fuera_de_horario": fuera.astype(int), "origen": origen,
                         "pidio_precio": pidio_precio, "pidio_delivery": pidio_delivery, "mensajes": mensajes,
                         "provincia": provincia, "categoria": categoria, "precio": precio, "compra": compra})


COLUMNAS_LEAD = ["log_minutos", "mensajes", "precio", "fuera_de_horario", "pidio_precio", "pidio_delivery", "provincia", "origen"]


def preparar_leads(df):
    """Ingeniería de variables compartida por el entrenamiento y la API."""
    out = df.copy()
    out["log_minutos"] = np.log1p(out["minutos_respuesta"].astype(float))
    return out[COLUMNAS_LEAD]
