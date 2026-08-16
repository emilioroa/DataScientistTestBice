# Uso de herramientas de IA

Documento vivo: se actualiza en cada etapa del desafío. Última actualización: **etapa 1 — EDA y auditoría de datos (versión fusionada)**.

## Herramientas utilizadas

| Herramienta | Uso |
|---|---|
| Claude (Anthropic) | Auditoría exploratoria de la data, generación del notebook de EDA con Plotly, redacción de documentación y discusión metodológica sobre diseño de validación |
| GitHub Copilot | Autocompletado puntual dentro del editor |

**Mi criterio de trabajo:** hice mi propio EDA y en paralelo pedí una auditoría a la IA sobre la misma data, para después contrastar ambas. El notebook final conserva mi estructura y suma los hallazgos que sobrevivieron al cruce. En dos casos el error estaba en la propuesta de la IA, y en uno estaba en mi verificación. Uso la IA para acelerar exploración y escritura de código repetitivo, no para decidir. Toda hipótesis que la IA propone se acepta solo si existe un gráfico o una métrica en el notebook que la respalde. Esa regla — *ninguna conclusión sin evidencia visual* — es la que estructura `notebooks/01_eda.ipynb`.

---

## Ejemplos concretos donde el output de la IA fue incorrecto o subóptimo

### 1. Hipótesis inicial errónea: "las etiquetas recientes están inmaduras"

**Qué propuso la IA.** Antes de ver la data, a partir solo del enunciado, planteó con bastante seguridad que el problema principal sería la **madurez del target**: siendo `default_12m` una ventana de 12 meses y llegando train hasta 2025-02, argumentó que las cohortes recientes no podían tener etiquetas completas, y predijo que la tasa de default caería en los últimos meses de train. La recomendación era excluir o reponderar esas cohortes.

**Qué encontré al verificar.** El gráfico H7 del notebook muestra exactamente lo contrario: la tasa sube de forma monótona de 7,07% (2024-01) a 13,31% (2025-01), sin ninguna caída en el tramo final. Si hubiera etiquetas inmaduras, el patrón sería descendente.

**Qué hice.** Descarté la recomendación de excluir cohortes — habría eliminado justamente la data más parecida al período de test. Reformulé el hallazgo: no hay problema de madurez, hay **deterioro real de la cartera**, explicado por un cambio de mezcla de originación (el canal digital pasa de 36% a 69% del volumen, y tiene 12,5% de default vs. 7,2% de sucursal). Dejé la verificación de madurez explícita en el notebook como nota metodológica, porque el chequeo era correcto aunque la conclusión anticipada no lo fuera.

**Por qué importa.** Es la diferencia entre tirar el 30% de la data por una hipótesis a priori y descubrir la tendencia que obliga a recalibrar el modelo hacia una tasa esperada de ~14% en vez del 9,9% promedio de train.

---

### 2. Diagnóstico apresurado del punto de masa en `edad = 19`

**Qué propuso la IA.** Al detectar que el 5,2% de los registros tiene exactamente 19 años (seis veces la frecuencia de los 20 años), la lectura inicial fue que se trataba de un **código de relleno para edad faltante**, y sugirió convertirlos a `NaN` y agregar una bandera de faltante.

**Qué encontré al verificar.** Crucé el segmento contra otras variables (gráfico H5). Si fueran registros con edad desconocida rellenada con un código, su perfil sería indistinguible del promedio de la cartera. No lo es: la antigüedad laboral mediana de ese grupo es de **12 meses**, contra 46 meses en el tramo 20-25 años. Son personas efectivamente jóvenes.

**Qué hice.** Rechacé la imputación. La explicación consistente es censura en el borde de elegibilidad del producto (19 es la edad mínima). Convertir ese 5,2% a `NaN` habría destruido señal legítima en un segmento que, además, **crece de 5,2% en train a 7,9% en test** — un dato que solo apareció al mirar el segmento en serio, y que refuerza el diagnóstico de deriva.

---

### 3. Diseño de validación subóptimo: split temporal único

**Qué propuso la IA.** Como esquema de validación, un único corte out-of-time: entrenar con 2024-01→2024-09 y validar en 2024-10→2025-02.

**Por qué es subóptimo.** El planteamiento es correcto en dirección (out-of-time y no k-fold aleatorio) pero pobre en ejecución. Con la deriva documentada en H7, un split único (a) entrega una sola estimación, sin noción de su varianza; (b) deja fuera del entrenamiento los cinco meses más recientes, que son los más parecidos al período de test; y (c) valida sobre un tramo de cinco meses en el que la tasa de default cambia casi 3 puntos, mezclando regímenes distintos.

**Qué hice.** Lo reemplacé por **backtesting temporal con ventanas expansivas** (H10): cuatro folds sucesivos donde el entrenamiento crece y la validación avanza en el tiempo. Reporto el promedio de folds y, por separado, el fold más reciente, que es el que mejor representa el escenario de producción. La estimación honesta de performance sale de ahí, no de un k-fold aleatorio.

---

### 4. Elección de librería en el notebook de EDA

**Qué propuso la IA.** Usar LightGBM dentro del notebook de EDA para las pruebas auxiliares (medición del costo de la fuga y validación adversarial).

**Qué hice.** Lo cambié a `HistGradientBoostingClassifier` de scikit-learn. El notebook de EDA no debería depender de la librería de modelado final: son pruebas diagnósticas, no el modelo, y reservar LightGBM para la etapa de modelado mantiene la separación de responsabilidades y reduce las dependencias necesarias para reproducir el EDA. La conclusión de ambos experimentos es idéntica con cualquiera de los dos algoritmos.

---

### 5. Falso negativo en mi propia detección de duplicados

**Qué pasó.** En mi EDA inicial verifiqué duplicados con `train.duplicated().sum()` y concluí "sin duplicados; categóricas limpias". Al contrastar con la auditoría hecha con IA apareció el problema: `id_solicitud` es único en todas las filas, así que al incluirlo en la comparación **ninguna fila puede salir duplicada por construcción**. La verificación estaba mal planteada.

**Qué hice.** Repetí la comparación excluyendo el `id`: aparecen **299 pares idénticos en las 19 columnas restantes**. Antes de eliminarlos verifiqué que no fueran coincidencias legítimas: los pares detectados coinciden en las 19 columnas, mientras que dos solicitudes tomadas al azar coinciden en promedio en 4 (gráfico en §3.6). Agregué el `drop_duplicates` a `src/prepare.py` y corregí la conclusión en el notebook.

**Por qué importa.** Mantenerlos no solo duplicaba el peso de esos casos: con validación por folds, la misma solicitud podía quedar simultáneamente en entrenamiento y validación, inflando la métrica. Este caso va en la dirección contraria a los anteriores — aquí el error fue mío y el cruce con la IA lo detectó. Por eso trabajé las dos auditorías en paralelo y las contrasté en vez de quedarme con una.

---

### 6. Análisis de pricing incompleto en la primera versión

**Qué tenía.** Mi sección de pricing mostraba que la tasa correlaciona −0,56 con el score y +0,21 con el default, y concluía que era "señal derivada". La conclusión era razonable pero no estaba demostrada: la correlación con el score no prueba que **toda** la señal de la tasa venga del score.

**Qué agregué.** Dos análisis que cierran el argumento (§7.3 y §7.4): (a) qué variables mira el motor de pricing —score, uso de línea, consultas y morosidad previa, todas observables por nosotros; ni monto ni plazo, lo que confirma pricing por riesgo y no por producto—; y (b) la prueba decisiva: dentro de cada decil de score, los que recibieron tasa alta se moran ~1,28× más que los de tasa baja, en los 10 deciles. Hay señal residual, pero es débil: el AUC del residuo de la tasa tras remover el score cae de 0,706 a **0,533**.

**Qué cambió en la decisión.** La conclusión operativa se mantiene (entrenar con y sin la variable), pero ahora está cuantificada: el costo esperado de excluirla es bajo. Pasé de una intuición defendible a un número que puedo poner en el informe.

---

### 7. La imputación por mediana generaba registros imposibles (lo detectó la validación, no la lectura del código)

**Qué pasó.** Mi `src/prepare.py` imputaba `antiguedad_laboral_meses` con la mediana global de train (59 meses). Revisando el código no hay nada mal: el patrón fit/transform es correcto y no hay leakage —lo verifiqué comprobando que los valores imputados en test son exactamente la mediana de train—. El problema aparece solo al **auditar la salida**, no la lógica.

**Qué encontré.** Asignar 59 meses de antigüedad a un cliente de 19 años significa que empezó a trabajar a los 14. Contando los registros que violan la restricción `antigüedad <= (edad − 18) × 12` después de limpiar: **622 en train, cuando la data cruda solo traía 46**. Es decir, mi propia limpieza creaba 576 registros imposibles, doce veces más de los que corregía. En test el efecto era de 238 casos. Y se concentraba justo en el segmento joven, que crece de 5,2% a 7,9% entre train y test.

**Qué hice.** Acoté el valor imputado al máximo posible dada la edad: `min(mediana_global, (edad − 18) × 12)`. La corrección resulta además empíricamente acertada — a un cliente de 19 años le asigna 12 meses, que es exactamente la mediana observada del tramo ≤ 21 años. Agregué también la corrección de los 46 casos que ya venían imposibles (`flag_antiguedad_invalida`), el `drop_duplicates` del hallazgo anterior, y una función `validar_salida()` con asserts que falla ruidosamente si cualquiera de las tres correcciones deja de funcionar tras un cambio futuro en el código.

**Qué aprendí de esto.** Revisar código generado o propio leyéndolo no basta: hay defectos que solo existen en la salida. La imputación por mediana es el ejemplo de manual — es correcta variable por variable y rompe las restricciones que existen *entre* variables. De aquí en adelante toda transformación lleva su chequeo de integridad post-ejecución.

---

## Lo que validé manualmente antes de confiar en el código o el análisis

- **La fuga de información (H6).** No la acepté por el AUC de 0,954. La confirmé por tres vías independientes antes de decidir excluir la variable: (a) la tasa de default es perfectamente monótona y llega a 100% para 7 o más contactos —imposible en una variable disponible al momento de la solicitud—; (b) la distribución en test se corta en 6 mientras que en train llega a 12, es decir la cola predictiva simplemente no existe en test; (c) entrenando el mismo modelo con y sin la variable sobre el mismo split, el AUC out-of-time pasa de 0,976 a 0,837. Los tres gráficos están en el notebook.

- **La corrección de unidades del ingreso (H3).** La IA propuso multiplicar por 1.000 los valores bajo 10.000. No lo apliqué a ciegas: verifiqué con un Q-Q plot que la distribución corregida se superpone con la del grupo ya expresado en pesos. La diferencia entre cuantiles homólogos queda bajo el 2%. También confirmé que no existe **ningún** registro en la franja 10.000–100.000, lo que descarta que el corte sea arbitrario.

- **El álgebra del umbral óptimo (H11).** Rehíce a mano la derivación de `p* = G/(G+L)` con `G = monto × 0,005 × plazo` y `L = monto × 0,55`, y verifiqué el resultado no trivial de que **el monto se cancela**, de modo que el umbral depende solo del plazo. Contrasté los valores obtenidos (9,8% a 12 meses, 30,4% a 48 meses) recalculándolos independientemente del código.

- **Los duplicados (H2).** Antes de eliminar 299 filas comprobé que no fueran coincidencias legítimas: los pares detectados coinciden en las 19 columnas, mientras que dos solicitudes tomadas al azar coinciden en promedio en 4. Con variables continuas de por medio, la coincidencia total no es explicable por azar.

- **La salida de `prepare.py`, no solo su lógica.** Comprobé sobre la data completa: que no queden nulos, que los valores imputados en test sean exactamente las medianas de train (ausencia de leakage), que `ratio_deuda_ingreso` no produzca infinitos, y que ninguna restricción entre variables quede violada tras la limpieza. Este último chequeo fue el que reveló el problema del punto 7.

- **Ejecución del notebook de principio a fin.** Lo corrí completo desde un kernel limpio para confirmar que reproduce todos los resultados sin estado residual, y revisé que cada cifra citada en el texto coincida con la salida de la celda correspondiente.

---

## Pendiente para las siguientes etapas

Este documento se irá completando con las iteraciones de modelado, calibración y definición de la política de aprobación.
