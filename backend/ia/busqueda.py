"""Algoritmos de búsqueda de SIRAC (Fase 3.2 del proyecto).

1. Flujo de conversación de Kinti  -> búsqueda no informada (BFS y DFS).
2. Rutas de delivery en Lima       -> búsqueda informada A* (heurística: distancia en línea recta).
3. Reparto de clientes potenciales -> búsqueda local Hill climbing.
"""
from collections import deque
import heapq
import math
import random

# ---------------------------------------------------------------- 1. Conversación (BFS / DFS)
# Estados de la conversación y acciones posibles de Kinti: estado -> [(acción, estado siguiente)]
FLUJO = {
    "inicio": [("saludar", "saludo")],
    "saludo": [("preguntar qué busca", "consulta_general"), ("reconocer el producto del anuncio", "producto_identificado")],
    "consulta_general": [("enviar catálogo", "catalogo_enviado"), ("identificar el producto", "producto_identificado")],
    "catalogo_enviado": [("identificar el producto", "producto_identificado")],
    "producto_identificado": [("verificar stock", "stock_verificado"), ("informar precio", "precio_informado")],
    "stock_verificado": [("informar precio", "precio_informado")],
    "precio_informado": [("cotizar delivery", "delivery_cotizado"), ("atender objeción de precio", "objecion_precio")],
    "objecion_precio": [("ofrecer promoción", "precio_informado"), ("cerrar sin venta", "perdido")],
    "delivery_cotizado": [("pedir datos de envío", "datos_cliente")],
    "datos_cliente": [("confirmar pedido y derivar al vendedor", "listo_para_pagar")],
    "perdido": [],
    "listo_para_pagar": [],
}
INICIO_CONV, OBJETIVO_CONV = "inicio", "listo_para_pagar"


def _reconstruir(padres, objetivo):
    camino, acciones, nodo = [objetivo], [], objetivo
    while padres[nodo] is not None:
        previo, accion = padres[nodo]
        acciones.append(accion)
        camino.append(previo)
        nodo = previo
    return camino[::-1], acciones[::-1]


def bfs(grafo=FLUJO, inicio=INICIO_CONV, objetivo=OBJETIVO_CONV):
    """Búsqueda en anchura: encuentra el camino con menos acciones."""
    frontera, padres, orden = deque([inicio]), {inicio: None}, []
    while frontera:
        nodo = frontera.popleft()
        orden.append(nodo)
        if nodo == objetivo:
            camino, acciones = _reconstruir(padres, objetivo)
            return {"algoritmo": "BFS", "camino": camino, "acciones": acciones, "pasos": len(acciones),
                    "expandidos": len(orden), "orden": orden}
        for accion, sig in grafo[nodo]:
            if sig not in padres:
                padres[sig] = (nodo, accion)
                frontera.append(sig)
    return None


def dfs(grafo=FLUJO, inicio=INICIO_CONV, objetivo=OBJETIVO_CONV):
    """Búsqueda en profundidad: llega a una solución, no necesariamente la más corta."""
    pila, padres, visitados, orden = [inicio], {inicio: None}, set(), []
    while pila:
        nodo = pila.pop()
        if nodo in visitados:
            continue
        visitados.add(nodo)
        orden.append(nodo)
        if nodo == objetivo:
            camino, acciones = _reconstruir(padres, objetivo)
            return {"algoritmo": "DFS", "camino": camino, "acciones": acciones, "pasos": len(acciones),
                    "expandidos": len(orden), "orden": orden}
        for accion, sig in reversed(grafo[nodo]):
            if sig not in visitados:
                padres[sig] = (nodo, accion)
                pila.append(sig)
    return None


# ---------------------------------------------------------------- 2. Rutas de delivery en Lima (A*)
# Coordenadas aproximadas del centro de cada distrito (elaboración propia con mapas públicos).
DISTRITOS = {
    "Ate": (-12.026, -76.919), "Santa Anita": (-12.044, -76.971), "El Agustino": (-12.043, -76.996),
    "La Molina": (-12.087, -76.936), "San Luis": (-12.074, -76.996), "La Victoria": (-12.066, -77.016),
    "Cercado de Lima": (-12.050, -77.025), "Rímac": (-12.026, -77.030), "Breña": (-12.060, -77.051),
    "Jesús María": (-12.075, -77.047), "Lince": (-12.084, -77.034), "San Isidro": (-12.098, -77.036),
    "San Borja": (-12.101, -76.999), "Surquillo": (-12.114, -77.012), "Miraflores": (-12.120, -77.030),
    "Santiago de Surco": (-12.144, -76.991), "Barranco": (-12.149, -77.021), "Chorrillos": (-12.169, -77.016),
    "San Juan de Miraflores": (-12.160, -76.970), "Villa El Salvador": (-12.212, -76.937),
    "San Juan de Lurigancho": (-11.985, -77.005), "Independencia": (-11.990, -77.049),
    "Los Olivos": (-11.970, -77.072), "Comas": (-11.940, -77.057), "San Martín de Porres": (-12.025, -77.083),
    "Callao": (-12.056, -77.118),
}
CONEXIONES = [
    ("Ate", "Santa Anita"), ("Ate", "La Molina"), ("Ate", "San Juan de Lurigancho"), ("Santa Anita", "El Agustino"),
    ("Santa Anita", "San Luis"), ("Santa Anita", "La Molina"), ("El Agustino", "San Luis"), ("El Agustino", "Cercado de Lima"),
    ("El Agustino", "San Juan de Lurigancho"), ("El Agustino", "La Victoria"), ("San Luis", "La Victoria"),
    ("San Luis", "San Borja"), ("La Molina", "San Borja"), ("La Molina", "Santiago de Surco"),
    ("La Victoria", "Cercado de Lima"), ("La Victoria", "Lince"), ("La Victoria", "San Borja"), ("Cercado de Lima", "Rímac"),
    ("Cercado de Lima", "Breña"), ("Cercado de Lima", "Jesús María"), ("Rímac", "San Juan de Lurigancho"),
    ("Rímac", "Independencia"), ("Rímac", "San Martín de Porres"), ("Breña", "Jesús María"),
    ("Breña", "San Martín de Porres"), ("Jesús María", "Lince"), ("Lince", "San Isidro"), ("San Isidro", "Miraflores"),
    ("San Isidro", "Surquillo"), ("San Isidro", "San Borja"), ("San Borja", "Surquillo"), ("San Borja", "Santiago de Surco"),
    ("Surquillo", "Miraflores"), ("Surquillo", "Santiago de Surco"), ("Miraflores", "Barranco"), ("Barranco", "Chorrillos"),
    ("Barranco", "Santiago de Surco"), ("Santiago de Surco", "Chorrillos"), ("Santiago de Surco", "San Juan de Miraflores"),
    ("Chorrillos", "San Juan de Miraflores"), ("San Juan de Miraflores", "Villa El Salvador"),
    ("Independencia", "Los Olivos"), ("Independencia", "Comas"), ("Independencia", "San Martín de Porres"),
    ("Los Olivos", "Comas"), ("Los Olivos", "San Martín de Porres"), ("San Martín de Porres", "Callao"),
    ("Breña", "Callao"), ("San Juan de Lurigancho", "Independencia"),
]
FACTOR_VIA = 1.35  # las pistas son más largas que la línea recta; así la heurística nunca sobreestima


def haversine(a, b):
    (la1, lo1), (la2, lo2) = DISTRITOS[a], DISTRITOS[b]
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def grafo_lima():
    g = {d: [] for d in DISTRITOS}
    for a, b in CONEXIONES:
        km = round(haversine(a, b) * FACTOR_VIA, 2)
        g[a].append((b, km))
        g[b].append((a, km))
    return g


def _km_camino(g, camino):
    return round(sum(next(k for v, k in g[a] if v == b) for a, b in zip(camino, camino[1:])), 2)


def a_estrella(origen, destino, usar_heuristica=True):
    """A* con h(n) = distancia en línea recta al destino. Sin heurística equivale a costo uniforme (Dijkstra)."""
    g = grafo_lima()
    h = (lambda n: haversine(n, destino)) if usar_heuristica else (lambda n: 0.0)
    frontera = [(h(origen), 0.0, origen)]
    costo, padres, cerrados, orden = {origen: 0.0}, {origen: None}, set(), []
    while frontera:
        _, gcost, nodo = heapq.heappop(frontera)
        if nodo in cerrados:
            continue
        cerrados.add(nodo)
        orden.append(nodo)
        if nodo == destino:
            camino = [destino]
            while padres[camino[-1]] is not None:
                camino.append(padres[camino[-1]])
            camino = camino[::-1]
            return {"algoritmo": "A*" if usar_heuristica else "Costo uniforme", "camino": camino,
                    "km": _km_camino(g, camino), "expandidos": len(orden), "orden": orden}
        for vecino, km in g[nodo]:
            nuevo = gcost + km
            if nuevo < costo.get(vecino, float("inf")):
                costo[vecino], padres[vecino] = nuevo, nodo
                heapq.heappush(frontera, (nuevo + h(vecino), nuevo, vecino))
    return None


def bfs_ruta(origen, destino):
    """BFS sobre el mapa: minimiza la cantidad de distritos recorridos, no los kilómetros."""
    g = grafo_lima()
    frontera, padres, orden = deque([origen]), {origen: None}, []
    while frontera:
        nodo = frontera.popleft()
        orden.append(nodo)
        if nodo == destino:
            camino = [destino]
            while padres[camino[-1]] is not None:
                camino.append(padres[camino[-1]])
            camino = camino[::-1]
            return {"algoritmo": "BFS", "camino": camino, "km": _km_camino(g, camino), "expandidos": len(orden), "orden": orden}
        for vecino, _ in g[nodo]:
            if vecino not in padres:
                padres[vecino] = nodo
                frontera.append(vecino)
    return None


# ---------------------------------------------------------------- 3. Reparto de clientes (Hill climbing)
VENDEDORES = [
    {"nombre": "Diego", "zona": "Lima", "especialidad": "cocina", "carga": 6, "capacidad": 12},
    {"nombre": "Milagros", "zona": "Lima", "especialidad": "hogar", "carga": 4, "capacidad": 12},
    {"nombre": "Kevin", "zona": "Provincia", "especialidad": "menaje", "carga": 3, "capacidad": 10},
]
MIN_POR_CLIENTE = 4  # minutos de espera que suma cada cliente en la cola de un vendedor


def leads_demo(n=14, semilla=7):
    rnd = random.Random(semilla)
    cats = ["cocina", "menaje", "hogar"]
    return [{"id": i + 1, "zona": "Provincia" if rnd.random() < 0.25 else "Lima", "categoria": rnd.choice(cats),
             "urgencia": rnd.choice([1, 1, 2, 2, 3])} for i in range(n)]


def costo_asignacion(asig, leads, vendedores=VENDEDORES):
    """Costo a minimizar: espera ponderada por urgencia + penalidades por zona/especialidad + exceso de capacidad."""
    carga = [v["carga"] for v in vendedores]
    total = 0.0
    for lead, iv in zip(leads, asig):
        carga[iv] += 1
        v = vendedores[iv]
        total += lead["urgencia"] * carga[iv] * MIN_POR_CLIENTE / 10
        total += 8 if lead["zona"] != v["zona"] else 0
        total += 3 if lead["categoria"] != v["especialidad"] else 0
    for v, c in zip(vendedores, carga):
        total += 10 * max(0, c - v["capacidad"])
    return round(total, 2)


def hill_climbing(leads, vendedores=VENDEDORES, reinicios=5, semilla=1):
    """Ascenso de colina por máxima pendiente con reinicios aleatorios. Vecino = mover un cliente a otro vendedor."""
    rnd = random.Random(semilla)
    n, k = len(leads), len(vendedores)
    inicial = [i % k for i in range(n)]  # estado inicial: reparto por turnos (round robin)
    costo_inicial = costo_asignacion(inicial, leads, vendedores)
    mejor, mejor_costo, iteraciones, historial = inicial, costo_inicial, 0, []
    for r in range(reinicios + 1):
        actual = inicial[:] if r == 0 else [rnd.randrange(k) for _ in range(n)]
        c_actual = costo_asignacion(actual, leads, vendedores)
        while True:
            vecino_mejor, c_vecino_mejor = None, c_actual
            for i in range(n):
                for j in range(k):
                    if j == actual[i]:
                        continue
                    cand = actual[:]
                    cand[i] = j
                    c = costo_asignacion(cand, leads, vendedores)
                    if c < c_vecino_mejor:
                        vecino_mejor, c_vecino_mejor = cand, c
            if vecino_mejor is None:
                break  # óptimo local: ningún vecino mejora
            actual, c_actual = vecino_mejor, c_vecino_mejor
            iteraciones += 1
            if r == 0:
                historial.append(c_actual)
        if c_actual < mejor_costo:
            mejor, mejor_costo = actual, c_actual
    return {"algoritmo": "Hill climbing", "costo_inicial": costo_inicial, "costo_final": mejor_costo,
            "mejora_pct": round(100 * (costo_inicial - mejor_costo) / costo_inicial, 1), "iteraciones": iteraciones,
            "historial_primer_ascenso": [costo_inicial] + historial,
            "asignacion": [{"lead": l["id"], "zona": l["zona"], "categoria": l["categoria"], "urgencia": l["urgencia"],
                            "vendedor": vendedores[iv]["nombre"], "vendedor_inicial": vendedores[inicial[idx]]["nombre"]}
                           for idx, (l, iv) in enumerate(zip(leads, mejor))]}
