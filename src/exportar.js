(function () {
  // ---------- Modal de Consultas ----------
  const navConsultas = document.getElementById("navConsultas");
  const consultasModal = document.getElementById("consultasModal");
  const consultasBody = document.getElementById("consultasBody");
  const consultasClose = document.getElementById("consultasClose");

  function abrirConsultas() {
    const qs = (window.ACAsistente && window.ACAsistente.consultas()) || [];
    if (!qs.length) {
      consultasBody.innerHTML = `<div class="cq-empty">Aún no has hecho consultas. Escribe una pregunta en el chat y aparecerá aquí.</div>`;
    } else {
      consultasBody.innerHTML = qs.map((q, i) => {
        const esc = q.replace(/"/g, "&quot;").replace(/</g, "&lt;");
        return `<div class="cq-item" data-q="${esc}">
          <span class="cq-n">${i + 1}</span>
          <span class="cq-q">${esc}</span>
          <span class="cq-go">↩</span>
        </div>`;
      }).join("");
      consultasBody.querySelectorAll(".cq-item").forEach(el => {
        el.addEventListener("click", () => {
          cerrarConsultas();
          if (window.ACAsistente) window.ACAsistente.reejecutar(el.dataset.q);
        });
      });
    }
    consultasModal.classList.add("open");
  }
  function cerrarConsultas() { consultasModal.classList.remove("open"); }

  if (navConsultas) navConsultas.addEventListener("click", abrirConsultas);
  if (consultasClose) consultasClose.addEventListener("click", cerrarConsultas);
  if (consultasModal) consultasModal.addEventListener("click", (e) => { if (e.target === consultasModal) cerrarConsultas(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrarConsultas(); });

  // ---------- Exportar a Excel ----------
  const navExportar = document.getElementById("navExportar");

  const pct = (v) => (v == null ? "s/d" : Number(v).toFixed(1) + "%");

  function anchos(cols) { return cols.map(w => ({ wch: w })); }

  function exportar() {
    if (typeof XLSX === "undefined") {
      alert("No se pudo cargar la librería de Excel (SheetJS). Verifica tu conexión a internet e intenta de nuevo.");
      return;
    }
    if (!window.ACDashboard || !window.ACDashboard.estadoActual) {
      alert("El dashboard no está listo todavía.");
      return;
    }
    const e = window.ACDashboard.estadoActual();
    const fecha = new Date();
    const stamp = fecha.toLocaleString("es-PE");
    const wb = XLSX.utils.book_new();

    // --- Hoja 1: Resumen ---
    const resumen = [
      ["AnemiaCero Junín — Reporte del dashboard"],
      ["Generado", stamp],
      ["Ámbito", e.ambito + ": " + e.nombre],
      ["Registros totales (región)", e.totalRegistros],
      ["Nivel de alerta (IND-07)", e.alerta],
      [],
      ["INDICADORES DEL ÁMBITO ACTUAL"],
      ["Código", "Indicador", "Valor"],
      ...e.kpis.map(k => [k.cod, k.nombre, pct(k.valor)]),
      [],
      ["VOLUMEN DE REGISTROS (ámbito actual)"],
      ["Gestantes con anemia", e.volumen.gestantes],
      ["Controles CRED", e.volumen.cred],
      ["Niños <36m con anemia", e.volumen.ninos],
    ];
    const wsR = XLSX.utils.aoa_to_sheet(resumen);
    wsR["!cols"] = anchos([34, 42, 14]);
    wsR["!merges"] = [
      { s: { r: 0, c: 0 }, e: { r: 0, c: 2 } },
      { s: { r: 6, c: 0 }, e: { r: 6, c: 2 } },
      { s: { r: 10, c: 0 }, e: { r: 10, c: 2 } },
    ];
    XLSX.utils.book_append_sheet(wb, wsR, "Resumen");

    // --- Hoja 2: Detalle por distrito ---
    const headTabla = ["Distrito", "Provincia", "Niños dx", "Abandono CRED (IND-03)", "Adherencia (IND-04)", "Recuperación (IND-05)", "Alerta (IND-07)"];
    const filas = e.distritos.map(r => [
      r.Distrito, r.Provincia, r.ninos, pct(r.ind03), pct(r.ind04), pct(r.ind05), r.alerta,
    ]);
    const wsT = XLSX.utils.aoa_to_sheet([
      ["Detalle por distrito — " + e.ambito + ": " + e.nombre],
      [],
      headTabla,
      ...filas,
    ]);
    wsT["!cols"] = anchos([22, 16, 10, 22, 20, 22, 20]);
    wsT["!merges"] = [{ s: { r: 0, c: 0 }, e: { r: 0, c: 6 } }];
    wsT["!autofilter"] = { ref: XLSX.utils.encode_range({ s: { r: 2, c: 0 }, e: { r: 2 + filas.length, c: 6 } }) };
    XLSX.utils.book_append_sheet(wb, wsT, "Distritos");

    // --- Hoja 3: Embudo de seguimiento ---
    const nombreFunnel = {
      cred_mes: "Controles CRED (mes 1 a 11)",
      gestantes_dosaje: "Dosajes de Hb en gestantes (1 a 5)",
      sup_toma: "Tomas de suplemento (T1 a T5)",
    }[e.funnel.clave] || e.funnel.clave;
    const base = e.funnel.serie[0] || 1;
    const embudo = [
      ["Embudo de seguimiento — " + nombreFunnel],
      ["Serie de cohorte regional"],
      [],
      ["Punto", "Cantidad", "Retención %"],
      ...e.funnel.serie.map((v, i) => [i + 1, v, (100 * v / base).toFixed(1) + "%"]),
    ];
    const wsF = XLSX.utils.aoa_to_sheet(embudo);
    wsF["!cols"] = anchos([30, 14, 14]);
    wsF["!merges"] = [{ s: { r: 0, c: 0 }, e: { r: 0, c: 2 } }];
    XLSX.utils.book_append_sheet(wb, wsF, "Embudo");

    // --- Hoja 4: Severidad ---
    const sg = e.severidad.gestantes, sn = e.severidad.ninos;
    const sev = [
      ["Distribución por severidad (región)"],
      [],
      ["Grupo", "Leve", "Moderada", "Severa", "Sin dato"],
      ["Gestantes", sg.LEV, sg.MOD, sg.SEV, sg.NULL],
      ["Niños <36m", sn.LEV, sn.MOD, sn.SEV, sn.NULL],
    ];
    const wsS = XLSX.utils.aoa_to_sheet(sev);
    wsS["!cols"] = anchos([16, 10, 12, 10, 12]);
    wsS["!merges"] = [{ s: { r: 0, c: 0 }, e: { r: 0, c: 4 } }];
    XLSX.utils.book_append_sheet(wb, wsS, "Severidad");

    const safe = (e.nombre || "region").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/gi, "_").toLowerCase();
    const nombreArchivo = `AnemiaCero_${safe}_${fecha.toISOString().slice(0, 10)}.xlsx`;
    XLSX.writeFile(wb, nombreArchivo);
  }

  if (navExportar) navExportar.addEventListener("click", exportar);
})();
