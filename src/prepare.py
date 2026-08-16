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
  3. COHERENCIA POST-IMPUTACIÓN: imputar no puede generar registros
     lógicamente imposibles (ver `_imputar_con_coherencia`).
  4. DECISIONES DOCUMENTADAS: ver docstring de cada función.

Uso:
    from prepare import preparar_datos
    train_clean, test_clean, params = preparar_datos(train_raw, test_raw)
"""

import numpy as np
import pandas as pd

# --- Constantes de negocio (decisiones documentadas) ---------------------
UMBRAL_INGRESO_MILES = 50_000   # bajo este valor, el ingreso está en miles (error de unidad)
EDAD_MAX_VALIDA = 100           # edad >= 100 se considera error de captura
EDAD_INICIO_LABORAL = 18        # edad desde la que se puede acumular antigüedad laboral
COLS_NULOS = ["ingreso_declarado", "antiguedad_laboral_meses"]

# Variable excluida del modelo por fuga de información (ver notebook §6.2).
# No se elimina aquí: el notebook la necesita para documentar el hallazgo.
VARIABLES_CON_FUGA = ["num_contactos_ult_trimestre"]


def _corregir_ingreso_en_miles(df: pd.DataFrame) -> pd.DataFrame:
    """
    DECISIÓN (Opción A): ~10% de las filas tienen `ingreso_declarado` en
    MILES de pesos (valores 280–5.014) en lugar de pesos. La evidencia:
    existe un GAP limpio (nada entre 5.014 y 280.000) y el Q-Q plot del
    grupo bajo ×1000 contra el grupo alto se superpone con menos de 2% de
    diferencia entre cuantiles homólogos. Se multiplican ×1000 y se deja
    la bandera `flag_ingreso_corregido`.
    """
    df = df.copy()
    mask = (df["ingreso_declarado"] < UMBRAL_INGRESO_MILES).fillna(False)
    df["flag_ingreso_corregido"] = mask.astype(int)
    df.loc[mask, "ingreso_declarado"] *= 1000
    return df


def _corregir_edad(df: pd.DataFrame) -> pd.DataFrame:
    """
    DECISIÓN: edad >= 100 años (hasta 133) es imposible → se marca como
    faltante para imputar luego, dejando bandera `flag_edad_invalida`.
    """
    df = df.copy()
    mask = (df["edad"] >= EDAD_MAX_VALIDA).fillna(False)
    df["flag_edad_invalida"] = mask.astype(int)
    df.loc[mask, "edad"] = np.nan
    return df


def _corregir_antiguedad_laboral(df: pd.DataFrame) -> pd.DataFrame:
    """
    DECISIÓN: 46 registros declaran una antigüedad laboral MAYOR a la vida
    laboral posible dada su edad (el máximo son 936 meses = 78 años
    trabajando). No se detecta mirando la variable sola: solo aparece al
    cruzarla contra `edad`. → NaN + bandera `flag_antiguedad_invalida`.

    Se ejecuta DESPUÉS de `_corregir_edad` para que el tope se calcule
    sobre edades ya validadas.
    """
    df = df.copy()
    tope = (df["edad"] - EDAD_INICIO_LABORAL) * 12
    mask = (df["antiguedad_laboral_meses"] > tope).fillna(False)
    df["flag_antiguedad_invalida"] = mask.astype(int)
    df.loc[mask, "antiguedad_laboral_meses"] = np.nan
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


def _imputar_con_coherencia(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Imputa con las medianas de TRAIN, pero ACOTANDO la antigüedad laboral
    al máximo posible dada la edad del cliente.

    POR QUÉ: imputar la mediana global (59 meses) a un cliente de 19 años
    genera un registro imposible — alguien que habría empezado a trabajar
    a los 14. Sin este tope la imputación creaba 576 registros imposibles
    en train y 238 en test: doce veces más de los que la limpieza corrige.
    El daño se concentra en el segmento joven, que además crece de 5,2% a
    7,9% entre train y test.

    El tope resuelve el problema de forma natural: a un cliente de 19 años
    le asigna 12 meses, que coincide con la mediana observada del tramo
    <= 21 años (12,0 meses).
    """
    df = df.copy()
    df["edad"] = df["edad"].fillna(params["mediana_edad"])
    df["ingreso_declarado"] = df["ingreso_declarado"].fillna(params["mediana_ingreso"])

    tope = ((df["edad"] - EDAD_INICIO_LABORAL) * 12).clip(lower=0)
    valor_imputado = np.minimum(params["mediana_antig_laboral"], tope)
    df["antiguedad_laboral_meses"] = df["antiguedad_laboral_meses"].fillna(valor_imputado)
    return df


def fit_parametros(train: pd.DataFrame) -> dict:
    """
    Calcula los parámetros de imputación USANDO SOLO TRAIN (evita leakage).
    Devuelve un dict con las medianas a usar tanto en train como en test.
    """
    # Se corrige primero para que las medianas se calculen sobre valores válidos
    tmp = _corregir_ingreso_en_miles(train)
    tmp = _corregir_edad(tmp)
    tmp = _corregir_antiguedad_laboral(tmp)

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

    NOTA: no es idempotente por diseño. Espera la data CRUDA; aplicarlo dos
    veces deja las banderas en cero porque la segunda pasada ya no encuentra
    nada que corregir. Partir siempre del DataFrame original.
    """
    df = df.copy()

    # 1) Parsear fecha
    df["fecha_solicitud"] = pd.to_datetime(df["fecha_solicitud"], errors="coerce")

    # 2) Correcciones + banderas (el orden importa)
    df = _agregar_flags_nulos(df)            # flags de nulos ANTES de imputar
    df = _corregir_ingreso_en_miles(df)      # ingreso en miles ×1000 + flag
    df = _corregir_edad(df)                  # edad >= 100 -> NaN + flag
    df = _corregir_antiguedad_laboral(df)    # antigüedad > vida laboral -> NaN + flag

    # 3) Imputación con medianas de TRAIN, respetando la coherencia edad/antigüedad
    df = _imputar_con_coherencia(df, params)

    # 4) Feature simple y robusto: ratio deuda/ingreso (capacidad de pago)
    df["ratio_deuda_ingreso"] = df["deuda_sistema"] / df["ingreso_declarado"].replace(0, np.nan)

    return df


def preparar_datos(train: pd.DataFrame, test: pd.DataFrame):
    """
    Pipeline completo. Devuelve (train_clean, test_clean, params).
    Los params se ajustan SOLO con train y se reutilizan en test.

    DECISIÓN: se eliminan 299 filas duplicadas exactas de train. Tienen
    `id_solicitud` distinto, por lo que `df.duplicated()` no las detecta:
    hay que excluir el id de la comparación. Los pares detectados coinciden
    en las 19 columnas restantes, mientras que dos solicitudes al azar
    coinciden en ~4 → es duplicación de ingesta, no coincidencia.
    Mantenerlas duplicaría el peso de esos casos y, peor, filtraría entre
    folds de validación (la misma solicitud en entrenamiento y validación).

    Solo se aplica a train: test debe conservar sus 12.000 filas intactas
    para la entrega de `predictions.csv`.
    """
    cols_sin_id = [c for c in train.columns if c != "id_solicitud"]
    n_dup = int(train.duplicated(subset=cols_sin_id).sum())
    train = train.drop_duplicates(subset=cols_sin_id, keep="first").reset_index(drop=True)

    params = fit_parametros(train)
    params["duplicados_eliminados"] = n_dup

    train_clean = transform(train, params)
    test_clean = transform(test, params)
    return train_clean, test_clean, params


def validar_salida(df: pd.DataFrame, nombre: str = "df") -> None:
    """
    Chequeos de integridad post-limpieza. Falla ruidosamente si alguna
    corrección deja de funcionar tras un cambio en el código.
    """
    assert df[["edad", "ingreso_declarado", "antiguedad_laboral_meses"]].isna().sum().sum() == 0, \
        f"{nombre}: quedaron nulos sin imputar"
    assert (df["edad"] < EDAD_MAX_VALIDA).all(), f"{nombre}: quedaron edades imposibles"
    tope = (df["edad"] - EDAD_INICIO_LABORAL) * 12
    n_imp = int((df["antiguedad_laboral_meses"] > tope).sum())
    assert n_imp == 0, f"{nombre}: {n_imp} registros con antigüedad > vida laboral posible"
    assert np.isfinite(df["ratio_deuda_ingreso"]).all(), f"{nombre}: ratio con inf o NaN"
    print(f"  {nombre}: OK ({len(df):,} filas)")


if __name__ == "__main__":
    # Prueba rápida de humo (smoke test)
    tr = pd.read_csv("data/train.csv")
    te = pd.read_csv("data/test.csv")
    tr_c, te_c, p = preparar_datos(tr, te)
    print("Parámetros de imputación (de train):", p)
    print("Train limpio:", tr_c.shape, "| Test limpio:", te_c.shape)
    print("Nulos restantes train:", tr_c[COLS_NULOS + ["edad"]].isna().sum().to_dict())
    print("Nuevas columnas flag:", [c for c in tr_c.columns if c.startswith("flag_")])
    print("Validación de integridad:")
    validar_salida(tr_c, "train_clean")
    validar_salida(te_c, "test_clean")