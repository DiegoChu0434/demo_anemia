(function () {
  const DIM_UBICACION = {
    nombre: "dim_ubicacion",
    tipo: "Dimensión · 3FN",
    campos: [
      { k: "id_ubicacion", key: "pk", d: "identificador de la ubicación" },
      { k: "provincia", d: "provincia" },
      { k: "distrito", d: "distrito" },
      { k: "cod_red / red", d: "red de salud" },
      { k: "cod_microred / microred", d: "micro-red" },
      { k: "departamento", d: "departamento" },
      { k: "ubigeo", d: "código de ubigeo" },
    ],
  };
  const DIM_ESTABLECIMIENTO = {
    nombre: "dim_establecimiento",
    tipo: "Dimensión · 3FN",
    campos: [
      { k: "renaes", key: "pk", d: "código RENAES del establecimiento" },
      { k: "id_establecimiento", d: "identificador interno" },
      { k: "nombre_establecimiento", d: "nombre del establecimiento" },
      { k: "categoria", d: "I-1, I-2, I-3, I-4, II-1, II-2, III-E" },
      { k: "ubigeo_establecimiento", d: "ubigeo del establecimiento" },
      { k: "cod_disa / disa", d: "dirección de salud" },
      { k: "id_ubicacion", key: "fk", d: "→ dim_ubicacion" },
    ],
  };

  const DATASETS = {
    gestantes: {
      titulo: "gestantes",
      origen: "DS1 · DATOS_ABIERTOS_GESTANTES_ANEMIA_DIRESAJUNIN.csv",
      meta: "Dataset de <b>gestantes con anemia</b> (4,791 registros). Al normalizar, la geografía y el establecimiento salieron a las dimensiones; el hecho conserva solo la FK <b>renaes</b>.",
      tablas: [
        {
          nombre: "hecho_gestante",
          tipo: "Hecho · 3FN",
          campos: [
            { k: "id_gestante", key: "pk", d: "clave sustituta" },
            { k: "renaes", key: "fk", d: "→ dim_establecimiento" },
            { k: "cod_pc", d: "código de paciente (enmascarado)" },
            { k: "fecha_nacimiento", d: "fecha de nacimiento" },
            { k: "fur", d: "fecha de última regla" },
            { k: "severidad", d: "LEV / MOD / SEV" },
            { k: "fecha_dx", d: "fecha de diagnóstico" },
            { k: "hemoglobina_1..5", d: "dosajes de Hb (tabulado, 1FN)" },
            { k: "fechas de dosaje", d: "fecha de cada dosaje" },
            { k: "fecha_recuperada", d: "fecha de recuperación" },
            { k: "fecha_supT1..T3", d: "tomas de suplemento (tabulado, 1FN)" },
            { k: "flag_recuperada", d: "0/1 derivado de la fecha" },
          ],
        },
        DIM_ESTABLECIMIENTO, DIM_UBICACION,
      ],
      nota: "Los dosajes y tomas se mantienen tabulados en columnas (1FN) por decisión de diseño analítico; el resto de atributos descriptivos cumple 3FN.",
    },

    cred: {
      titulo: "controles_cred",
      origen: "DS2 · NIÑAS Y NIÑOS DE 364 DÍAS ... ONCE (11) CONTROLES CRED.csv",
      meta: "Dataset de <b>controles CRED</b> (19,686 registros). Salieron a dimensión el nombre y categoría del establecimiento, además de la geografía.",
      tablas: [
        {
          nombre: "hecho_cred",
          tipo: "Hecho · 3FN",
          campos: [
            { k: "id_cred", key: "pk", d: "clave sustituta" },
            { k: "renaes", key: "fk", d: "→ dim_establecimiento" },
            { k: "anio / mes", d: "período del registro" },
            { k: "sexo", d: "sexo del niño" },
            { k: "fecha_nac", d: "fecha de nacimiento" },
            { k: "seguro", d: "tipo de seguro" },
            { k: "edad_dias", d: "edad en días" },
            { k: "peso_cnv", d: "peso al nacer" },
            { k: "fecha_cred_mes1..11", d: "fecha de cada control (tabulado, 1FN)" },
            { k: "num_cred_mes1..11", d: "0/1 por mes (tabulado, 1FN)" },
          ],
        },
        DIM_ESTABLECIMIENTO, DIM_UBICACION,
      ],
      nota: "Los controles mes 1 a 11 se conservan tabulados (1FN). IND-03 (abandono) se calcula con num_cred_mes1 y num_cred_mes11.",
    },

    ninos: {
      titulo: "ninos_anemia",
      origen: "DS3 · Niños_menores_de_36_meses_con_dx_de_anemia...csv",
      meta: "Dataset de <b>niños &lt;36 meses con anemia</b> (12,486 registros). La severidad y las hemoglobinas dependen del propio hecho; la geografía salió a dimensión.",
      tablas: [
        {
          nombre: "hecho_nino_anemia",
          tipo: "Hecho · 3FN",
          campos: [
            { k: "id_nino", key: "pk", d: "clave sustituta" },
            { k: "renaes", key: "fk", d: "→ dim_establecimiento" },
            { k: "fecha_nac", d: "fecha de nacimiento" },
            { k: "severidad", d: "LEV / MOD / SEV" },
            { k: "fecha_dx", d: "fecha de diagnóstico" },
            { k: "hb_dx", d: "Hb al diagnóstico" },
            { k: "hb_mes / hb_tresmeses / hb_seismeses", d: "Hb de control" },
            { k: "fecha_recup", d: "fecha de recuperación" },
            { k: "flag_recuperado", d: "0/1 recuperación" },
            { k: "fecha_supT1..T6", d: "tomas de suplemento (T6 excluida)" },
          ],
        },
        DIM_ESTABLECIMIENTO, DIM_UBICACION,
      ],
      nota: "T6 se excluye del cálculo de adherencia (campo no operativo, 0.2% de registros). Los demás atributos cumplen 3FN.",
    },

    establecimientos: {
      titulo: "establecimientos",
      origen: "Catálogo RENAES (441 establecimientos únicos, extraído de DS2)",
      meta: "Las <b>dos dimensiones</b> del modelo en estrella. Aquí se resuelve la dependencia transitiva <b>renaes → ubicación → provincia</b> que exige la 3FN: la jerarquía geográfica se aísla en dim_ubicacion.",
      tablas: [DIM_ESTABLECIMIENTO, DIM_UBICACION],
      nota: "Si cambia el nombre de un distrito o la asignación de una micro-red, se corrige en una sola fila de dim_ubicacion y se propaga a todos los establecimientos.",
    },
  };

  const modal = document.getElementById("modeloModal");
  const titEl = document.getElementById("modeloTit");
  const bodyEl = document.getElementById("modeloBody");
  if (!modal) return;

  function campoHTML(c) {
    const key = c.key ? `<span class="mb-key ${c.key}">${c.key.toUpperCase()}</span>` : "";
    return `<div class="mb-field"><span class="k">${c.k}${key}</span><span class="d">${c.d || ""}</span></div>`;
  }
  function tablaHTML(t) {
    const campos = t.campos.map(campoHTML).join("");
    return `<div class="mb-tabla">
      <div class="mb-th"><span class="nm">${t.nombre}</span><span class="tag">${t.tipo}</span></div>
      ${campos}
    </div>`;
  }

  function abrir(dsKey) {
    const ds = DATASETS[dsKey];
    if (!ds) return;
    titEl.textContent = ds.titulo;
    bodyEl.innerHTML =
      `<p class="mb-meta"><b>Origen:</b> ${ds.origen}<br>${ds.meta}</p>` +
      ds.tablas.map(tablaHTML).join("") +
      `<div class="mb-note"><b>Nota de normalización.</b> ${ds.nota}</div>`;
    modal.classList.add("open");
  }
  function cerrar() { modal.classList.remove("open"); }

  document.querySelectorAll(".tabla-row[data-ds]").forEach(row => {
    row.style.cursor = "pointer";
    row.addEventListener("click", () => abrir(row.dataset.ds));
  });
  document.getElementById("modeloClose").addEventListener("click", cerrar);
  modal.addEventListener("click", (e) => { if (e.target === modal) cerrar(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrar(); });
})();
