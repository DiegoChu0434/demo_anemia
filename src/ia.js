(function () {
  const D = window.DASHBOARD_DATA;
  const CFG = window.AC_CONFIG || {};

  const cap = (s) => s ? s.charAt(0) + s.slice(1).toLowerCase() : s;
  const pct = (v) => v == null ? "sin dato" : v.toFixed(1) + "%";
  const fmt = (n) => n == null ? "\u2013" : n.toLocaleString("es-PE");
  const ALERTA_LABEL = { verde: "Verde", ambar: "\u00c1mbar", rojo: "Rojo", sin_datos: "Datos insuficientes" };

  const IND_META = {
    ind01: { cod: "IND-01", nom: "continuidad del seguimiento de hemoglobina en gestantes", mejor: "alto", suf: "de gestantes llega al 5\u00ba dosaje", funnel: "gestantes_dosaje", vol: "gestantes" },
    ind02: { cod: "IND-02", nom: "recuperaci\u00f3n de gestantes", mejor: "alto", suf: "de gestantes se recupera", funnel: "gestantes_dosaje", vol: "gestantes" },
    ind03: { cod: "IND-03", nom: "abandono de controles CRED", mejor: "bajo", suf: "abandona los controles CRED", funnel: "cred_mes", vol: "ninos" },
    ind04: { cod: "IND-04", nom: "adherencia a la suplementaci\u00f3n con hierro", mejor: "alto", suf: "mantiene la suplementaci\u00f3n (5\u00aa toma)", funnel: "sup_toma", vol: "ninos" },
    ind05: { cod: "IND-05", nom: "recuperaci\u00f3n de anemia infantil", mejor: "alto", suf: "de los ni\u00f1os se recupera", funnel: "sup_toma", vol: "ninos" },
  };
  const MIN_CASOS = 10;

  function disponible() {
    return !!(CFG.GEMINI_API_KEY && CFG.GEMINI_API_KEY.trim());
  }

  function construirContexto() {
    const provs = D.provincias.map(p => cap(p.Provincia)).join(", ");
    const dists = D.distritos
      .filter(d => (d.ninos || 0) + (d.gestantes || 0) > 0)
      .map(d => `${cap(d.Distrito)} (${cap(d.Provincia)})`).join("; ");
    return [
      "DATOS DISPONIBLES (regi\u00f3n Jun\u00edn, Per\u00fa):",
      `Indicadores globales: IND-01 continuidad Hb gestantes=${D.global.ind01_continuidad_hb}%, ` +
      `IND-02 recuperaci\u00f3n gestantes=${D.global.ind02_recup_gestantes}%, ` +
      `IND-03 abandono CRED=${D.global.ind03_abandono_cred}%, ` +
      `IND-04 adherencia suplementaci\u00f3n=${D.global.ind04_adherencia_sup}%, ` +
      `IND-05 recuperaci\u00f3n ni\u00f1os=${D.global.ind05_recup_ninos}%.`,
      `Provincias: ${provs}.`,
      `Distritos con datos: ${dists}.`,
    ].join("\n");
  }

  const SYSTEM_PROMPT = `Eres el motor de intenci\u00f3n de un dashboard de salud sobre anemia en la regi\u00f3n Jun\u00edn (Per\u00fa).
Interpretas la pregunta del usuario (teniendo en cuenta el historial de la conversaci\u00f3n) y devuelves UN SOLO objeto JSON (sin texto extra, sin markdown) con esta forma exacta:
{
  "accion": "valor" | "ranking" | "alertas" | "resumen" | "ayuda" | "fuera_de_tema",
  "indicador": "ind01" | "ind02" | "ind03" | "ind04" | "ind05" | null,
  "lugar": { "tipo": "distrito" | "provincia" | "global", "nombre": "<NOMBRE EN MAYUSCULAS EXACTO del contexto>" | null, "provincia": "<provincia del distrito en MAYUSCULAS>" | null },
  "nivel": "distritos" | "provincias" | null,
  "metrica": "volumen_gestantes" | "volumen_ninos" | "volumen_cred" | null,
  "orden": "mejor" | "peor" | null,
  "limite": <entero 1-10 | null>,
  "comentario": "<una frase breve y natural en espa\u00f1ol que acompa\u00f1e la respuesta, SIN cifras inventadas>"
}

Definiciones de indicadores:
- ind01: continuidad del seguimiento de hemoglobina en gestantes (llegar al 5\u00ba dosaje). M\u00e1s alto es mejor.
- ind02: recuperaci\u00f3n de gestantes con anemia. M\u00e1s alto es mejor.
- ind03: abandono de controles CRED (ni\u00f1os). M\u00e1s BAJO es mejor (es malo cuando es alto).
- ind04: adherencia a la suplementaci\u00f3n con hierro (5\u00aa toma). M\u00e1s alto es mejor.
- ind05: recuperaci\u00f3n de anemia infantil. M\u00e1s alto es mejor.

Reglas:
- "accion": "valor" cuando preguntan por un indicador en un lugar concreto. "ranking" cuando piden comparar/ordenar lugares (mejor/peor/d\u00f3nde hay m\u00e1s o menos, cu\u00e1l es el mayor/menor). "alertas" cuando preguntan por distritos en rojo/cr\u00edticos/en alerta. "resumen" cuando piden el estado general de un lugar o de la regi\u00f3n. "ayuda" solo para saludos sueltos o "qu\u00e9 puedes hacer". "fuera_de_tema" si no tiene que ver con estos datos de anemia.
- USA EL HISTORIAL para resolver referencias: si el usuario dice "esa", "la primera", "dame solo una", "y en provincias", "y el abandono?", hereda el indicador, lugar o nivel del turno anterior. Nunca respondas "no entend\u00ed": deduce la intenci\u00f3n m\u00e1s probable del contexto.
- "nivel": "provincias" si la pregunta es a nivel provincia, "distritos" si es a nivel distrito; en rankings, por defecto "distritos" salvo que digan "provincia(s)".
- "metrica": usar SOLO cuando el ranking es por CANTIDAD/VOLUMEN de registros, no por un indicador. "cu\u00e1ntas/cantidad/m\u00e1s/menos gestantes" o "mayor cantidad de embarazadas" -> "volumen_gestantes". "cu\u00e1ntos/cantidad/m\u00e1s ni\u00f1os con anemia/casos de anemia" -> "volumen_ninos". "cantidad de controles CRED" -> "volumen_cred". En estos casos accion="ranking", indicador=null y metrica con el valor correspondiente. Si el ranking es por un indicador (recuperaci\u00f3n, abandono, etc.), deja metrica=null.
- "limite": si piden "una", "la que", "el que", "cu\u00e1l es el/la" -> 1. Si piden "top 3", "las 3 peores" -> ese n\u00famero. Si no especifican -> null (se usar\u00e1 5).
- Si no mencionan lugar y no hay contexto, usa lugar.tipo="global".
- "nombre" y "provincia" deben coincidir EXACTAMENTE con un nombre del contexto (en MAYUSCULAS). Si no reconoces el lugar, usa tipo="global".
- "orden": "peor" si piden lo peor/m\u00e1s cr\u00edtico/m\u00e1s abandono/menor recuperaci\u00f3n; "mejor" si piden lo mejor/mayor; null si no aplica.
- El "comentario" NUNCA debe contener porcentajes ni n\u00fameros concretos: esos los pone el sistema. Solo una frase de contexto.
- Responde SOLO el JSON.`;

  function formatearHistorial(historial) {
    if (!Array.isArray(historial) || !historial.length) return "";
    const lineas = historial.map(h => `${h.rol === "usuario" ? "Usuario" : "Asistente"}: ${h.texto}`);
    return "\n\nHISTORIAL DE LA CONVERSACI\u00d3N (del m\u00e1s antiguo al m\u00e1s reciente):\n" + lineas.join("\n");
  }

  async function llamarGemini(pregunta, historial) {
    const model = CFG.GEMINI_MODEL || "gemini-2.0-flash";
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(CFG.GEMINI_API_KEY)}`;
    const body = {
      system_instruction: { parts: [{ text: SYSTEM_PROMPT }] },
      contents: [{ role: "user", parts: [{ text: construirContexto() + formatearHistorial(historial) + "\n\nPregunta actual del usuario: " + pregunta }] }],
      generationConfig: { temperature: 0.1, responseMimeType: "application/json" },
    };
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), CFG.TIMEOUT_MS || 9000);
    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: ctrl.signal,
      });
      clearTimeout(t);
      if (!res.ok) {
        let detalle = "";
        try { detalle = (await res.json())?.error?.message || ""; } catch (e) {}
        throw new Error("HTTP " + res.status + (detalle ? " - " + detalle : ""));
      }
      const data = await res.json();
      if (window.ACUso && data.usageMetadata) window.ACUso.registrar(data.usageMetadata);
      const txt = data?.candidates?.[0]?.content?.parts?.[0]?.text || "";
      return JSON.parse(limpiarJSON(txt));
    } finally {
      clearTimeout(t);
    }
  }

  function limpiarJSON(s) {
    const m = s.match(/\{[\s\S]*\}/);
    return m ? m[0] : s;
  }

  function recGlobal() {
    return {
      ind01: D.global.ind01_continuidad_hb, ind02: D.global.ind02_recup_gestantes,
      ind03: D.global.ind03_abandono_cred, ind04: D.global.ind04_adherencia_sup,
      ind05: D.global.ind05_recup_ninos, alerta: D.global.alerta,
      gestantes: D.meta.registros.gestantes, cred: D.meta.registros.cred, ninos: D.meta.registros.ninos,
    };
  }
  function buscarLugar(lugar) {
    if (!lugar || lugar.tipo === "global" || !lugar.nombre)
      return { tipo: "global", nombre: "Regi\u00f3n Jun\u00edn", rec: recGlobal() };
    const nom = (lugar.nombre || "").toUpperCase();
    if (lugar.tipo === "distrito") {
      const rec = D.distritos.find(d => d.Distrito === nom &&
        (!lugar.provincia || d.Provincia === (lugar.provincia || "").toUpperCase())) ||
        D.distritos.find(d => d.Distrito === nom);
      if (rec) return { tipo: "distrito", nombre: rec.Distrito, prov: rec.Provincia, rec };
    }
    const recp = D.provincias.find(p => p.Provincia === nom);
    if (recp) return { tipo: "provincia", nombre: recp.Provincia, rec: recp };
    return { tipo: "global", nombre: "Regi\u00f3n Jun\u00edn", rec: recGlobal() };
  }

  function comparaGlobal(indKey, v) {
    const g = recGlobal()[indKey];
    const meta = IND_META[indKey];
    if (g == null || v == null) return "";
    const dif = Math.abs(v - g);
    if (dif < 0.1) return " Est\u00e1 en l\u00ednea con el promedio regional.";
    const peor = meta.mejor === "alto" ? v < g : v > g;
    return ` ${peor ? "Por debajo" : "Mejor que"} el promedio regional (${pct(g)}).`;
  }

  function salidaValor(indKey, lugar, comentario) {
    const meta = IND_META[indKey];
    const r = lugar.rec;
    if (!r) return { txt: "No encontr\u00e9 datos para ese lugar.", enfoque: null };
    const v = r[indKey];
    const extra = comentario ? ` <span class="mut">${comentario}</span>` : "";
    if (v == null)
      return {
        txt: `En <b>${cap(lugar.nombre)}</b> no hay dato suficiente para ${meta.nom} (menos de 10 casos).${extra}`,
        enfoque: enfoqueDe(lugar, { kpi: indKey }),
      };
    const txt = `En <b>${cap(lugar.nombre)}</b>, la <b>${meta.nom}</b> (${meta.cod}) es ` +
      `<b class="hi">${pct(v)}</b>. Es decir, ${pct(v)} ${meta.suf}.` +
      comparaGlobal(indKey, v) + extra;
    return { txt, enfoque: enfoqueDe(lugar, { kpi: indKey, funnel: meta.funnel }) };
  }

  function salidaRanking(indKey, orden, comentario, nivel, limite) {
    const meta = IND_META[indKey];
    const campoVol = meta.vol;
    const esProv = nivel === "provincias";
    const fuente = esProv ? D.provincias : D.distritos;
    const n = Math.min(10, Math.max(1, limite || 5));
    let arr = fuente.filter(x => x[indKey] != null && (x[campoVol] || 0) >= MIN_CASOS);
    const peor = orden === "peor" || (orden == null && meta.mejor === "bajo");
    let asc;
    if (meta.mejor === "alto") asc = peor; else asc = !peor;
    arr = arr.slice().sort((a, b) => asc ? a[indKey] - b[indKey] : b[indKey] - a[indKey]);
    const top = arr.slice(0, n);
    const ambLab = esProv ? "provincias" : "distritos";
    if (!top.length) return { txt: `No hay ${ambLab} con al menos ${MIN_CASOS} casos para rankear ${meta.nom}.`, enfoque: null };
    const volLab = (indKey === "ind01" || indKey === "ind02") ? "gestantes" : "ni\u00f1os";
    const filas = top.map((x, i) => {
      const nm = cap(esProv ? x.Provincia : x.Distrito);
      const sub = esProv ? "" : ` <span class="mut">(${cap(x.Provincia)})</span>`;
      const idx = n === 1 ? "" : `${i + 1}. `;
      return `${idx}${qlink("Resumen de " + nm)}${sub} \u2014 ${pct(x[indKey])} <span class="mut">\u00b7 ${fmt(x[campoVol])} ${volLab}</span>`;
    }).join("<br>");
    const first = top[0];
    const enfoque = { kpi: indKey, funnel: meta.funnel };
    if (esProv) { enfoque.prov = first.Provincia; enfoque.dist = ""; }
    else { enfoque.prov = first.Provincia; enfoque.dist = first.Distrito; }
    const etiqueta = peor ? "con peor" : "con mejor";
    const extra = comentario ? `${comentario}<br><br>` : "";
    if (n === 1) {
      const titulo = esProv ? "La provincia" : "El distrito";
      return {
        txt: `${extra}${titulo} ${etiqueta.replace("con ", "")} <b>${meta.nom}</b> (${meta.cod}) es:<br><br>${filas}<br><br>` +
          `<span class="mut">Entre \u00e1mbitos con \u2265 ${MIN_CASOS} ${volLab}. Lo enfoqu\u00e9 en el tablero.</span>`,
        enfoque,
      };
    }
    const titulo = esProv ? "Provincias" : "Distritos";
    return {
      txt: `${extra}${titulo} ${etiqueta} <b>${meta.nom}</b> (${meta.cod}):<br><br>${filas}<br><br>` +
        `<span class="mut">Solo \u00e1mbitos con \u2265 ${MIN_CASOS} ${volLab}. Enfoqu\u00e9 el primero en el tablero.</span>`,
      enfoque,
    };
  }

  const VOL_META = {
    volumen_gestantes: { campo: "gestantes", lab: "gestantes con anemia", kpi: "ind02", funnel: "gestantes_dosaje" },
    volumen_ninos: { campo: "ninos", lab: "ni\u00f1os con anemia", kpi: "ind05", funnel: "sup_toma" },
    volumen_cred: { campo: "cred", lab: "controles CRED", kpi: "ind03", funnel: "cred_mes" },
  };

  function salidaRankingVolumen(metrica, orden, comentario, nivel, limite) {
    const meta = VOL_META[metrica];
    if (!meta) return null;
    const esProv = nivel === "provincias";
    const fuente = esProv ? D.provincias : D.distritos;
    const n = Math.min(10, Math.max(1, limite || 5));
    const menor = orden === "peor" || orden === "menor";
    let arr = fuente.filter(x => (x[meta.campo] || 0) > 0)
      .slice().sort((a, b) => menor ? a[meta.campo] - b[meta.campo] : b[meta.campo] - a[meta.campo]);
    const top = arr.slice(0, n);
    const ambLab = esProv ? "provincias" : "distritos";
    if (!top.length) return { txt: `No hay ${ambLab} con registros de ${meta.lab}.`, enfoque: null };
    const filas = top.map((x, i) => {
      const nm = cap(esProv ? x.Provincia : x.Distrito);
      const sub = esProv ? "" : ` <span class="mut">(${cap(x.Provincia)})</span>`;
      const idx = n === 1 ? "" : `${i + 1}. `;
      return `${idx}${qlink("Resumen de " + nm)}${sub} \u2014 <b>${fmt(x[meta.campo])}</b> ${meta.lab}`;
    }).join("<br>");
    const first = top[0];
    const enfoque = { kpi: meta.kpi, funnel: meta.funnel };
    if (esProv) { enfoque.prov = first.Provincia; enfoque.dist = ""; }
    else { enfoque.prov = first.Provincia; enfoque.dist = first.Distrito; }
    const extra = comentario ? `${comentario}<br><br>` : "";
    const dir = menor ? "menor" : "mayor";
    const titulo = esProv ? "Provincias" : "Distritos";
    if (n === 1) {
      const t = esProv ? "La provincia" : "El distrito";
      return { txt: `${extra}${t} con ${dir} cantidad de <b>${meta.lab}</b> es:<br><br>${filas}<br><br><span class="mut">Lo enfoqu\u00e9 en el tablero.</span>`, enfoque };
    }
    return { txt: `${extra}${titulo} con ${dir} cantidad de <b>${meta.lab}</b>:<br><br>${filas}<br><br><span class="mut">Enfoqu\u00e9 el primero en el tablero.</span>`, enfoque };
  }

  function salidaAlertas(comentario) {
    const rojos = D.distritos.filter(x => x.alerta === "rojo");
    if (!rojos.length) return { txt: "No hay distritos en nivel <b>rojo</b> actualmente.", enfoque: null };
    rojos.sort((a, b) => (a.ind05 ?? 999) - (b.ind05 ?? 999));
    const filas = rojos.slice(0, 10).map(x =>
      `<span class="pill rojo">Rojo</span> ${qlink("Resumen de " + cap(x.Distrito))} <span class="mut">(${cap(x.Provincia)})</span> \u2014 recuperaci\u00f3n ${pct(x.ind05)}, abandono CRED ${pct(x.ind03)}`
    ).join("<br>");
    const extra = comentario ? `${comentario}<br><br>` : "";
    return {
      txt: `${extra}Hay <b>${rojos.length}</b> distritos en nivel rojo (recuperaci\u00f3n < 30% o abandono CRED > 50%):<br><br>${filas}`,
      enfoque: { prov: "", dist: "", tablaRojos: true },
    };
  }

  function salidaResumen(lugar, comentario) {
    const r = lugar.rec;
    if (!r) return { txt: "No encontr\u00e9 ese lugar.", enfoque: null };
    const al = ALERTA_LABEL[r.alerta] || r.alerta;
    const extra = comentario ? `<span class="mut">${comentario}</span><br><br>` : "";
    const txt = `<b>${cap(lugar.nombre)}</b> \u2014 nivel de alerta <span class="pill ${r.alerta}">${al}</span><br><br>${extra}` +
      `\u2022 Recuperaci\u00f3n anemia infantil (IND-05): <b>${pct(r.ind05)}</b><br>` +
      `\u2022 Abandono CRED (IND-03): <b>${pct(r.ind03)}</b><br>` +
      `\u2022 Adherencia suplementaci\u00f3n (IND-04): <b>${pct(r.ind04)}</b><br>` +
      `\u2022 Continuidad Hb gestantes (IND-01): <b>${pct(r.ind01)}</b><br>` +
      `\u2022 Recuperaci\u00f3n gestantes (IND-02): <b>${pct(r.ind02)}</b><br><br>` +
      `<span class="mut">Registros: ${fmt(r.gestantes)} gestantes \u00b7 ${fmt(r.cred)} CRED \u00b7 ${fmt(r.ninos)} ni\u00f1os con anemia.</span>`;
    return { txt, enfoque: enfoqueDe(lugar, {}) };
  }

  function enfoqueDe(lugar, base) {
    const e = Object.assign({}, base);
    if (lugar.tipo === "distrito") { e.prov = lugar.prov; e.dist = lugar.nombre; }
    else if (lugar.tipo === "provincia") { e.prov = lugar.nombre; e.dist = ""; }
    else { e.prov = ""; e.dist = ""; }
    return e;
  }

  function qlink(q) {
    return `<a class="qlink" data-q="${q.replace(/"/g, "&quot;")}">${q}</a>`;
  }

  function resolver(intent) {
    if (!intent || typeof intent !== "object") return null;
    const comentario = (intent.comentario || "").trim();
    const lugar = buscarLugar(intent.lugar);
    const ind = IND_META[intent.indicador] ? intent.indicador : null;

    switch (intent.accion) {
      case "valor":
        if (ind) return salidaValor(ind, lugar, comentario);
        return salidaResumen(lugar, comentario);
      case "ranking":
        if (VOL_META[intent.metrica]) return salidaRankingVolumen(intent.metrica, intent.orden, comentario, intent.nivel, intent.limite);
        if (ind) return salidaRanking(ind, intent.orden, comentario, intent.nivel, intent.limite);
        return salidaAlertas(comentario);
      case "alertas":
        return salidaAlertas(comentario);
      case "resumen":
        return salidaResumen(lugar, comentario);
      case "ayuda":
        return null;
      case "fuera_de_tema":
        return {
          txt: comentario || "Solo puedo responder sobre los datos de anemia de la DIRESA Jun\u00edn (recuperaci\u00f3n, abandono CRED, adherencia, continuidad Hb, alertas por distrito).",
          enfoque: null,
        };
      default:
        return null;
    }
  }

  async function responder(pregunta, historial) {
    if (!disponible() || !D) return null;
    try {
      const intent = await llamarGemini(pregunta, historial);
      return resolver(intent);
    } catch (e) {
      console.warn("[ACIA] fallo IA, uso motor de reglas:", e.message);
      return null;
    }
  }

  window.ACIA = { disponible, responder };
})();
