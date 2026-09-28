/* AnemiaCero Junin - Asistente local (Opcion A)
   Responde preguntas en lenguaje natural consultando window.DASHBOARD_DATA.
   No usa internet ni LLM externo: motor de intencion + datos reales del ETL. */
(function () {
  const D = window.DASHBOARD_DATA;
  if (!D) return;

  // ---------------- utilidades de texto ----------------
  const norm = (s) => (s || "").toString().toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")   // quita tildes
    .replace(/[^a-z0-9\s]/g, " ").replace(/\s+/g, " ").trim();

  const cap = (s) => s ? s.charAt(0) + s.slice(1).toLowerCase() : s;
  const pct = (v) => v == null ? "sin dato" : v.toFixed(1) + "%";
  const fmt = (n) => n == null ? "–" : n.toLocaleString("es-PE");

  // catalogo de nombres geograficos (para reconocerlos en la pregunta)
  const PROVS = D.provincias.map(p => ({ raw: p.Provincia, n: norm(p.Provincia) }));
  const DISTS = D.distritos.map(d => ({ raw: d.Distrito, n: norm(d.Distrito), prov: d.Provincia }));

  // definicion de indicadores: sinonimos + campo + sentido (mayor/menor mejor)
  const INDS = [
    { key:"ind05", cod:"IND-05", nom:"recuperación de anemia infantil", campo:"ind05",
      kw:["recuperacion", "recuperados", "recupera", "recuperan", "recuperado", "cura", "curan"], mejor:"alto", suf:"de los niños se recupera" },
    { key:"ind03", cod:"IND-03", nom:"abandono de controles CRED", campo:"ind03",
      kw:["abandono", "abandonan", "desercion", "desertan", "cred", "control", "controles"], mejor:"bajo", suf:"abandona los controles CRED" },
    { key:"ind04", cod:"IND-04", nom:"adherencia a la suplementación con hierro", campo:"ind04",
      kw:["adherencia", "suplementacion", "suplemento", "hierro", "toma", "tomas"], mejor:"alto", suf:"mantiene la suplementación (5ª toma)" },
    { key:"ind01", cod:"IND-01", nom:"continuidad del seguimiento de hemoglobina en gestantes", campo:"ind01",
      kw:["continuidad", "hemoglobina", "dosaje", "dosajes", "seguimiento gestante"], mejor:"alto", suf:"de gestantes llega al 5º dosaje" },
    { key:"ind02", cod:"IND-02", nom:"recuperación de gestantes", campo:"ind02",
      kw:["recuperacion gestante", "gestantes recuperadas", "recupera gestante"], mejor:"alto", suf:"de gestantes se recupera" },
  ];

  // ---------------- deteccion ----------------
  function detectarLugar(q) {
    // distrito primero (mas especifico)
    for (const d of DISTS) if (d.n && q.includes(d.n)) {
      const rec = D.distritos.find(x => x.Distrito === d.raw && x.Provincia === d.prov);
      return { tipo:"distrito", nombre:d.raw, prov:d.prov, rec };
    }
    for (const p of PROVS) if (p.n && q.includes(p.n)) {
      const rec = D.provincias.find(x => x.Provincia === p.raw);
      return { tipo:"provincia", nombre:p.raw, rec };
    }
    return { tipo:"global", nombre:"Región Junín", rec:globalRec() };
  }
  function globalRec() {
    return { ind01:D.global.ind01_continuidad_hb, ind02:D.global.ind02_recup_gestantes,
             ind03:D.global.ind03_abandono_cred, ind04:D.global.ind04_adherencia_sup,
             ind05:D.global.ind05_recup_ninos, alerta:D.global.alerta,
             gestantes:D.meta.registros.gestantes, cred:D.meta.registros.cred, ninos:D.meta.registros.ninos };
  }
  function detectarIndicador(q) {
    let best = null, score = 0;
    for (const ind of INDS) {
      let s = 0;
      for (const k of ind.kw) if (q.includes(k)) s += k.split(" ").length;
      if (s > score) { score = s; best = ind; }
    }
    return best;
  }
  const ALERTA_LABEL = { verde:"Verde", ambar:"Ámbar", rojo:"Rojo", sin_datos:"Datos insuficientes" };

  // ---------------- generacion de respuesta ----------------
  function responder(pregunta) {
    const q = norm(pregunta);

    // 1) saludos / ayuda
    if (/\b(hola|buenas|ayuda|que puedes|puedes hacer|ejemplos)\b/.test(q))
      return { txt: ayudaTxt(), foco:null };

    const ind = detectarIndicador(q);
    const esRanking = /\b(mejor|mejores|peor|peores|mas|menos|mayor|menor|top|ranking|cuales|que distrito|que provincia|donde)\b/.test(q);

    // 2) ranking por indicador (tiene prioridad si hay un indicador + palabra de orden)
    if (ind && esRanking) return ranking(q, ind);

    // 3) alertas / semaforo (rojos, criticos) — cuando NO se pide un indicador puntual
    if (/\b(rojo|rojos|critico|criticos|alerta|alertas|prioridad|prioritario)\b/.test(q)
        || (/\b(peor|peores)\b/.test(q) && !ind))
      return rankingAlerta(q);

    // 4) valor puntual de un lugar (con indicador)
    const lugar = detectarLugar(q);
    if (ind) return valorIndicadorLugar(ind, lugar);

    // 5) resumen de un lugar (sin indicador claro)
    if (lugar.tipo !== "global" || /\b(resumen|general|region|junin|como esta|estado|situacion|todo)\b/.test(q))
      return resumenLugar(lugar);

    // 6) fallback
    return { txt:"No estoy seguro de qué indicador quieres. Prueba con: <i>«recuperación en Huancayo»</i>, <i>«distritos en rojo»</i> o <i>«peor abandono CRED»</i>.", foco:null };
  }

  // que embudo mostrar segun el indicador consultado
  const FUNNEL_DE = { ind01:"gestantes_dosaje", ind02:"gestantes_dosaje",
                      ind03:"cred_mes", ind04:"sup_toma", ind05:"sup_toma" };

  function valorIndicadorLugar(ind, lugar) {
    const r = lugar.rec;
    if (!r) return { txt:"No encontré datos para ese lugar.", foco:null };
    const v = r[ind.campo];
    if (v == null)
      return { txt:`En <b>${cap(lugar.nombre)}</b> no hay dato suficiente para ${ind.nom} (menos de 10 casos).`,
               foco:lugar, enfoque:{ kpi:ind.key } };
    const txt = `En <b>${cap(lugar.nombre)}</b>, la <b>${ind.nom}</b> (${ind.cod}) es <b class="hi">${pct(v)}</b>. ` +
      `Es decir, ${pct(v)} ${ind.suf}.` + comparaGlobal(ind, v);
    return { txt, foco:lugar, enfoque:{ kpi:ind.key, funnel:FUNNEL_DE[ind.key] } };
  }
  function comparaGlobal(ind, v) {
    const g = globalRec()[ind.campo];
    if (g == null || v == null) return "";
    const dif = (v - g).toFixed(1);
    if (Math.abs(dif) < 0.1) return " Está en línea con el promedio regional.";
    const peor = ind.mejor === "alto" ? v < g : v > g;
    return ` ${peor ? "Por debajo" : "Mejor que"} el promedio regional (${pct(g)}).`;
  }

  const MIN_CASOS = 10; // mismo criterio que el semaforo: evita rankings con 1-2 casos
  function ranking(q, ind) {
    const nivel = /provincia/.test(q) ? "provincias" : "distritos";
    // para indicadores de ninos exige minimo de ninos; para gestantes minimo de gestantes
    const campoVol = (ind.key === "ind01" || ind.key === "ind02") ? "gestantes" : "ninos";
    let arr = D[nivel].filter(x => x[ind.campo] != null && (x[campoVol] || 0) >= MIN_CASOS);
    const peor = /\b(peor|peores|mas abandono|mayor abandono|menos|menor)\b/.test(q) || (ind.mejor === "bajo" && !/\b(mejor|mejores|menos abandono|menor abandono)\b/.test(q));
    // "peor" = malo. Para recuperacion/adherencia malo=bajo; para abandono malo=alto.
    let asc;
    if (ind.mejor === "alto") asc = peor;        // peor recuperacion -> menor valor -> ascendente
    else asc = !peor;                            // peor abandono -> mayor valor -> descendente
    arr = arr.slice().sort((a,b) => asc ? a[ind.campo]-b[ind.campo] : b[ind.campo]-a[ind.campo]);
    const top = arr.slice(0, 5);
    const etiqueta = peor ? "con peor" : "con mejor";
    if (!top.length) return { txt:`No hay ${nivel} con al menos ${MIN_CASOS} casos para rankear ${ind.nom}.`, foco:null };
    const volLab = (ind.key === "ind01" || ind.key === "ind02") ? "gestantes" : "niños";
    const volCampo = (ind.key === "ind01" || ind.key === "ind02") ? "gestantes" : "ninos";
    const filas = top.map((x,i) => {
      const nm = cap(x.Distrito || x.Provincia);
      return `${i+1}. ${qlink("Resumen de " + nm)}${x.Distrito?` <span class="mut">(${cap(x.Provincia)})</span>`:""} — ${pct(x[ind.campo])} <span class="mut">· ${fmt(x[volCampo])} ${volLab}</span>`;
    }).join("<br>");
    // enfocar el primero del ranking en el dashboard
    const first = top[0];
    const enfoque = { kpi:ind.key, funnel:FUNNEL_DE[ind.key] };
    if (first.Distrito) { enfoque.prov = first.Provincia; enfoque.dist = first.Distrito; }
    else if (first.Provincia) { enfoque.prov = first.Provincia; enfoque.dist = ""; }
    return { txt:`${nivel==="provincias"?"Provincias":"Distritos"} ${etiqueta} <b>${ind.nom}</b> (${ind.cod}):<br><br>${filas}<br><br><span class="mut">Se consideran solo ámbitos con ≥ ${MIN_CASOS} ${volLab} para evitar porcentajes inestables. Enfoqué el primero en el tablero.</span>`, foco:null, enfoque };
  }

  function rankingAlerta(q) {
    const nivel = /provincia/.test(q) ? "provincias" : "distritos";
    const rojos = D[nivel].filter(x => x.alerta === "rojo");
    if (!rojos.length) return { txt:`No hay ${nivel} en nivel <b>rojo</b> actualmente.`, foco:null };
    rojos.sort((a,b) => (a.ind05??999) - (b.ind05??999));
    const filas = rojos.slice(0,10).map(x => {
      const nm = cap(x.Distrito || x.Provincia);
      return `<span class="pill rojo">Rojo</span> ${qlink("Resumen de " + nm)}${x.Distrito?` <span class="mut">(${cap(x.Provincia)})</span>`:""} — recuperación ${pct(x.ind05)}, abandono CRED ${pct(x.ind03)}`;
    }).join("<br>");
    return { txt:`Hay <b>${rojos.length}</b> ${nivel} en nivel rojo (recuperación < 30% o abandono CRED > 50%):<br><br>${filas}`, foco:null, enfoque:{ prov:"", dist:"", tablaRojos:true } };
  }

  function resumenLugar(lugar) {
    const r = lugar.rec; if (!r) return { txt:"No encontré ese lugar.", foco:null };
    const al = ALERTA_LABEL[r.alerta] || r.alerta;
    const txt = `<b>${cap(lugar.nombre)}</b> — nivel de alerta <span class="pill ${r.alerta}">${al}</span><br><br>` +
      `• Recuperación anemia infantil (IND-05): <b>${pct(r.ind05)}</b><br>` +
      `• Abandono CRED (IND-03): <b>${pct(r.ind03)}</b><br>` +
      `• Adherencia suplementación (IND-04): <b>${pct(r.ind04)}</b><br>` +
      `• Continuidad Hb gestantes (IND-01): <b>${pct(r.ind01)}</b><br>` +
      `• Recuperación gestantes (IND-02): <b>${pct(r.ind02)}</b><br><br>` +
      `<span class="mut">Registros: ${fmt(r.gestantes)} gestantes · ${fmt(r.cred)} CRED · ${fmt(r.ninos)} niños con anemia.</span>`;
    const enfoque = {};
    if (lugar.tipo === "distrito") { enfoque.prov = lugar.prov; enfoque.dist = lugar.nombre; }
    else if (lugar.tipo === "provincia") { enfoque.prov = lugar.nombre; enfoque.dist = ""; }
    else { enfoque.prov = ""; enfoque.dist = ""; }
    return { txt, foco:lugar, enfoque };
  }

  function qlink(q) {
    return `<a class="qlink" data-q="${q.replace(/"/g,'&quot;')}">${q}</a>`;
  }
  function ayudaTxt() {
    return `Soy el asistente de <b>AnemiaCero Junín</b>. Respondo con los datos reales del sistema. ` +
      `Toca una pregunta para consultarla:<br><br>` +
      `• ${qlink("¿Cuál es la recuperación en Huancayo?")}<br>` +
      `• ${qlink("¿Qué distritos están en rojo?")}<br>` +
      `• ${qlink("¿Dónde hay más abandono de CRED?")}<br>` +
      `• ${qlink("Distritos con mejor adherencia a la suplementación")}<br>` +
      `• ${qlink("Resumen de la provincia de Satipo")}`;
  }

  // ---------------- Sidebar (conteos + historial) ----------------
  function initSidebar() {
    const r = D.meta.registros;
    const setTxt = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = fmt(v); };
    setTxt("cGest", r.gestantes); setTxt("cCred", r.cred); setTxt("cNin", r.ninos);
  }
  const historial = [];
  function pushHistorial(q) {
    historial.unshift(q);
    const cont = document.getElementById("historial");
    if (!cont) return;
    cont.innerHTML = historial.slice(0, 12).map(h =>
      `<div class="hist-item" title="${h.replace(/"/g,'&quot;')}">› ${h}</div>`).join("");
    cont.querySelectorAll(".hist-item").forEach((el, i) =>
      el.addEventListener("click", () => enviar(historial[i])));
  }

  // ---------------- UI ----------------
  const app = document.getElementById("app");
  const log = document.getElementById("chatLog");
  const input = document.getElementById("chatInput");
  const send = document.getElementById("chatSend");
  let activado = false;

  function burbuja(html, quien) {
    const div = document.createElement("div");
    div.className = "msg " + quien;
    div.innerHTML = html;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
    return div;
  }

  function typing() {
    const div = document.createElement("div");
    div.className = "msg bot";
    div.innerHTML = '<span class="mut">Consultando datos…</span>';
    log.appendChild(div); log.scrollTop = log.scrollHeight;
    return div;
  }

  function activar() {
    if (activado) return;
    activado = true;
    app.classList.add("active");   // hero -> workspace (chat + dashboard) con transición CSS
    burbuja(ayudaTxt(), "bot");    // saludo del asistente al abrir el chat
  }

  function enviar(texto) {
    const val = (texto != null ? texto : input.value).trim();
    if (!val) return;
    const primera = !activado;
    activar();
    pushHistorial(val);
    burbuja(val, "user");
    input.value = "";

    const t = typing();
    setTimeout(() => {
      t.remove();
      const { txt, enfoque } = responder(val);
      burbuja(txt, "bot");
      if (enfoque && window.ACDashboard) window.ACDashboard.enfocar(enfoque);
    }, primera ? 620 : 260);
  }

  send.addEventListener("click", () => enviar());
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") enviar(); });

  // delegacion: cualquier enlace .qlink dentro del chat dispara una consulta
  log.addEventListener("click", (e) => {
    const a = e.target.closest(".qlink");
    if (a) { e.preventDefault(); enviar(a.dataset.q); }
  });

  // sugerencias del hero (lista .sug): usar su texto .q
  document.querySelectorAll(".hero .sug").forEach(s =>
    s.addEventListener("click", () => enviar(s.querySelector(".q").textContent)));

  // boton de ayuda
  const help = document.getElementById("helpBtn");
  if (help) help.addEventListener("click", () => enviar("ayuda"));

  initSidebar();
})();
