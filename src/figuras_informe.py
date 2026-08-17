"""
figuras_informe.py — Genera las imágenes estáticas que se insertan en INFORME.md
================================================================================

Los notebooks usan Plotly (interactivo, para análisis). El informe ejecutivo se lee
en GitHub o impreso, así que necesita imágenes estáticas: se regeneran aquí con
matplotlib, a partir de los mismos datos y el mismo modelo.

Uso, desde la raíz del repositorio:
    python src/figuras_informe.py
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import lightgbm as lgb
import shap
from sklearn.isotonic import IsotonicRegression

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from prepare import preparar_datos

# --- Estilo corporativo ----------------------------------------------------
AZUL, AZUL_MED, AZUL_CLARO = "#0E162A", "#2E536D", "#A9BDDF"
ACENTO, PETROLEO, ALERTA, OK = "#CE894D", "#062C33", "#C00000", "#2E7D32"
plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linestyle": "--",
    "figure.facecolor": "white", "savefig.bbox": "tight",
})

SALIDA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "reports", "figuras")
os.makedirs(SALIDA, exist_ok=True)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
train_raw = pd.read_csv(os.path.join(RAIZ, "data", "train.csv"))
test_raw = pd.read_csv(os.path.join(RAIZ, "data", "test.csv"))
train, test, _ = preparar_datos(train_raw, test_raw)
train["fecha"] = pd.to_datetime(train["fecha_solicitud"])
test["fecha"] = pd.to_datetime(test["fecha_solicitud"])

TARGET = "default_12m"
CAT = ["tipo_empleo", "region", "canal", "dia_semana_solicitud"]
EXCLUIR = ["id_solicitud", "fecha_solicitud", "fecha", TARGET,
           "num_contactos_ult_trimestre", "tasa_interes_anual"]
FEATS = [c for c in train.columns if c not in EXCLUIR]
MONOTONIA = {"score_buro": -1, "antiguedad_cliente_meses": -1, "peor_morosidad_12m": 1,
             "uso_linea_credito_pct": 1, "num_consultas_buro_3m": 1,
             "num_creditos_vigentes": 1, "ratio_deuda_ingreso": 1}
HP = dict(num_leaves=31, min_child_samples=60, learning_rate=0.03,
          reg_lambda=5.0, colsample_bytree=0.7)
FOLDS = [("2024-08-01", "2024-10-01"), ("2024-10-01", "2024-12-01"),
         ("2024-12-01", "2025-02-01"), ("2025-02-01", "2025-03-01")]

# Nombres legibles para un lector no técnico
LEGIBLE = {
    "score_buro": "Score de buró",
    "uso_linea_credito_pct": "Uso de la línea de crédito",
    "peor_morosidad_12m": "Peor mora del último año",
    "num_consultas_buro_3m": "Consultas al buró (3 meses)",
    "ratio_deuda_ingreso": "Deuda sobre ingreso",
    "monto_solicitado": "Monto solicitado",
    "antiguedad_laboral_meses": "Antigüedad laboral",
    "antiguedad_cliente_meses": "Antigüedad como cliente",
    "num_creditos_vigentes": "Créditos vigentes",
    "plazo_meses": "Plazo", "edad": "Edad", "canal": "Canal de originación",
    "ingreso_declarado": "Ingreso declarado", "deuda_sistema": "Deuda en el sistema",
    "region": "Región", "tipo_empleo": "Tipo de empleo",
    "dia_semana_solicitud": "Día de la semana",
}
nombre = lambda c: LEGIBLE.get(c, c.replace("_", " "))


def X(df):
    M = df[FEATS].copy()
    for c in CAT:
        if c in M.columns:
            M[c] = M[c].astype("category")
    return M


def particiones(df):
    for ini, fin in FOLDS:
        yield df[df.fecha < ini], df[(df.fecha >= ini) & (df.fecha < fin)]


def nuevo_modelo(n=500):
    return lgb.LGBMClassifier(n_estimators=n, verbose=-1, random_state=42,
                              monotone_constraints=[MONOTONIA.get(c, 0) for c in FEATS], **HP)


# ===========================================================================
# FIGURA 1 · El problema: la mora viene subiendo
# ===========================================================================
mens = train.groupby(train.fecha.dt.to_period("M"))[TARGET].agg(["size", "mean"])
z = np.polyfit(np.arange(len(mens)), mens["mean"].values, 1)
proy = np.polyval(z, np.arange(len(mens), len(mens) + 4))
etiq = [str(p) for p in mens.index]
etiq_test = ["2025-03", "2025-04", "2025-05", "2025-06"]

fig, ax = plt.subplots(figsize=(9, 3.6))
ax.plot(etiq, mens["mean"] * 100, "o-", color=AZUL, lw=2.5, ms=6, label="Mora observada")
ax.plot(etiq_test, proy * 100, "--", color=ACENTO, lw=2, label="Proyección (período a evaluar)")
ax.axhline(train[TARGET].mean() * 100, ls=":", color=PETROLEO, lw=1.5)
ax.text(0.15, 9.15, f"Promedio histórico: {train[TARGET].mean():.1%}",
        color=PETROLEO, fontsize=9)
ax.annotate("+88% en 13 meses", xy=(12, 13.3), xytext=(6.8, 14.9), color=ALERTA, fontsize=10,
            fontweight="bold", arrowprops=dict(arrowstyle="->", color=ALERTA))
ax.set_ylabel("Tasa de mora (%)")
ax.set_title("La mora se duplicó en trece meses y la tendencia sigue", fontweight="bold", loc="left")
ax.tick_params(axis="x", rotation=45)
ax.legend(frameon=False, loc="upper left")
fig.savefig(f"{SALIDA}/01_deterioro.png")
plt.close(fig)
print("✓ 01_deterioro.png")

# ===========================================================================
# FIGURA 2 · El dato contaminado
# ===========================================================================
g = train_raw.groupby("num_contactos_ult_trimestre")[TARGET].agg(["size", "mean"])
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.6))
ax1.plot(g.index, g["mean"] * 100, "o-", color=ALERTA, lw=2.5, ms=7)
ax1.axhline(train_raw[TARGET].mean() * 100, ls=":", color=AZUL, lw=1.5)
ax1.annotate("100% de mora\nsin excepción", xy=(9, 100), xytext=(4.3, 72),
             color=ALERTA, fontsize=9, arrowprops=dict(arrowstyle="->", color=ALERTA))
ax1.set(xlabel="N° de contactos registrados", ylabel="Tasa de mora (%)", ylim=(-5, 115))
ax1.set_title("Un campo que 'predice' demasiado bien", fontweight="bold", loc="left", fontsize=10)

a = train_raw["num_contactos_ult_trimestre"].value_counts(normalize=True).sort_index()
b = test_raw["num_contactos_ult_trimestre"].value_counts(normalize=True).sort_index()
idx = sorted(set(a.index) | set(b.index))
w = 0.4
ax2.bar([i - w/2 for i in idx], [a.get(i, 0) * 100 for i in idx], w, color=AZUL, label="Histórico")
ax2.bar([i + w/2 for i in idx], [b.get(i, 0) * 100 for i in idx], w, color=ACENTO, label="A evaluar")
ax2.axvspan(6.5, 12.5, color=ALERTA, alpha=0.10)
ax2.annotate("no existe en\nlas solicitudes nuevas", xy=(9, 3), xytext=(6.0, 22),
             color=ALERTA, fontsize=8.5, arrowprops=dict(arrowstyle="->", color=ALERTA))
ax2.set(xlabel="N° de contactos registrados", ylabel="% de solicitudes")
ax2.set_title("...y que no está disponible al decidir", fontweight="bold", loc="left", fontsize=10)
ax2.legend(frameon=False)
fig.tight_layout()
fig.savefig(f"{SALIDA}/02_dato_contaminado.png")
plt.close(fig)
print("✓ 02_dato_contaminado.png")

# ===========================================================================
# Modelo para las figuras de explicabilidad
# ===========================================================================
tr_f, va_f = list(particiones(train))[-1]
modelo = nuevo_modelo().fit(X(tr_f), tr_f[TARGET],
                            eval_set=[(X(va_f), va_f[TARGET])], eval_metric="auc",
                            callbacks=[lgb.early_stopping(50, verbose=False)])

# ===========================================================================
# FIGURA 3 · Qué mira el modelo + coherencia con el negocio
# ===========================================================================
imp = pd.Series(modelo.booster_.feature_importance("gain"), index=FEATS)
imp = (imp / imp.sum()).sort_values().tail(8)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 3.8),
                               gridspec_kw={"width_ratios": [1.15, 1]})
ax1.barh([nombre(c) for c in imp.index], imp.values * 100, color=AZUL_MED)
for i, v in enumerate(imp.values * 100):
    ax1.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=9)
ax1.set(xlabel="Peso en la decisión (%)", xlim=(0, 74))
ax1.set_title("En qué se apoya el modelo", fontweight="bold", loc="left", fontsize=10)

base = X(va_f.sample(400, random_state=42))
grid = np.unique(np.quantile(train["score_buro"], np.linspace(0.01, 0.99, 20)))
pdp = []
for v in grid:
    tmp = base.copy(); tmp["score_buro"] = v
    pdp.append(modelo.predict_proba(tmp)[:, 1].mean())
ax2.plot(grid, np.array(pdp) * 100, "o-", color=OK, lw=2.5, ms=5)
ax2.set(xlabel="Score de buró", ylabel="Riesgo estimado (%)")
ax2.set_title("Siempre baja: nunca al revés", fontweight="bold", loc="left", fontsize=10)
ax2.annotate("garantizado por diseño,\nno por casualidad", xy=(700, 4), xytext=(560, 14),
             color=OK, fontsize=8.5, arrowprops=dict(arrowstyle="->", color=OK))
fig.tight_layout()
fig.savefig(f"{SALIDA}/03_que_mira_el_modelo.png")
plt.close(fig)
print("✓ 03_que_mira_el_modelo.png")

# ===========================================================================
# FIGURA 4 · Explicación de un caso individual
# ===========================================================================
muestra = va_f.sample(min(2500, len(va_f)), random_state=42)
sv = shap.TreeExplainer(modelo).shap_values(X(muestra))
if isinstance(sv, list):
    sv = sv[1]
p_m = modelo.predict_proba(X(muestra))[:, 1]

idx = int(np.argsort(p_m)[-8])
caso = muestra.iloc[idx]
contrib = pd.Series(sv[idx], index=FEATS).sort_values(key=np.abs, ascending=False).head(6)[::-1]
etiquetas = [f"{nombre(v)}\n({caso[v]:,.0f})" if v not in CAT else f"{nombre(v)}\n({caso[v]})"
             for v in contrib.index]

fig, ax = plt.subplots(figsize=(8.6, 3.8))
ax.barh(etiquetas, contrib.values, color=[ALERTA if v > 0 else OK for v in contrib.values])
ax.axvline(0, color=PETROLEO, lw=1)
for i, v in enumerate(contrib.values):
    ax.text(v + (0.03 if v > 0 else -0.03), i, f"{v:+.2f}", va="center",
            ha="left" if v > 0 else "right", fontsize=9)
umbral = (0.005 * caso.plazo_meses) / (0.005 * caso.plazo_meses + 0.55)
ax.set_xlabel("← empuja a aprobar        |        empuja a rechazar →")
ax.set_title(f"Solicitud {caso.id_solicitud}: riesgo estimado {p_m[idx]:.0%} · "
             f"límite para {int(caso.plazo_meses)} meses: {umbral:.0%} → RECHAZAR",
             fontweight="bold", loc="left", fontsize=10)
ax.set_xlim(contrib.min() - 0.35, contrib.max() + 0.35)
fig.savefig(f"{SALIDA}/04_caso_individual.png")
plt.close(fig)
print(f"✓ 04_caso_individual.png (solicitud {caso.id_solicitud}, "
      f"resultado real: {'mora' if caso[TARGET] == 1 else 'pagó'})")

# ===========================================================================
# FIGURA 5 · Ganancia por política
# ===========================================================================
oof = []
for tr_f2, va_f2 in particiones(train):
    m = nuevo_modelo().fit(X(tr_f2), tr_f2[TARGET],
                           eval_set=[(X(va_f2), va_f2[TARGET])], eval_metric="auc",
                           callbacks=[lgb.early_stopping(50, verbose=False)])
    oof.append(pd.DataFrame({"p": m.predict_proba(X(va_f2))[:, 1], "y": va_f2[TARGET].values,
                             "monto": va_f2.monto_solicitado.values,
                             "plazo": va_f2.plazo_meses.values}))
oof = pd.concat(oof, ignore_index=True)
oof["p_cal"] = IsotonicRegression(out_of_bounds="clip").fit(oof.p, oof.y).predict(oof.p)
oof["G"] = oof.monto * 0.005 * oof.plazo
oof["L"] = oof.monto * 0.55
oof["margen"] = np.where(oof.y == 1, -oof.L, oof.G)
oof["umbral"] = oof.G / (oof.G + oof.L)

MM = 1e6
vals = [oof.margen.sum() / MM,
        oof.loc[oof.p_cal < oof.umbral, "margen"].sum() / MM,
        oof.loc[oof.y == 0, "margen"].sum() / MM]
aps = [1.0, (oof.p_cal < oof.umbral).mean(), (oof.y == 0).mean()]
labels = ["Aprobar todo\n(hoy)", "Política\nrecomendada", "Máximo teórico\n(imposible)"]

fig, ax = plt.subplots(figsize=(7.6, 3.9))
barras = ax.bar(labels, vals, color=[AZUL_CLARO, ACENTO, PETROLEO], width=0.55)
for b, v, a in zip(barras, vals, aps):
    ax.text(b.get_x() + b.get_width()/2, v + 90, f"${v:,.0f} MM\naprueba {a:.0%}",
            ha="center", fontsize=9.5)
ax.annotate("", xy=(0.92, vals[1] * 1.02), xytext=(0.16, vals[0] * 1.30),
            arrowprops=dict(arrowstyle="->", color=ALERTA, lw=2.2))
ax.text(0.54, vals[1] * 0.60, f"+${vals[1]-vals[0]:,.0f} MM\n(+{(vals[1]/vals[0]-1)*100:.0f}%)",
        ha="center", color=ALERTA, fontweight="bold", fontsize=12)
ax.set_ylabel("Ganancia de la cartera (millones CLP)")
ax.set_ylim(0, max(vals) * 1.28)
ax.set_title("Lo que está en juego\nSimulación sobre 7 meses de solicitudes reales",
             fontweight="bold", loc="left", fontsize=11)
fig.savefig(f"{SALIDA}/05_ganancia.png")
plt.close(fig)
print(f"✓ 05_ganancia.png  (base {vals[0]:,.0f} → política {vals[1]:,.0f} MM, "
      f"aprueba {aps[1]:.1%})")

print(f"\nFiguras generadas en {SALIDA}")