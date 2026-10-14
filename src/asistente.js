(function () {
  const D = window.DASHBOARD_DATA;
  if (!D) return;

  const norm = (s) => (s || "").toString().toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9\s]/g, " ").replace(/\s+/g, " ").trim();

  const cap = (s) => s ? s.charAt(0) + s.slice(1).toLowerCase() : s;
  const pct = (v) => v == null ? "sin dato" : v.toFixed(1) + "%";
  const fmt = (n) => n == null ? "–" : n.toLocaleString("es-PE");

  const PROVS = D.provincias.map(p => ({ raw: p.Provincia, n: norm(p.Provincia) }));
  const DISTS = D.distritos.map(d => ({ raw: d.Distrito, n: norm(d.Distrito), prov: d.Provincia }));

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

  function detectarLugar(q) {
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

  function responder(pregunta) {
    const q = norm(pregunta);

    if (/\b(hola|buenas|ayuda|que puedes|puedes hacer|ejemplos)\b/.test(q))
      return { txt: ayudaTxt(), foco:null };

    const ind = detectarIndicador(q);
    const esRanking = /\b(mejor|mejores|peor|peores|mas|menos|mayor|menor|top|ranking|cuales|que distrito|que provincia|donde)\b/.test(q);

    if (ind && esRanking) return ranking(q, ind);

    if (/\b(rojo|rojos|critico|criticos|alerta|alertas|prioridad|prioritario)\b/.test(q)
        || (/\b(peor|peores)\b/.test(q) && !ind))
      return rankingAlerta(q);

    const lugar = detectarLugar(q);
    if (ind) return valorIndicadorLugar(ind, lugar);

    if (lugar.tipo !== "global" || /\b(resumen|general|region|junin|como esta|estado|situacion|todo)\b/.test(q))
      return resumenLugar(lugar);

    return { txt:"No estoy seguro de qué indicador quieres. Prueba con: <i>«recuperación en Huancayo»</i>, <i>«distritos en rojo»</i> o <i>«peor abandono CRED»</i>.", foco:null };
  }

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

  const MIN_CASOS = 10;
  function ranking(q, ind) {
    const nivel = /provincia/.test(q) ? "provincias" : "distritos";
    const campoVol = (ind.key === "ind01" || ind.key === "ind02") ? "gestantes" : "ninos";
    let arr = D[nivel].filter(x => x[ind.campo] != null && (x[campoVol] || 0) >= MIN_CASOS);
    const peor = /\b(peor|peores|mas abandono|mayor abandono|menos|menor)\b/.test(q) || (ind.mejor === "bajo" && !/\b(mejor|mejores|menos abandono|menor abandono)\b/.test(q));
    let asc;
    if (ind.mejor === "alto") asc = peor;
    else asc = !peor;
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
    return `Soy el asistente de <b>AnemiaCero Junín</b>. Pregúntame en lenguaje natural sobre los ` +
      `datos de anemia de la DIRESA Junín: recuperación infantil, abandono de controles CRED, ` +
      `adherencia a la suplementación, continuidad de hemoglobina en gestantes o alertas por distrito. ` +
      `Puedo dar valores de un lugar, comparar y rankear, o resumir una provincia o distrito.`;
  }

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

  const app = document.getElementById("app");
  const log = document.getElementById("chatLog");
  const input = document.getElementById("chatInput");
  const send = document.getElementById("chatSend");
  let activado = false;

  const AVATAR = "img/Gemini_Generated_Image_ry3ymery3ymery3y.jpg";

  function burbuja(html, quien) {
    const div = document.createElement("div");
    div.className = "msg " + quien;
    if (quien === "bot") {
      div.innerHTML = `<img class="avatar" src="${AVATAR}" alt="asistente"><div class="msg-txt">${html}</div>`;
    } else {
      div.innerHTML = html;
    }
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
    return div;
  }

  function typing() {
    const div = document.createElement("div");
    div.className = "msg bot";
    div.innerHTML = `<img class="avatar" src="${AVATAR}" alt="asistente"><div class="msg-txt"><span class="mut">Consultando datos…</span></div>`;
    log.appendChild(div); log.scrollTop = log.scrollHeight;
    return div;
  }

  function activar() {
    if (activado) return;
    activado = true;
    app.classList.add("active");
  }

  const conversacion = [];
  const soloTexto = (html) => (html || "").replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();

  function enviar(texto) {
    const val = (texto != null ? texto : input.value).trim();
    if (!val) return;
    const primera = !activado;
    activar();
    pushHistorial(val);
    burbuja(val, "user");
    input.value = "";

    const t = typing();
    const delay = primera ? 620 : 260;
    const inicio = Date.now();
    const historialIA = conversacion.slice(-6);
    conversacion.push({ rol: "usuario", texto: val });

    const pintar = ({ txt, enfoque }) => {
      t.remove();
      burbuja(txt, "bot");
      conversacion.push({ rol: "asistente", texto: soloTexto(txt).slice(0, 400) });
      if (conversacion.length > 20) conversacion.splice(0, conversacion.length - 20);
      if (enfoque && window.ACDashboard) window.ACDashboard.enfocar(enfoque);
    };

    const usarIA = window.ACIA && window.ACIA.disponible();
    const promesa = usarIA
      ? window.ACIA.responder(val, historialIA).catch(() => null)
      : Promise.resolve(null);

    promesa.then((resIA) => {
      const res = resIA || responder(val);
      const espera = Math.max(0, delay - (Date.now() - inicio));
      setTimeout(() => pintar(res), espera);
    });
  }

  send.addEventListener("click", () => enviar());
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") enviar(); });

  log.addEventListener("click", (e) => {
    const a = e.target.closest(".qlink");
    if (a) { e.preventDefault(); enviar(a.dataset.q); }
  });

  const help = document.getElementById("helpBtn");
  if (help) help.addEventListener("click", () => enviar("ayuda"));

  window.ACAsistente = {
    consultas() { return historial.slice(); },
    reejecutar(q) { if (q) enviar(q); },
  };

  initSidebar();
})();
