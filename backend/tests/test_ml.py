from ia.ml import entrenar


def test_regresion_no_lineal_supera_a_la_lineal():
    _, info, _ = entrenar.entrenar_regresion()
    m = info["modelos"]
    assert m["logaritmica"]["r2"] > m["lineal"]["r2"]
    assert m["logaritmica"]["r2"] >= 0.80


def test_regresion_logistica_discrimina():
    _, info, _ = entrenar.entrenar_clasificacion()
    assert info["metricas"]["auc_roc"] >= 0.70
    assert info["metricas"]["sensibilidad"] >= 0.60
    assert 0.12 <= info["datos"]["tasa_compra"] <= 0.20
