# AnemiaCero Junín — Demo del Monitor de Seguimiento Integrado

Demo funcional basada en el **Informe Final** y los tres datasets abiertos de la DIRESA Junín
(gestantes con anemia, controles CRED, niños menores de 36 meses con anemia).

Reproduce el flujo descrito en el informe: **ETL → indicadores analíticos → dashboard**.

## Contenido

### Estructura del proyecto

```
demo_anemia/
├── index.html                  # Página del dashboard (punto de entrada)
├── README.md
├── .gitignore                  # Protege src/config.js y temporales
├── Informe_Final.docx          # Documento de referencia
│
├── data/                       # Datos
│   ├── dashboard_data.json     #   Resultado del ETL (legible)
│   ├── data.js                 #   Mismos datos como variable JS (abrir sin servidor)
│   └── raw/                    #   Los 3 CSV crudos de la DIRESA Junín
│
├── etl/
│   └── etl_indicadores.py      # ETL: limpia los CSV y calcula los indicadores
│
└── src/                        # Código del front
    ├── app.js                  #   Lógica del dashboard
    ├── asistente.js            #   Chat: interpreta la pregunta y dispara el tablero
    ├── ia.js                   #   Capa de IA (Gemini): intención en lenguaje natural
    ├── uso.js                  #   Contador de consumo de la IA (llamadas y tokens)
    ├── panel-uso.js            #   Panel lateral de límites y consumo de la IA
    ├── config.example.js       #   Plantilla de configuración (SIN key, sí va a git)
    └── config.js               #   Tu config con la API key (NO va a git)
```

| Pieza | Qué es |
|---|---|
| `etl/etl_indicadores.py` | Proceso ETL en Python: limpia los 3 CSV de `data/raw/`, estandariza (NULL→null, fechas ISO, severidad LEV/MOD/SEV, deduplicación) y calcula los 7 indicadores (IND-01 a IND-07) y el embudo, agregados por provincia y distrito. Escribe en `data/`. |
| `data/dashboard_data.json` | Resultado del ETL (datos legibles). |
| `data/data.js` | Los mismos datos embebidos como variable JS (permite abrir el dashboard sin servidor). |
| `index.html` | Dashboard web: KPIs, embudo de seguimiento, filtros en cascada, distribución por severidad, tabla de distritos con semáforo de alertas. |
| `src/app.js` | Lógica del dashboard. |
| `src/asistente.js` | Asistente de consulta: interpreta la pregunta (con IA si hay key, o con el motor de reglas local) y dispara el dashboard con los datos reales del ETL. |
| `src/ia.js` | Capa de IA (Google Gemini): interpreta preguntas en lenguaje natural libre y las convierte en una intención estructurada. Las cifras siempre salen del JSON, no las inventa el modelo. Si falla o no hay key, cae al motor de reglas. |
| `src/modelo.js` | Al hacer clic en un dataset del sidebar, muestra su estructura en tercera forma normal (3FN) según el informe (tablas de hecho, dimensiones, PK/FK). |
| `src/exportar.js` | Menú *Consultas* (lista de preguntas hechas, clic para repetir) y menú *Exportar* (genera un Excel .xlsx con el estado actual del dashboard: resumen, distritos, embudo y severidad). |
| `src/config.example.js` | Plantilla de configuración de la IA (sin key). **Esta sí se sube al repo.** |
| `src/config.js` | Tu configuración real con la API key. **Ignorada por git** (`.gitignore`). |

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

## IA opcional (Google Gemini)

El asistente puede usar una **IA gratuita** para entender preguntas en lenguaje natural libre
(no solo las frases pre-armadas del motor de reglas). Funciona así:

1. Tu pregunta se envía a **Gemini**, que la interpreta y decide *qué* indicador, lugar y tipo de
   respuesta corresponde (devuelve una intención estructurada).
2. El dashboard arma la respuesta con las **cifras reales del JSON**. La IA nunca inventa números:
   solo interpreta la pregunta y redacta una frase de contexto.
3. Si no hay internet, falla la API o no configuraste la key, el asistente **cae automáticamente**
   al motor de reglas local. Nada se rompe.

### Configurar la API key (gratis, sin tarjeta)

1. Entra a **https://aistudio.google.com/apikey** e inicia sesión con tu cuenta Google.
2. Clic en **Create API key** y copia la clave.
3. Copia **`src/config.example.js`** como **`src/config.js`** y pega tu clave en `GEMINI_API_KEY`:

   ```js
   window.AC_CONFIG = {
     GEMINI_API_KEY: "TU_CLAVE_AQUI",
     GEMINI_MODEL: "gemini-2.0-flash",
     TIMEOUT_MS: 9000,
   };
   ```

4. Recarga `index.html`. Ya puedes preguntar en lenguaje natural libre, por ejemplo:
   *«¿en qué distrito de Satipo se recuperan menos niños?»* o *«compárame la adherencia entre Huancayo y Jauja»*.

> **Seguridad:** `src/config.js` está en `.gitignore`, así que tu clave **nunca se sube al repositorio**.
> La plantilla `src/config.example.js` (sin clave) sí se versiona, para que otros sepan qué configurar.
> Como es una demo que corre en el navegador, la clave queda visible en el cliente: no uses una key sensible.
> Para publicar en producción, protege la clave detrás de un backend o función serverless.

## Consultas y exportación

En la barra superior:

- **Consultas**: abre la lista de todas las preguntas que has hecho en la sesión. Al hacer clic en una,
  se vuelve a ejecutar y el dashboard regresa a ese estado.
- **Exportar**: genera un archivo **Excel (.xlsx)** con lo que estás viendo en ese momento (según el
  ámbito y los filtros actuales). Incluye cuatro hojas: *Resumen* (ámbito, 5 indicadores, alerta y
  volumen), *Distritos* (la tabla con autofiltro), *Embudo* y *Severidad*. Usa la librería SheetJS
  cargada desde CDN, por lo que la primera exportación requiere conexión a internet.

> Nota: la versión gratuita de SheetJS exporta estructura, varias hojas, anchos de columna y autofiltro,
> pero no colores de celda (eso solo está en su edición de pago). El semáforo se incluye como texto
> en la columna *Alerta*.

## Cómo ejecutar

### 1. (Opcional) Regenerar los datos desde los CSV
Requiere Python con `pandas`. Desde la raíz del proyecto:

```
python etl/etl_indicadores.py
```

Lee los CSV de `data/raw/`, valida los conteos y regenera
`data/dashboard_data.json` y `data/data.js`.

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
