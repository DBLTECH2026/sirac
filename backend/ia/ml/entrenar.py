"""Entrena los primeros modelos de SIRAC con los datos simulados y guarda modelos y métricas.

Uso:  python -m ia.ml.entrenar                 (modelos + métricas)
      python -m ia.ml.entrenar --graficos DIR  (además, gráficos PNG y CSV para el informe)
"""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, mean_absolute_error, mean_squared_error,
                             precision_score, r2_score, recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, PolynomialFeatures, StandardScaler

from .datos import campanas, leads, preparar_leads

DIR_MODELOS = Path(__file__).resolve().parent.parent / "modelos"
SEMILLA = 42


def modelos_regresion():
    return {
        "lineal": Pipeline([("modelo", LinearRegression())]),
        "logaritmica": Pipeline([("log", FunctionTransformer(np.log)), ("modelo", LinearRegression())]),
        "polinomica_2": Pipeline([("poli", PolynomialFeatures(2, include_bias=False)), ("esc", StandardScaler()),
                                  ("modelo", LinearRegression())]),
    }


def entrenar_regresion():
    df = campanas()
    X, y = df[["inversion"]].values, df["conversaciones"].values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=SEMILLA)
    resultados, ajustados = {}, {}
    for nombre, m in modelos_regresion().items():
        m.fit(Xtr, ytr)
        p = m.predict(Xte)
        resultados[nombre] = {"r2": round(r2_score(yte, p), 4), "mae": round(mean_absolute_error(yte, p), 3),
                              "rmse": round(float(np.sqrt(mean_squared_error(yte, p))), 3)}
        ajustados[nombre] = m
    mejor = max(resultados, key=lambda k: resultados[k]["r2"])
    lin = ajustados["lineal"].named_steps["modelo"]
    loga = ajustados["logaritmica"].named_steps["modelo"]
    return ajustados, {"datos": {"dias": len(df), "entrenamiento": len(Xtr), "prueba": len(Xte)},
                       "modelos": resultados, "mejor": mejor,
                       "ecuaciones": {"lineal": f"conversaciones = {lin.intercept_:.2f} + {lin.coef_[0]:.4f}·inversión",
                                      "logaritmica": f"conversaciones = {loga.intercept_:.2f} + {loga.coef_[0]:.2f}·ln(inversión)"}}, df


def calificador():
    num = ["log_minutos", "mensajes", "precio"]
    binarias = ["fuera_de_horario", "pidio_precio", "pidio_delivery", "provincia"]
    pre = ColumnTransformer([("num", StandardScaler(), num), ("bin", "passthrough", binarias),
                             ("cat", OneHotEncoder(drop="first", categories=[["meta", "google", "organico", "directo"]]), ["origen"])])
    return Pipeline([("prep", pre), ("modelo", LogisticRegression(class_weight="balanced", max_iter=2000))])


def entrenar_clasificacion():
    df = leads()
    X, y = preparar_leads(df), df["compra"].values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=SEMILLA, stratify=y)
    m = calificador().fit(Xtr, ytr)
    prob = m.predict_proba(Xte)[:, 1]
    pred = (prob >= 0.5).astype(int)
    vn, fp, fn, vp = confusion_matrix(yte, pred).ravel()
    nombres = list(m.named_steps["prep"].get_feature_names_out())
    coefs = m.named_steps["modelo"].coef_[0]
    return m, {
        "datos": {"conversaciones": len(df), "tasa_compra": round(float(y.mean()), 4), "entrenamiento": len(Xtr), "prueba": len(Xte)},
        "metricas": {"exactitud": round(accuracy_score(yte, pred), 4), "precision": round(precision_score(yte, pred), 4),
                     "sensibilidad": round(recall_score(yte, pred), 4), "f1": round(f1_score(yte, pred), 4),
                     "auc_roc": round(roc_auc_score(yte, prob), 4),
                     "exactitud_linea_base": round(float(1 - yte.mean()), 4)},
        "matriz_confusion": {"vn": int(vn), "fp": int(fp), "fn": int(fn), "vp": int(vp)},
        "coeficientes": {n.split("__")[-1]: {"beta": round(float(c), 4), "odds_ratio": round(float(np.exp(c)), 3)}
                         for n, c in zip(nombres, coefs)},
    }, (yte, prob, df)


def graficos(directorio, reg_modelos, reg_info, df_camp, cls_info, roc_datos):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    d = Path(directorio)
    d.mkdir(parents=True, exist_ok=True)
    noche, verde, celeste, violeta, gris = "#0A1424", "#0EB155", "#16B6D8", "#7C5CFC", "#9FB3CC"
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})

    # 1. Regresión: inversión vs conversaciones
    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=160)
    ax.scatter(df_camp["inversion"], df_camp["conversaciones"], s=18, color=gris, label="Días simulados (180)")
    xs = np.linspace(df_camp["inversion"].min(), df_camp["inversion"].max(), 200).reshape(-1, 1)
    estilos = {"lineal": (celeste, "--", "Lineal"), "logaritmica": (verde, "-", "No lineal (logarítmica)"),
               "polinomica_2": (violeta, ":", "Polinómica de grado 2")}
    for nombre, (c, ls, etq) in estilos.items():
        r2 = reg_info["modelos"][nombre]["r2"]
        ax.plot(xs, reg_modelos[nombre].predict(xs), color=c, ls=ls, lw=2.4, label=f"{etq} · R² = {r2:.3f}")
    ax.set_xlabel("Inversión diaria en anuncios (S/)")
    ax.set_ylabel("Conversaciones de WhatsApp en el día")
    ax.set_title("Inversión en anuncios vs. conversaciones (datos simulados)", color=noche, fontsize=13, loc="left")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(d / "ml-regresion-inversion-conversaciones.png")
    plt.close(fig)

    # 2. Curva ROC de la regresión logística
    yte, prob, _ = roc_datos
    fpr, tpr, _ = roc_curve(yte, prob)
    fig, ax = plt.subplots(figsize=(6.4, 5.6), dpi=160)
    ax.plot(fpr, tpr, color=verde, lw=2.6, label=f"Regresión logística · AUC = {cls_info['metricas']['auc_roc']:.3f}")
    ax.plot([0, 1], [0, 1], color=gris, ls="--", label="Azar (AUC = 0.5)")
    ax.set_xlabel("Tasa de falsos positivos")
    ax.set_ylabel("Tasa de verdaderos positivos (sensibilidad)")
    ax.set_title("Curva ROC del calificador de clientes", color=noche, fontsize=13, loc="left")
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(d / "ml-curva-roc-logistica.png")
    plt.close(fig)

    # 3. Matriz de confusión
    mc = cls_info["matriz_confusion"]
    mat = np.array([[mc["vn"], mc["fp"]], [mc["fn"], mc["vp"]]])
    fig, ax = plt.subplots(figsize=(5.6, 4.8), dpi=160)
    ax.imshow(mat, cmap="Greens")
    for (i, j), v in np.ndenumerate(mat):
        ax.text(j, i, f"{v:,}", ha="center", va="center", fontsize=16, color=noche, fontweight="bold")
    ax.set_xticks([0, 1], ["Predice: no compra", "Predice: compra"])
    ax.set_yticks([0, 1], ["Real: no compró", "Real: compró"])
    ax.set_title("Matriz de confusión (prueba, umbral 0.5)", color=noche, fontsize=12, loc="left")
    fig.tight_layout()
    fig.savefig(d / "ml-matriz-confusion.png")
    plt.close(fig)

    # 4. Odds ratios
    co = cls_info["coeficientes"]
    etiquetas = {"log_minutos": "Minutos de espera (log)", "mensajes": "Mensajes del cliente", "precio": "Precio del producto",
                 "fuera_de_horario": "Llega fuera de horario", "pidio_precio": "Pidió el precio", "pidio_delivery": "Pidió delivery",
                 "provincia": "Es de provincia", "origen_google": "Viene de Google", "origen_organico": "Orgánico",
                 "origen_directo": "Directo (sin anuncio)"}
    orden = sorted(co, key=lambda k: co[k]["beta"])
    fig, ax = plt.subplots(figsize=(8.4, 5.2), dpi=160)
    vals = [co[k]["beta"] for k in orden]
    ax.barh([etiquetas.get(k, k) for k in orden], vals, color=[verde if v > 0 else "#E5484D" for v in vals])
    ax.axvline(0, color=noche, lw=1)
    ax.set_xlabel("Coeficiente β (positivo = sube la probabilidad de compra)")
    ax.set_title("Qué pesa en la probabilidad de compra", color=noche, fontsize=13, loc="left")
    fig.tight_layout()
    fig.savefig(d / "ml-coeficientes-logistica.png")
    plt.close(fig)

    campanas().to_csv(d / "datos-simulados-campanas.csv", index=False)
    roc_datos[2].to_csv(d / "datos-simulados-leads.csv", index=False)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--graficos", help="carpeta donde guardar gráficos PNG y CSV")
    args = ap.parse_args(argv)
    DIR_MODELOS.mkdir(parents=True, exist_ok=True)
    reg_modelos, reg_info, df_camp = entrenar_regresion()
    cls_modelo, cls_info, roc_datos = entrenar_clasificacion()
    joblib.dump(reg_modelos[reg_info["mejor"]], DIR_MODELOS / "proyeccion_conversaciones.joblib")
    joblib.dump(cls_modelo, DIR_MODELOS / "calificador_leads.joblib")
    metricas = {"regresion": reg_info, "clasificacion": cls_info,
                "nota": "Datos simulados de Kusi Hogar S.A.C. (caso hipotético); semilla fija para reproducibilidad."}
    (DIR_MODELOS / "metricas.json").write_text(json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.graficos:
        graficos(args.graficos, reg_modelos, reg_info, df_camp, cls_info, roc_datos)
    print(json.dumps({"regresion": reg_info["modelos"], "mejor": reg_info["mejor"], "clasificacion": cls_info["metricas"],
                      "tasa_compra": cls_info["datos"]["tasa_compra"]}, ensure_ascii=False, indent=1))
    return metricas


if __name__ == "__main__":
    main()
