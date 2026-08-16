# Desafío Técnico — Data Scientist Senior · Andina Crédito

Modelo de probabilidad de default (mora 90+ días a 12 meses) para solicitudes de crédito de consumo, y su traducción a una política de aprobación con impacto económico cuantificado.

## Estado del proyecto

| Etapa | Estado | Entregable |
|---|---|---|
| 1. EDA y auditoría de datos | ✅ | `notebooks/01_eda.ipynb` |
| 2. Modelado, calibración y política | ✅ | `notebooks/02_modelo.ipynb`, `predictions.csv` |
| 4. Informe ejecutivo | ⏳ | `INFORME.md` |
| Uso de IA | 🔄 en actualización continua | `AI_USAGE.md` |

## Hallazgos principales del EDA

El detalle, con el gráfico que respalda cada conclusión, está en `notebooks/01_eda.ipynb`.

1. **`num_contactos_ult_trimestre` es una fuga de información.** AUC univariado de 0,954 y 100% de default para 7 o más contactos. Su distribución además se corta en 6 en test mientras llega a 12 en train. Se excluye del modelo: incluirla infla el AUC out-of-time de 0,837 a 0,976 sin ningún poder predictivo real.
2. **La cartera se está deteriorando.** La tasa de default sube de 7,1% a 13,3% entre 2024-01 y 2025-01, empujada por el crecimiento del canal digital (36% → 69% del volumen, con 12,5% de default frente a 7,2% en sucursal). El promedio de train (9,9%) subestima el riesgo del período de test, estimado en ~14%.
3. **`ingreso_declarado` mezcla dos unidades.** Un 12% de los registros está expresado en miles de pesos. Se corrige multiplicando por 1.000 los valores bajo 10.000, verificado con Q-Q plot.
4. **299 filas duplicadas exactas** con `id_solicitud` distinto, eliminadas.
5. **El umbral de aprobación óptimo depende del plazo, no del monto**: 9,8% a 12 meses y 30,4% a 48 meses. Esto hace que la calibración del modelo sea más importante que su AUC.

## Instalación y ejecución

Requiere Python 3.10 o superior. Ejecutar en orden desde la raíz del repositorio.

**1. Clonar el repositorio**

```
git clone https://github.com/<tu-usuario>/desafio-ds-senior.git
cd desafio-ds-senior
```

**2. Crear el entorno virtual**

```
python -m venv .venv
```

**3. Activar el entorno**

Windows:

```
.venv\Scripts\activate
```

macOS / Linux:

```
source .venv/bin/activate
```

Debe aparecer `(.venv)` al inicio del prompt.

**4. Instalar las dependencias**

```
pip install --upgrade pip
pip install -r requirements.txt
```

**5. Registrar el kernel de Jupyter**

```
python -m ipykernel install --user --name andina-credito --display-name "Python (Andina Credito)"
```

**6. Abrir el notebook de EDA**

```
jupyter lab notebooks/01_eda.ipynb
```

Seleccionar el kernel **Python (Andina Credito)** y ejecutar todas las celdas (`Run → Run All Cells`).

**7. Regenerar `predictions.csv`**

```
jupyter lab notebooks/02_modelo.ipynb
```

Ejecutar todas las celdas. El notebook escribe `predictions.csv` en la raíz del repositorio
(12.000 filas, columnas `id_solicitud,prob_default`) y valida el formato con un `assert`.
Toma unos 3 minutos, la mayor parte en la búsqueda de hiperparámetros.

## Estructura del repositorio

```
.
├── data/
│   ├── train.csv               # 45.300 solicitudes 2024-01 → 2025-02 con target
│   └── test.csv                # 12.000 solicitudes 2025-02 → 2025-06 sin target
├── notebooks/
│   ├── 01_eda.ipynb            # auditoría de datos: 12 hallazgos, cada uno con su gráfico
│   └── 02_modelo.ipynb         # baseline WOE, LightGBM, explicabilidad, calibración y política
├── src/
│   └── prepare.py              # limpieza fit/transform, sin leakage
├── predictions.csv             # entregable: 12.000 probabilidades
├── INFORME.md                  # informe ejecutivo (etapa 4)
├── AI_USAGE.md                 # documentación del uso de IA
├── requirements.txt
└── README.md
```

## Notas metodológicas

**Validación.** No se usa k-fold aleatorio. Dada la deriva temporal documentada, la estimación de performance proviene de un backtesting temporal con ventanas expansivas (cuatro folds sucesivos), reportando el promedio y, por separado, el fold más reciente por ser el más representativo del período de test.

**Calibración.** Como la política de aprobación compara probabilidades contra umbrales absolutos, la calibración es más crítica que el ranking. Se reportan Brier score y curva de calibración además del AUC.

**Explicabilidad.** El modelo lleva restricciones de monotonía en 7 variables donde el negocio
tiene una expectativa inequívoca, verificadas por dependencia parcial. Se acompaña de un
baseline logístico con WOE, importancia por ganancia, análisis SHAP global e individual.

**Gráficos.** El EDA usa Plotly. Los gráficos son interactivos y se renderizan dentro del notebook; `nbformat` es una dependencia obligatoria para ello.
