"""
prepare.py — Limpieza y preparación de datos · Andina Crédito
================================================================

Módulo de preparación para el modelo de probabilidad de default.

Principios de diseño:
  1. SIN DATA LEAKAGE: todos los estadísticos de imputación se calculan
     SOLO sobre train y se aplican a test (patrón fit/transform).
  2. TRAZABILIDAD: cada corrección deja una BANDERA (flag_*) para que el
     modelo pueda aprender si "el dato faltaba/estaba corregido" es en sí
     mismo predictivo.
  3. DECISIONES DOCUMENTADAS: ver docstring de cada función.

Uso:
    from prepare import preparar_datos
    train_clean, test_clean, params = preparar_datos(train_raw, test_raw)
"""

import numpy as np
import pandas as pd

# --- Constantes de negocio (decisiones documentadas) ---------------------
UMBRAL_INGRESO_MILES = 50_000   # bajo este valor, el ingreso está en miles (error de unidad)
EDAD_MAX_VALIDA = 100           # edad >= 100 se considera error de captura
COLS_NULOS = ["ingreso_declarado", "antiguedad_laboral_meses"]


def _corregir_ingreso_en_miles(df: pd.DataFrame) -> pd.DataFrame:
    """
    DECISIÓN (Opción A): ~10% de las filas tienen `ingreso_declarado` en
    MILES de pesos (valores 280–5.014) en lugar de pesos. La evidencia:
    existe un GAP limpio (nada entre 5.014 y 280.000) y la mediana del
    grupo bajo ×1000 coincide con la mediana global. Se multiplican ×1000
    y se deja la bandera `flag_ingreso_corregido`.
    """
    df = df.copy()
    mask = df["ingreso_declarado"] < UMBRAL_INGRESO_MILES
    df["flag_ingreso_corregido"] = mask.fillna(False).astype(int)
    df.loc[mask, "ingreso_declarado"] = df.loc[mask, "ingreso_declarado"] * 1000
    return df


def _corregir_edad(df: pd.DataFrame) -> pd.DataFrame:
    """
    DECISIÓN: edad >= 100 años (hasta 133) es imposible → se marca como
    faltante para imputar luego, dejando bandera `flag_edad_invalida`.
    """
    df = df.copy()
    mask = df["edad"] >= EDAD_MAX_VALIDA
    df["flag_edad_invalida"] = mask.astype(int)
    df.loc[mask, "edad"] = np.nan
    return df


def _agregar_flags_nulos(df: pd.DataFrame) -> pd.DataFrame:
    """
    DECISIÓN: `ingreso_declarado` (~18%) y `antiguedad_laboral_meses` (~16%)
    tienen nulos. Antes de imputar, se deja una bandera de faltante porque
    el HECHO de que falte puede ser predictivo (ej. no declarar ingreso).
    """
    df = df.copy()
    for col in COLS_NULOS:
        df[f"flag_{col}_faltante"] = df[col].isna().astype(int)
    return df


def fit_parametros(train: pd.DataFrame) -> dict:
    """
    Calcula los parámetros de imputación USANDO SOLO TRAIN (evita leakage).
    Devuelve un dict con las medianas a usar tanto en train como en test.
    """
    # Se corrige primero para que las medianas se calculen sobre valores válidos
    tmp = _corregir_ingreso_en_miles(train)
    tmp = _corregir_edad(tmp)

    params = {
        "mediana_edad": float(tmp["edad"].median()),
        "mediana_ingreso": float(tmp["ingreso_declarado"].median()),
        "mediana_antig_laboral": float(tmp["antiguedad_laboral_meses"].median()),
    }
    return params


def transform(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Aplica todas las correcciones + imputación usando `params` (de train).
    Sirve tanto para train como para test.
    """
    df = df.copy()

    # 1) Parsear fecha
    df["fecha_solicitud"] = pd.to_datetime(df["fecha_solicitud"], errors="coerce")

    # 2) Correcciones + banderas
    df = _agregar_flags_nulos(df)          # flags de nulos ANTES de imputar
    df = _corregir_ingreso_en_miles(df)    # ingreso en miles ×1000 + flag
    df = _corregir_edad(df)                # edad>=100 -> NaN + flag

    # 3) Imputación con medianas de TRAIN (sin leakage)
    df["edad"] = df["edad"].fillna(params["mediana_edad"])
    df["ingreso_declarado"] = df["ingreso_declarado"].fillna(params["mediana_ingreso"])
    df["antiguedad_laboral_meses"] = df["antiguedad_laboral_meses"].fillna(
        params["mediana_antig_laboral"]
    )

    # 4) Feature simple y robusto: ratio deuda/ingreso (capacidad de pago)
    df["ratio_deuda_ingreso"] = df["deuda_sistema"] / df["ingreso_declarado"]

    return df


def preparar_datos(train: pd.DataFrame, test: pd.DataFrame):
    """
    Pipeline completo. Devuelve (train_clean, test_clean, params).
    Los params se ajustan SOLO con train y se reutilizan en test.
    """
    params = fit_parametros(train)
    train_clean = transform(train, params)
    test_clean = transform(test, params)
    return train_clean, test_clean, params


if __name__ == "__main__":
    # Prueba rápida de humo (smoke test)
    tr = pd.read_csv("data/train.csv")
    te = pd.read_csv("data/test.csv")
    tr_c, te_c, p = preparar_datos(tr, te)
    print("Parámetros de imputación (de train):", p)
    print("Train limpio:", tr_c.shape, "| Test limpio:", te_c.shape)
    print("Nulos restantes train:", tr_c[COLS_NULOS + ["edad"]].isna().sum().to_dict())
    print("Nuevas columnas flag:", [c for c in tr_c.columns if c.startswith("flag_")])
