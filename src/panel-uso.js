(function () {
  if (!window.ACUso) return;

  const panel = document.getElementById("panelUso");
  if (!panel) return;

  const hayIA = window.ACIA && window.ACIA.disponible();
  if (!hayIA) return;
  panel.style.display = "block";

  const $ = (id) => document.getElementById(id);
  const fmt = (n) => (n == null ? "0" : n.toLocaleString("es-PE"));

  function clasePct(p) {
    if (p >= 90) return "bad";
    if (p >= 70) return "warn";
    return "";
  }

  function setBarra(barId, valId, limId, valor, limite) {
    const pct = limite ? Math.min(100, (100 * valor) / limite) : 0;
    const bar = $(barId);
    if (bar) {
      bar.style.width = pct.toFixed(1) + "%";
      bar.className = clasePct(pct);
    }
    if ($(valId)) $(valId).textContent = fmt(valor);
    if (limId && $(limId)) $(limId).textContent = fmt(limite);
  }

  function render(e) {
    const L = e.limites;
    setBarra("usoRpdBar", "usoRpdVal", "usoRpdLim", e.dia.llamadas, L.rpd);
    setBarra("usoRpmBar", "usoRpmVal", "usoRpmLim", e.ventana.rpm, L.rpm);
    setBarra("usoTpmBar", "usoTpmVal", "usoTpmLim", e.ventana.tpm, L.tpm);
    if ($("usoTokDia")) $("usoTokDia").textContent = fmt(e.dia.tokens);

    const note = $("usoNote");
    if (note) {
      note.textContent = (L.referencial
        ? "Límites referenciales del plan gratuito; los reales se ven en Google AI Studio. "
        : "") + "Solo cuenta el consumo hecho desde esta página. RPD se reinicia a diario.";
    }
  }

  const reset = $("usoReset");
  if (reset) reset.addEventListener("click", () => window.ACUso.reset());

  function destello() {
    panel.classList.remove("uso-flash");
    void panel.offsetWidth;
    panel.classList.add("uso-flash");
  }

  window.ACUso.onCambio((e) => { render(e); destello(); });
  render(window.ACUso.estado());

  // refresco en vivo: la ventana por-minuto (RPM/TPM) cambia con el tiempo,
  // no solo al preguntar, así que repintamos cada segundo.
  setInterval(() => render(window.ACUso.estado()), 1000);
})();
