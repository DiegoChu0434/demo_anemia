(function () {
  const CFG = window.AC_CONFIG || {};
  const LIM = CFG.LIMITES || { rpm: 15, rpd: 1500, tpm: 1000000, referencial: true };
  const STORE_KEY = "ac_uso_gemini";
  const VENTANA_MS = 60000;

  const listeners = [];
  let estadoCache = cargar();

  function hoyISO() {
    return new Date().toISOString().slice(0, 10);
  }

  function base() {
    return {
      fecha: hoyISO(),
      llamadasDia: 0,
      tokensDia: 0,
      eventos: [],
    };
  }

  function cargar() {
    let s;
    try {
      s = JSON.parse(localStorage.getItem(STORE_KEY)) || base();
    } catch (e) {
      s = base();
    }
    if (s.fecha !== hoyISO()) s = base();
    if (!Array.isArray(s.eventos)) s.eventos = [];
    return s;
  }

  function guardar(s) {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(s));
    } catch (e) {}
  }

  function limpiarVentana(s) {
    const corte = Date.now() - VENTANA_MS;
    s.eventos = s.eventos.filter(ev => ev.t >= corte);
  }

  function registrar(usageMetadata) {
    const tokens = (usageMetadata && (usageMetadata.totalTokenCount || usageMetadata.total_token_count)) || 0;
    if (estadoCache.fecha !== hoyISO()) estadoCache = base();
    estadoCache.llamadasDia += 1;
    estadoCache.tokensDia += tokens;
    estadoCache.eventos.push({ t: Date.now(), tokens });
    limpiarVentana(estadoCache);
    guardar(estadoCache);
    emitir();
    return estado();
  }

  function estado() {
    if (estadoCache.fecha !== hoyISO()) estadoCache = base();
    limpiarVentana(estadoCache);
    const rpmActual = estadoCache.eventos.length;
    const tpmActual = estadoCache.eventos.reduce((a, ev) => a + ev.tokens, 0);
    return {
      limites: { rpm: LIM.rpm, rpd: LIM.rpd, tpm: LIM.tpm, referencial: !!LIM.referencial },
      dia: {
        fecha: estadoCache.fecha,
        llamadas: estadoCache.llamadasDia,
        tokens: estadoCache.tokensDia,
      },
      ventana: {
        rpm: rpmActual,
        tpm: tpmActual,
      },
    };
  }

  function reset() {
    estadoCache = base();
    guardar(estadoCache);
    emitir();
  }

  function onCambio(cb) {
    if (typeof cb === "function") listeners.push(cb);
  }

  function emitir() {
    const e = estado();
    listeners.forEach(cb => { try { cb(e); } catch (err) {} });
  }

  window.ACUso = { registrar, estado, reset, onCambio };
})();
