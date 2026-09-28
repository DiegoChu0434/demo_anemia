# AnemiaCero Junín — Demo del Monitor de Seguimiento Integrado

Demo funcional basada en el **Informe Final** y los tres datasets abiertos de la DIRESA Junín
(gestantes con anemia, controles CRED, niños menores de 36 meses con anemia).

Reproduce el flujo descrito en el informe: **ETL → indicadores analíticos → dashboard**.

## Contenido

| Archivo | Qué es |
|---|---|
| `etl_indicadores.py` | Proceso ETL en Python: limpia los 3 CSV, estandariza (NULL→null, fechas ISO, severidad LEV/MOD/SEV, deduplicación) y calcula los 7 indicadores (IND-01 a IND-07) y el embudo, agregados por provincia y distrito. |
| `dashboard_data.json` | Resultado del ETL (datos legibles). |
| `data.js` | Los mismos datos embebidos como variable JS (permite abrir el dashboard sin servidor). |
| `index.html` | Dashboard web: KPIs, embudo de seguimiento, filtros en cascada, distribución por severidad, tabla de distritos con semáforo de alertas. |
| `app.js` | Lógica del dashboard. |
| `asistente.js` | Asistente de consulta local: responde preguntas en lenguaje natural usando los datos reales del ETL (sin internet ni API externa). |

## Experiencia (flujo conversacional)

La aplicación **arranca con el asistente centrado** (pantalla de bienvenida). Al hacer la primera
pregunta, se produce una **transición profesional**: el asistente se desplaza a la izquierda como
panel de conversación y el **dashboard aparece a la derecha**, mostrando los datos según la pregunta.
Cada nueva consulta actualiza el tablero y **resalta** el indicador, el embudo o la tabla relevante.

## Asistente de consulta

El asistente entiende preguntas escritas y responde con los datos reales. Funciona 100% local
(motor de intención sobre el JSON, sin LLM ni conexión). Ejemplos que reconoce:

- «¿Cuál es la recuperación en Huancayo?» → valor puntual del indicador en ese lugar
- «¿Qué distritos están en rojo?» → lista de ámbitos en alerta crítica
- «¿Dónde hay más abandono de CRED?» → ranking (filtra ámbitos con < 10 casos)
- «Resumen de la provincia de Satipo» → ficha con los 5 indicadores y el semáforo

Al mencionar un distrito o provincia, el asistente **sincroniza los filtros** del dashboard automáticamente.

## Cómo ejecutar

### 1. (Opcional) Regenerar los datos desde los CSV
Requiere Python con `pandas`. Desde esta carpeta:

```
python etl_indicadores.py
```

Lee los CSV que están en la carpeta superior (`..`), valida los conteos y regenera
`dashboard_data.json` y `data.js`.

### 2. Ver el dashboard
Abre **`index.html`** con doble clic (funciona directamente en el navegador, sin servidor).

> Si prefieres servirlo por HTTP:
> ```
> python -m http.server 8000
> ```
> y entra a http://localhost:8000

## Indicadores (definiciones del Informe, sección 3.4)

- **IND-01** Continuidad del seguimiento de Hb en gestantes (llegan al 5° dosaje) → **5.8%**
- **IND-02** Tasa de recuperación de gestantes → **17.8%**
- **IND-03** Tasa de abandono de controles CRED (mes 1 → mes 11) → **39.6%**
- **IND-04** Adherencia a la suplementación con hierro (5ª toma) → **41.0%**
- **IND-05** Tasa de recuperación de anemia infantil → **47.0%** *(post-deduplicación; el informe reporta 46.9% pre-ETL)*
- **IND-06** Índice de retención del embudo (las tres series que dibuja el gráfico)
- **IND-07** Nivel de alerta (semáforo): rojo si recuperación < 30% o abandono CRED > 50%; ámbar en rangos intermedios; solo se evalúa con ≥ 10 casos.

## Notas

- El cruce entre datasets es **geográfico-institucional** (provincia/distrito), como indica el informe,
  porque los identificadores de persona están enmascarados.
- Las cifras son **de elaboración propia** a partir de los datos abiertos; es una demo académica,
  no un sistema en producción.
