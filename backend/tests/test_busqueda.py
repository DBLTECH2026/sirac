from ia import busqueda as b


def test_bfs_encuentra_la_conversacion_mas_corta():
    r = b.bfs()
    assert r["camino"][0] == "inicio" and r["camino"][-1] == "listo_para_pagar"
    assert r["pasos"] == 6


def test_dfs_llega_al_objetivo_pero_no_siempre_por_el_camino_corto():
    r = b.dfs()
    assert r["camino"][-1] == "listo_para_pagar"
    assert r["pasos"] >= b.bfs()["pasos"]


def test_heuristica_admisible():
    g = b.grafo_lima()
    for a, vecinos in g.items():
        for v, km in vecinos:
            assert b.haversine(a, v) <= km  # la línea recta nunca supera el costo real del tramo


def test_a_estrella_es_optimo_y_expande_menos():
    for o, d in [("Ate", "Comas"), ("Ate", "Chorrillos"), ("Callao", "Villa El Salvador")]:
        a, u = b.a_estrella(o, d), b.a_estrella(o, d, usar_heuristica=False)
        assert a["km"] == u["km"]
        assert a["expandidos"] <= u["expandidos"]


def test_hill_climbing_mejora_el_reparto_por_turnos():
    r = b.hill_climbing(b.leads_demo())
    assert r["costo_final"] < r["costo_inicial"]
    h = r["historial_primer_ascenso"]
    assert all(x > y for x, y in zip(h, h[1:]))  # cada paso mejora estrictamente
