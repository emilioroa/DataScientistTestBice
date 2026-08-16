# Uso de IA en este desafío

Este documento describe de forma transparente cómo utilicé herramientas de IA
durante el desarrollo del desafío, incluyendo los casos donde su output fue
incorrecto, incompleto o subóptimo y requirió mi revisión y corrección.

## 1. Herramientas utilizadas y para qué

| Herramienta | Para qué la usé |
|-------------|-----------------|
| **Microsoft Copilot (Claude)** | Asistencia en la exploración de datos, generación de código base para `prepare.py` y el notebook de EDA, discusión conceptual (buró de crédito, risk-based pricing), estrategia de validación y redacción de documentación. |
| **GitHub Copilot** (autocompletado en VS Code) | Sugerencias de código línea a línea durante el desarrollo. |

**Metodología de trabajo — iterativa y crítica.** No acepté los outputs tal como
se generaron. Trabajé en ciclos de *revisión → comentario → corrección → validación*:
revisé cada entregable, pedí cambios concretos y verifiqué el resultado con evidencia
sobre la data real antes de darlo por bueno. La sección 2 documenta las correcciones
de fondo y la sección 3 las iteraciones de mejora que yo dirigí.

## 2. Ejemplos donde el output de la IA fue incorrecto / subóptimo y cómo lo corregí

### Ejemplo 1 — Imputación ingenua del ingreso (error de criterio)
- **Qué sugirió la IA inicialmente:** ante los nulos y valores bajos de
  `ingreso_declarado`, imputar los faltantes con la media/mediana global y tratar
  los valores muy bajos como outliers a recortar.
- **Por qué era subóptimo:** ~10% de las filas tenían valores en el rango 280–5.014,
  con un **gap perfecto** (ningún valor entre 5.014 y 280.000). No eran outliers
  aleatorios: eran un **error de unidad** (ingresos en *miles de pesos*). Recortarlos
  habría destruido información válida de ~4.500 clientes.
- **Mi decisión:** tras revisar la evidencia (mediana del grupo bajo ×1000 ≈ mediana
  global; ratio deuda/ingreso resultante ~1,9, coherente), **yo opté por la Opción A**:
  corregir ×1000 y **dejar una bandera** `flag_ingreso_corregido`, documentándolo como
  supuesto a validar con el negocio. Pedí explícitamente que se agregara la marca.

### Ejemplo 2 — Validación con split aleatorio (error metodológico grave)
- **Qué sugirió la IA inicialmente:** `train_test_split` aleatorio (hold-out 20%).
- **Por qué era incorrecto:** la tasa de default **crece** en el tiempo (7% → 13%)
  y el test es un período **posterior** al train. Un split aleatorio mezcla meses y
  da una estimación **optimista y deshonesta**, justo lo que la evaluación penaliza.
- **Qué hice:** lo reemplacé por **validación temporal (out-of-time)**: entrenar en
  meses antiguos y validar en los recientes, simulando el gap real hacia producción.

### Ejemplo 3 — Edad como outlier a winsorizar
- **Qué sugirió la IA:** winsorizar/clipping al percentil 99 de `edad`.
- **Por qué era subóptimo:** las edades ≥ 100 (hasta 133) no son extremos legítimos,
  son **errores de captura**. Winsorizar los habría "aplastado" a ~73 años, inventando dato.
- **Qué hice:** marcarlas como inválidas (`NaN`) + `flag_edad_invalida` e imputar con
  la mediana de train (tratarlas como faltante, no como valor real extremo).

### Ejemplo 4 — "seaborn es interactivo" (imprecisión técnica que detecté)
- **Contexto:** pedí cambiar los gráficos de matplotlib por una librería mejor y en
  la conversación se mencionó seaborn como opción "interactiva".
- **Qué estaba mal:** **seaborn NO es interactivo** (está construido sobre matplotlib
  y genera gráficos estáticos). Yo aclaré que lo que buscaba era **interactividad real**
  (zoom, hover, tooltips).
- **Qué hice:** decidí usar **Plotly** en lugar de seaborn/matplotlib para todo el EDA,
  y pedí corregir la redacción para no afirmar algo técnicamente incorrecto.

### Ejemplo 5 — Señal predictiva incompleta (solo 2 variables)
- **Qué produjo la IA inicialmente:** en la sección de señal predictiva analizó solo
  `score_buro` y `tipo_empleo`, dejando fuera el resto de variables.
- **Por qué era insuficiente:** una exploración seria debe revisar **todas** las
  variables relevantes y priorizarlas con un criterio objetivo, no elegir dos a mano.
- **Mi corrección (la pedí explícitamente):** reordenar el EDA para **primero** calcular
  correlaciones + ranking, y **luego** analizar la señal del **Top 10** por quintiles
  (numéricas) o por categoría (categóricas). Además señalé que la correlación de Pearson
  no cubre las variables categóricas, por lo que se incorporó una métrica comparable
  (**AUC univariado**) para rankear numéricas y categóricas en igualdad de condiciones.

### Ejemplo 6 — Faltaba el análisis del pricing
- **Qué faltaba:** la IA no incluyó un análisis específico de `tasa_interes_anual`.
- **Por qué importa:** la tasa la asigna el sistema de *risk-based pricing*, así que es
  predictiva pero **no es señal independiente** (codifica el riesgo vía score). Ignorarlo
  puede llevar a un modelo que se degrade si cambia la política de pricing.
- **Mi corrección (la pedí explícitamente):** agregar una sección de pricing (correlaciones
  tasa↔score↔default, tasa de default por quintil de tasa, y scatter tasa vs score) y dejar
  la decisión de **modelar con y sin** la variable para medir su aporte real.

## 3. Iteraciones de mejora que yo dirigí sobre los entregables

Además de las correcciones de fondo, guié varias iteraciones de forma y contenido:

- **Confirmé el diseño de `src/prepare.py` (módulo centralizado):** cuestioné el
  `from prepare import preparar_datos` preguntando si era una librería externa a instalar.
  Tras confirmar que es un **archivo propio** del repo (no una dependencia), validé y
  mantuve el diseño por ser la práctica estándar (una sola fuente de verdad, anti-leakage),
  en lugar de duplicar la limpieza dentro del notebook.
- **Migración a gráficos interactivos (Plotly):** pedí reemplazar matplotlib.
- **Sección de correlaciones ampliada:** pedí que se mostrara la **tabla completa**, una
  **matriz de correlación** interactiva y un **ranking** de variables por correlación con
  el target (no solo una lista de números).
- **Paleta corporativa Banco BICE:** solicité los códigos oficiales y pedí aplicarlos a
  todos los gráficos, por ser una entrega dirigida a BICE
  (`#0E162A`, `#2E536D`, `#A9BDDF`, `#CE894D`, `#062C33`).
- **Reordenamiento del EDA:** pedí que las correlaciones/ranking fueran antes de la señal
  predictiva, y que la señal se analizara sobre el Top 10.
- **`requirements.txt` completo:** pedí consolidar todas las dependencias, incluyendo las
  que tuve que instalar aparte para Plotly (`nbformat`, ver Ejemplo/Nota abajo).

## 4. Incidencias técnicas resueltas durante el trabajo

- **`ValueError: Mime type rendering requires nbformat>=4.2.0`:** al ejecutar los gráficos
  Plotly en el notebook faltaba la dependencia `nbformat`. La instalé (`pip install nbformat`),
  reinicié el kernel y **la agregué al `requirements.txt`** para que el entorno sea reproducible
  por quien evalúe el repo.
- **`git` no reconocido en la terminal:** al inicio, Git no estaba en el PATH; lo instalé y
  reabrí la terminal para poder clonar y versionar el trabajo.

## 5. Qué validé manualmente antes de confiar en el código/análisis generado

- [x] **Data leakage:** estadísticos de imputación calculados **solo en train** y
      aplicados a test (fit/transform en `prepare.py`). Ninguna variable usa info posterior
      al desembolso (según el diccionario, todas son *point-in-time*).
- [x] **Corrección del ingreso:** confirmé el gap limpio entre regímenes y la coherencia
      del ratio deuda/ingreso tras multiplicar ×1000.
- [x] **Validación temporal:** confirmé la tendencia creciente del default por mes antes
      de descartar el split aleatorio.
- [x] **Ranking predictivo:** revisé que el AUC univariado ordene de forma coherente y que
      las categóricas queden comparables con las numéricas.
- [x] **Reproducibilidad:** ejecuté el notebook de principio a fin sin errores y `prepare.py`
      como smoke test (0 nulos restantes, banderas OK).
- [x] **Gráficos Plotly:** verifiqué que todas las figuras interactivas se generan sin errores.
- [x] **Formato de salida:** (pendiente en el paso de predicción) confirmar que
      `predictions.csv` tenga exactamente 12.000 filas y las columnas pedidas.

> Nota: este archivo se actualiza a medida que avanzan las etapas (modelado, validación,
> política de aprobación) y a medida que reviso e itero sobre los outputs generados.
