# Uso de herramientas de IA

## Herramientas

| Herramienta | Uso |
|---|---|
| Claude (Anthropic) | Auditoría exploratoria, generación de código para gráficos y modelado, discusión metodológica, redacción de documentación |
| GitHub Copilot | Autocompletado puntual en el editor |

Trabajé con la IA de forma intensiva y en las cuatro etapas del desafío. Este documento describe **cómo** la dirigí, porque el criterio está en la dirección más que en el volumen de código generado.

---

## Cómo dirigí el trabajo

Cinco reglas que apliqué de forma sistemática. No son declaraciones de principios: cada una produjo correcciones concretas que están documentadas más abajo.

### 1. Ninguna conclusión sin un gráfico que permita verificarla

Es la regla que estructura `01_eda.ipynb`. Cada hallazgo va con la evidencia visual al lado, no en un anexo. El motivo es práctico: una afirmación sin gráfico es una afirmación que nadie puede refutar, ni siquiera yo. Cuando le pedí a la IA que respaldara visualmente cada conclusión, varias no sobrevivieron al ejercicio.

### 2. Cuantificar, no argumentar

Fue mi exigencia más productiva. Ante cualquier afirmación causal o de impacto, pedí el número antes de aceptarla. Los tres errores más graves de esta lista —la atribución del deterioro al cambio de canal, el peso del umbral por plazo, y la hipótesis de las etiquetas inmaduras— eran razonamientos plausibles, bien construidos y **nunca medidos**. Un relato ordenado es exactamente el tipo de conclusión que nadie cuestiona en una presentación.

### 3. Cuestionar los gráficos que no se entienden

Un gráfico confuso casi siempre esconde un problema, no solo un tema estético. Cuando el eje temporal de la composición etaria apareció estirado desde 1970, no era un asunto de formato: era una posición numérica interpretada como fecha. Cuando la flecha de la figura de ganancias tapaba una etiqueta, había que rehacerla porque esa figura va al informe del gerente.

### 4. Exigir que lo técnico se explique en simple

Hubo análisis que la IA produjo correctamente y que yo no manejaba al 100%. En vez de aceptarlos e incorporarlos, pedí explicación antes de aprobarlos. La calibración isotónica es el caso claro: entenderla —que es una función monótona creciente, que por eso preserva el ranking y por eso el AUC no se mueve, que corrige el nivel y no el orden— fue lo que me permitió decidir con criterio propio **no** aplicar el ajuste por deriva. Sin esa comprensión habría aceptado la recomendación por defecto.

La misma exigencia aplicó a la sección de la política de aprobación: la primera versión mezclaba el ejemplo económico, el backtest, la curva de decisión y la calibración en un bloque denso. Pedí desarmarla en subsecciones con un propósito cada una, y que se justificara explícitamente por qué se usaban `HistGradientBoostingClassifier` e `IsotonicRegression`. Si yo no puedo explicar una decisión, no puedo defenderla en una reunión.

### 5. Foco explícito en explicabilidad

Lo definí como criterio transversal del modelado, no como una sección al final. Un modelo de riesgo crediticio tiene que explicarse ante el gerente de Riesgo, ante auditoría y ante el cliente al que se le rechaza. De ahí salieron tres decisiones de diseño: incluir un **baseline logístico con WOE** aunque cueste tiempo, imponer **restricciones de monotonía** en siete variables aceptando un modelo potencialmente peor en métrica a cambio de uno defendible, y construir la **explicación individual** de una solicitud rechazada, que es el caso de uso operativo real.

### 6. Estructura narrativa para tres audiencias

Le pedí explícitamente a la IA que fuera armando el EDA y el modelado como un relato seguible, no como una lista de hallazgos. La entrega tiene que funcionar para tres lectores distintos:

- **Para mí**, que necesito poder retomar el trabajo y defender cada decisión.
- **Para otro data scientist**, que debe poder seguir el hilo y reproducir el resultado.
- **Para la gerencia**, que necesita entender el problema y la recomendación sin leer código.

Cuando la IA propuso un EDA organizado como "hallazgo 1, hallazgo 2, hallazgo 3", lo rechacé: mantuve mi estructura de capítulos y le pedí que insertara sus hallazgos donde correspondía dentro de ese hilo. Por eso la fuga de información aparece en el capítulo de señal predictiva, donde encabeza el ranking, y no en un apartado suelto. Esa misma exigencia derivó en pedir que el informe ejecutivo llevara **gráficos incorporados** — cinco figuras que hacen visible el problema, el dato contaminado, en qué se apoya el modelo, un caso individual explicado y la ganancia en juego.

---

## Ejemplos concretos donde el output de la IA fue incorrecto o subóptimo

Los agrupé por tipo de error, porque el patrón importa más que el conteo.

### A · Conclusiones plausibles que nunca se midieron

Es la categoría más peligrosa: no hay código roto ni dato malo, solo un razonamiento bien construido aceptado sin verificación.

**A1. La atribución del deterioro al cambio de canal.** El EDA afirmaba, en su primera versión, que el alza de mora "no es un shock macro, es un cambio de mezcla de originación", apoyándose en que el canal digital pasó de 36% a 69% del volumen y tiene 12,5% de mora contra 7,2% de sucursal. Ambos hechos son ciertos y no bastan para sostener la conclusión.

Lo descubrí investigando otra cosa: quise probar si el pico de solicitantes de 19 años estaba creciendo y si eso explicaba el alza. Al medir esa hipótesis correspondía aplicar la misma vara a la afirmación sobre el canal. Con estandarización directa —congelar las tasas de default de cada grupo en su nivel de 2024-01 y dejar variar solo la composición— el resultado desarma ambas versiones: la mezcla etaria explica **8,9%** del alza, el canal **14,5%**, y juntos, descontando el solapamiento, **18,8%**. **Más del 80% es deterioro dentro de cada perfil.** El segmento sucursal / 40-49 años, el más estable de la cartera, pasó de 6,8% a 10,6% de mora sin que su composición cambiara.

Agregué §8.2 al EDA con la descomposición, corregí §8.1 y reescribí la sección 1 del informe ejecutivo, que repetía la atribución equivocada. La implicancia es más importante que la corrección: si el mismo perfil es hoy más riesgoso, **ninguna variable disponible lo captura**, lo que refuerza la decisión de declarar la brecha de calibración en vez de ajustarla, y convierte el hallazgo en una pregunta para la gerencia antes que para el modelo.

**A2. El umbral por plazo, sobrevendido.** La derivación de que el umbral óptimo depende del plazo y no del monto es correcta —la verifiqué a mano, incluido el resultado no trivial de que el monto se cancela— pero la IA la presentó como el gran hallazgo económico, con la frase "un corte único deja valor sobre la mesa". Al montar el backtest con un diseño que eligiera el umbral global *fuera* de la muestra de evaluación, el umbral por plazo rinde 1.057 MM contra 1.031 MM del mejor corte único: **+2,5%**. Real, defendible, y un refinamiento, no el titular.

Reordené la narrativa: el titular medido es que pasar de aprobar todo a aplicar **cualquier** umbral sensato multiplica la ganancia. El umbral por plazo es el párrafo fino que sigue.

**A3. La hipótesis de las etiquetas inmaduras.** Antes de ver los datos, y solo a partir del enunciado, la IA planteó con seguridad que el problema principal sería la madurez del target y predijo que la tasa de default caería en las cohortes recientes de train. Recomendó excluirlas. El gráfico mensual muestra exactamente lo contrario: la mora sube de forma monótona hasta el último mes. Haber seguido esa recomendación habría eliminado justamente los datos más parecidos al período de test. Dejé la verificación de madurez en el notebook como nota metodológica, porque el chequeo era correcto aunque la conclusión anticipada no lo fuera.

### B · Diagnósticos apresurados sobre los datos

**B1. El pico en edad = 19 como código de faltante.** Al detectar que el 5,2% de los registros tiene exactamente 19 años, la lectura inicial fue que se trataba de un relleno para edad faltante, con recomendación de convertirlos a nulo. Crucé el segmento contra otras variables: si fuera relleno, su perfil sería indistinguible del promedio, y no lo es —su antigüedad laboral mediana es de 12 meses contra 46 en el tramo 20-25. Son jóvenes reales, y 19 es la edad mínima de elegibilidad. Imputarlos habría destruido señal legítima en un segmento que además crece de 5,2% a 7,9% entre train y test.

**B2. Descartar `canal` por derivar en el tiempo.** Tras la validación adversarial, la IA sugirió que la deriva "estaba concentrada en `canal` y la variable con fuga", tratando ambas como equivalentes. Rechacé el criterio: `canal` es información legítima disponible al momento de la solicitud, y su cambio en el tiempo es exactamente lo que describe cómo está mutando la cartera. Además el criterio no es consistente — bajo esa misma lógica habría que eliminar `edad` y `score_buro`, que también derivan de forma marcada.

Corregí la sección para dejar claro qué es la validación adversarial: **un diagnóstico de magnitud, no un criterio de selección de variables**. La única exclusión justificada es la fuga, y no por derivar sino por ser posterior al desembolso.

### C · Defectos que solo aparecen al auditar la salida

Leer el código no basta. Estos tres no se ven revisando la lógica.

**C1. La imputación generaba registros imposibles.** Mi `prepare.py` imputaba la antigüedad laboral con la mediana global (59 meses). El código es correcto y no tiene leakage —lo verifiqué comprobando que los valores imputados en test son exactamente la mediana de train. Pero asignar 59 meses a un cliente de 19 años implica que empezó a trabajar a los 14. Contando los registros que violan `antigüedad ≤ (edad − 18) × 12` después de limpiar: **622 en train, cuando la data cruda traía 46**. Mi limpieza creaba 576 casos imposibles, doce veces más de los que corregía, concentrados en el segmento joven.

La corrección fue acotar el valor imputado al máximo posible dada la edad, que además resulta empíricamente acertada: a un cliente de 19 años le asigna 12 meses, exactamente la mediana observada del tramo ≤21. Agregué una función `validar_salida()` con asserts que falla ruidosamente si cualquiera de las correcciones deja de funcionar.

**C2. Verificación de monotonía con la herramienta equivocada.** Tras entrenar LightGBM con restricciones en 7 variables, la IA propuso verificarlas con el efecto SHAP promedio por decil. El chequeo dio **incumplimiento en tres variables**. El error era del método: SHAP absorbe interacciones y al agrupar por deciles mezcla perfiles, así que el promedio puede oscilar aunque cada predicción sea monótona. Lo que la restricción garantiza es que al mover **solo** esa variable, dejando el resto fijo, la predicción no cambie de dirección — y eso lo mide la **dependencia parcial**. Bajo el método correcto las siete se cumplen sin excepción.

De haber aceptado el primer resultado habría abandonado una decisión de diseño que resultó buena: la monotonía no cuesta AUC en estos datos (0,8438 con restricciones contra 0,8423 sin ellas).

**C3. Mi propio falso negativo en duplicados.** Este error fue mío y lo detectó el cruce con la auditoría de la IA. Verifiqué duplicados con `train.duplicated().sum()` y concluí "sin duplicados". El problema es que `id_solicitud` es único en todas las filas, así que al incluirlo en la comparación **ninguna fila puede salir duplicada por construcción**. Excluyendo el id aparecen **299 pares idénticos** en las 19 columnas restantes. Antes de eliminarlos verifiqué que no fueran coincidencias: los pares detectados coinciden en las 19 columnas, mientras que dos solicitudes al azar coinciden en promedio en 4.

Mantenerlos no solo duplicaba el peso de esos casos: con validación por folds, la misma solicitud podía quedar simultáneamente en entrenamiento y validación. Trabajé las dos auditorías en paralelo precisamente para que este tipo de punto ciego apareciera.

### D · Decisiones metodológicas subóptimas

**D1. Split temporal único.** Como esquema de validación, la IA propuso un solo corte out-of-time. La dirección es correcta —temporal y no aleatorio— pero la ejecución es pobre: entrega una sola estimación sin noción de su varianza, deja fuera del entrenamiento los meses más recientes, y valida sobre un tramo donde la mora cambia casi 3 puntos, mezclando regímenes. Lo reemplacé por **backtesting con ventanas expansivas**: cuatro folds sucesivos, reportando el promedio y por separado el fold más reciente.

**D2. Librería de diagnóstico en el EDA.** La IA propuso usar LightGBM dentro del EDA para las pruebas auxiliares. Lo cambié a `HistGradientBoostingClassifier` de scikit-learn: el EDA no debe depender de la librería del modelo final, y esas pruebas son diagnósticos comparativos donde lo único que importa es usar el mismo modelo a ambos lados de la comparación.

**D3. Análisis de pricing incompleto.** Mi sección original mostraba que la tasa correlaciona −0,56 con el score y +0,21 con el default, y concluía "señal derivada". Razonable pero no demostrado. Agregué dos análisis que cierran el argumento: qué variables mira el motor de pricing (score, uso de línea, consultas y morosidad; **no** monto ni plazo, lo que confirma pricing por riesgo y no por producto), y la prueba decisiva —dentro de cada decil de score, los de tasa alta se moran 1,28× más, en los 10 deciles, pero el AUC del residuo tras remover el score cae de 0,706 a **0,533**. Pasé de una intuición defendible a un número que puedo poner en el informe.

### E · Errores de implementación en gráficos

**E1. Eje temporal estirado desde 1970.** El gráfico de composición etaria aparecía casi vacío, con el eje x extendiéndose desde 1970. La causa: las etiquetas del eje son strings tipo `'2024-01'` que Plotly interpreta como fechas, así que la posición numérica de la línea vertical se leyó como milisegundos desde el epoch. La solución fue declarar el eje como categórico con orden explícito. Lo anoto porque ilustra el punto general: **un gráfico que se ve raro casi nunca es un problema estético**.

---

## Lo que validé manualmente antes de confiar

- **La fuga de información.** No la acepté por el AUC de 0,954. La confirmé por tres vías: la tasa de mora es perfectamente monótona y llega a 100% desde 7 contactos, imposible en una variable disponible al decidir; la distribución en test se corta en 6 mientras en train llega a 12, o sea la cola predictiva no existe en test; y entrenando el mismo modelo con y sin ella sobre el mismo split, el AUC out-of-time pasa de 0,976 a 0,837.

- **La corrección de unidades del ingreso.** No apliqué el ×1000 a ciegas: verifiqué con un Q-Q plot que la distribución corregida se superpone con la del grupo ya expresado en pesos, con menos de 2% de diferencia entre cuantiles homólogos. También confirmé que no existe **ningún** registro en la franja intermedia, lo que descarta que el corte sea arbitrario.

- **El álgebra del umbral óptimo.** Rehíce a mano la derivación de `p* = G/(G+L)` y verifiqué el resultado no trivial de que el monto se cancela. Recalculé los umbrales de la tabla independientemente del código.

- **La salida de `prepare.py`, no solo su lógica.** Sobre la data completa: que no queden nulos, que los valores imputados en test sean exactamente las medianas de train, que `ratio_deuda_ingreso` no produzca infinitos, y que ninguna restricción entre variables quede violada tras limpiar. Este último chequeo reveló el problema C1.

- **Ejecución completa de ambos notebooks desde kernel limpio**, confirmando que reproducen todos los resultados sin estado residual, y que cada cifra citada en el texto coincide con la salida de su celda.

---

## Lo que no delegué

Las decisiones de criterio, en las que la IA aportó opciones y argumentos pero la elección fue mía:

| Decisión | Qué elegí y por qué |
|---|---|
| Excluir la variable con fuga | Cuesta ~0,14 de AUC declarado. Es la decisión más cara en métrica y la que hace creíbles las cifras del informe. |
| Excluir `tasa_interes_anual` | Cuesta 0,0006 de AUC y compra independencia del motor de pricing. Robustez sobre métrica. |
| Aplicar restricciones de monotonía | Acepté un modelo potencialmente peor a cambio de uno defendible ante Riesgo y auditoría. Resultó no costar nada. |
| Incluir el baseline logístico con WOE | Cuesta tiempo en un plazo de 48 horas. Da un piso comparable y el estándar trazable de la banca. |
| **No** ajustar la calibración por deriva | Habría subido la ganancia reportada, pero es una apuesta no validable. Preferí declararla en el informe. |
| Mantener mi estructura del EDA | Rechacé el formato de lista de hallazgos y exigí que se integraran a un relato seguible. |

---

## Reflexión final

La IA aceleró de forma sustancial la exploración y la escritura de código, y produjo hallazgos que yo no había visto —la fuga de información es el más importante de todo el desafío. También produjo, con la misma fluidez y la misma seguridad, conclusiones causales sin medir, un diagnóstico equivocado sobre un segmento de clientes, un criterio inconsistente de selección de variables y una verificación con la herramienta incorrecta.

El patrón que me quedó es que los errores más caros no son los que rompen el código —esos se ven— sino los razonamientos plausibles y bien redactados que nadie pide comprobar. La defensa es exigir el número antes que el argumento, y auditar la salida y no solo la lógica.
