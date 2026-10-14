/* AnemiaCero Junin - Plantilla de configuracion de la IA (Google Gemini)
   -----------------------------------------------------------------------
   COPIA este archivo como  src/config.js  y pega tu clave.
   src/config.js esta en .gitignore: tu clave NUNCA se sube al repositorio.

   COMO OBTENER TU API KEY GRATUITA (no requiere tarjeta):
     1. Entra a  https://aistudio.google.com/apikey
     2. Inicia sesion con tu cuenta Google.
     3. Clic en "Create API key" y copia la clave.
     4. Pegala abajo entre las comillas de GEMINI_API_KEY (en tu src/config.js).

   NOTAS:
   - Si dejas la key vacia, el asistente funciona igual con el motor de
     reglas local (sin IA). La IA es una mejora opcional.
   - Esta es una demo academica: la key queda visible en el navegador.
     No uses una key de produccion aqui. Para publicar, protegela detras
     de un backend o funcion serverless.
*/
window.AC_CONFIG = {
  // Pega aqui tu clave de Google AI Studio:
  GEMINI_API_KEY: "",

  // Modelo gratuito y rapido del free tier. Puedes cambiarlo si quieres.
  GEMINI_MODEL: "gemini-2.0-flash",

  // Milisegundos antes de abandonar la llamada y caer al motor de reglas.
  TIMEOUT_MS: 9000,
};
