// Netlify Function: intermediario seguro con Google Gemini.
// La API key vive aqui como variable de entorno (GEMINI_API_KEY) y NUNCA
// se envia al navegador. El front llama a /api/gemini con el cuerpo de la
// peticion ya armado (system_instruction, contents, generationConfig).
exports.handler = async (event) => {
  const CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Content-Type": "application/json",
  };

  if (event.httpMethod === "OPTIONS") {
    return { statusCode: 204, headers: CORS, body: "" };
  }
  if (event.httpMethod !== "POST") {
    return { statusCode: 405, headers: CORS, body: JSON.stringify({ error: { message: "Metodo no permitido" } }) };
  }

  const KEY = process.env.GEMINI_API_KEY;
  if (!KEY) {
    return { statusCode: 500, headers: CORS, body: JSON.stringify({ error: { message: "Falta GEMINI_API_KEY en el entorno de Netlify" } }) };
  }

  const model = process.env.GEMINI_MODEL || "gemini-flash-latest";
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(KEY)}`;

  try {
    const payload = JSON.parse(event.body || "{}");
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const text = await res.text();
    return { statusCode: res.status, headers: CORS, body: text };
  } catch (e) {
    return { statusCode: 502, headers: CORS, body: JSON.stringify({ error: { message: "Error al contactar Gemini: " + e.message } }) };
  }
};
