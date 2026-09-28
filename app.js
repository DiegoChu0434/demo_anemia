/* AnemiaCero Junin - Dashboard demo
   Consume window.DASHBOARD_DATA (generado por el ETL en data.js). */
(function () {
  const D = window.DASHBOARD_DATA;
  if (!D) { document.body.innerHTML = "<p style='padding:40px'>No se encontró data.js. Ejecuta primero <code>python etl_indicadores.py</code>.</p>"; return; }

  // ---------- estado ----------
  let prov = "", dist = "", funnelKey = "cred_mes";
  let sortCol = "ninos", sortDir = -1;

  // ---------- helpers ----------
  const $ = (id) => document.getElementById(id);
  const fmt = (n) => n == null ? "–" : n.toLocaleString("es-PE");
  const pct = (v) => v == null ? "–" : v.toFixed(1) + "%";

  // clasificacion de color por indicador (umbrales del informe, HU-03 / Tabla 3.7)
  function clsRecup(v){ if(v==null)return""; return v<30?"bad":v<50?"warn":"good"; }       // recuperacion: mayor es mejor
  function clsAbandono(v){ if(v==null)return""; return v>50?"bad":v>40?"warn":"good"; }     // abandono: menor es mejor
  function clsAdher(v){ if(v==null)return""; return v<40?"bad":v<60?"warn":"good"; }
  function clsCont(v){ if(v==null)return""; return v<15?"bad":v<40?"warn":"good"; }

  // ---------- poblar filtros ----------
  function initFiltros() {
    const sp = $("selProv");
    D.provincias.forEach(p => {
      const o = document.createElement("option"); o.value = p.Provincia; o.textContent = cap(p.Provincia); sp.appendChild(o);
    });
    sp.addEventListener("change", () => { prov = sp.value; dist = ""; fillDistritos(); render(); });
    $("selDist").addEventListener("change", (e) => { dist = e.target.value; render(); });
    $("btnReset").addEventListener("click", () => { prov=""; dist=""; sp.value=""; fillDistritos(); render(); });
    document.querySelectorAll(".funnel-tabs button").forEach(b => {
      b.addEventListener("click", () => {
        document.querySelectorAll(".funnel-tabs button").forEach(x=>x.classList.remove("on"));
        b.classList.add("on"); funnelKey = b.dataset.f; render();
      });
    });
    document.querySelectorAll("#tabla th").forEach(th => {
      th.addEventListener("click", () => {
        const c = th.dataset.c;
        if (sortCol === c) sortDir *= -1; else { sortCol = c; sortDir = (c==="Distrito"||c==="Provincia")?1:-1; }
        renderTabla();
      });
    });
    fillDistritos();
  }
  function fillDistritos() {
    const sd = $("selDist"); sd.innerHTML = '<option value="">Todos</option>';
    D.distritos.filter(d => !prov || d.Provincia === prov)
      .forEach(d => { const o=document.createElement("option"); o.value=d.Distrito; o.textContent=cap(d.Distrito); sd.appendChild(o); });
  }
  const cap = (s) => s ? s.charAt(0)+s.slice(1).toLowerCase() : s;

  // ---------- obtener el registro del ambito actual ----------
  function scope() {
    if (dist) return D.distritos.find(d => d.Distrito===dist && (!prov || d.Provincia===prov));
    if (prov) return D.provincias.find(p => p.Provincia===prov);
    // global
    return {
      ind01: D.global.ind01_continuidad_hb, ind02: D.global.ind02_recup_gestantes,
      ind03: D.global.ind03_abandono_cred, ind04: D.global.ind04_adherencia_sup,
      ind05: D.global.ind05_recup_ninos, alerta: D.global.alerta,
      gestantes: D.meta.registros.gestantes, cred: D.meta.registros.cred, ninos: D.meta.registros.ninos,
    };
  }

  // ---------- render principal ----------
  function render() {
    const s = scope();
    // ambito
    $("scopeLvl").textContent = dist ? "Distrito" : prov ? "Provincia" : "Ámbito";
    $("scopeNm").textContent  = dist ? cap(dist) : prov ? cap(prov) : "Región Junín";
    $("badgeRegs").textContent = fmt(D.meta.registros.total) + " registros";

    renderAlerta(s.alerta);
    renderKpis(s);
    renderFunnel();     // el embudo usa series globales (cohorte regional) salvo ambito global
    renderSeveridad();
    renderVolumen(s);
    renderTabla();
  }

  function renderAlerta(a) {
    const box = $("alerta");
    box.className = "alerta " + (a==="sin_datos"?"ambar":a);
    const txt = {
      verde:"Nivel VERDE — indicadores dentro de rangos aceptables.",
      ambar:"Nivel ÁMBAR — seguimiento con pérdidas relevantes; requiere atención.",
      rojo:"Nivel ROJO — deserción crítica o baja recuperación; intervención prioritaria.",
      sin_datos:"Datos insuficientes en este ámbito (menos de 10 casos)."
    }[a] || a;
    $("alertaTxt").textContent = "IND-07 · " + txt;
  }

  function kpiCard(key, cod, lab, val, cls) {
    return `<div class="kpi" data-k="${key}">
      <div class="cod">${cod}</div>
      <div class="lab">${lab}</div>
      <div class="val ${cls}">${pct(val)}</div>
      <div class="bar"><i class="bg-${cls||'good'}" style="width:${val==null?0:Math.min(100,val)}%"></i></div>
    </div>`;
  }
  function renderKpis(s) {
    $("kpis").innerHTML =
      kpiCard("ind01","IND-01","Continuidad Hb en gestantes (5° dosaje)", s.ind01, clsCont(s.ind01)) +
      kpiCard("ind02","IND-02","Recuperación de gestantes", s.ind02, clsRecup(s.ind02)) +
      kpiCard("ind03","IND-03","Abandono de controles CRED", s.ind03, clsAbandono(s.ind03)) +
      kpiCard("ind04","IND-04","Adherencia a suplementación (5° toma)", s.ind04, clsAdher(s.ind04)) +
      kpiCard("ind05","IND-05","Recuperación de anemia infantil", s.ind05, clsRecup(s.ind05));
  }

  function renderFunnel() {
    const series = D.funnel[funnelKey];
    const labels = {
      cred_mes: series.map((_,i)=>"Mes "+(i+1)),
      gestantes_dosaje: series.map((_,i)=>"Dosaje "+(i+1)),
      sup_toma: series.map((_,i)=>"Toma T"+(i+1)),
    }[funnelKey];
    const base = series[0] || 1;
    let html = "";
    series.forEach((v,i) => {
      const w = (100*v/base).toFixed(1);
      html += `<div class="funnel-row"><div class="k">${labels[i]}</div>
        <div class="funnel-bar"><i style="width:${w}%"></i><span>${fmt(v)} · ${w}%</span></div></div>`;
    });
    $("funnel").innerHTML = html;
    const last = series[series.length-1], ret = (100*last/base).toFixed(1);
    const note = {
      cred_mes:`Del 100% inicial se retiene ${ret}% al mes 11 (abandono ${(100-ret).toFixed(1)}%).`,
      gestantes_dosaje:`Solo ${ret}% de quienes inician el control de Hb llega al 5° dosaje.`,
      sup_toma:`La adherencia cae a ${ret}% en la 5ª toma respecto de la 1ª.`
    }[funnelKey];
    $("funnelNote").textContent = "Series de cohorte regional. " + note;
  }

  function renderSeveridad() {
    drawSev("sevGest", D.severidad.gestantes);
    drawSev("sevNin",  D.severidad.ninos);
  }
  function drawSev(id, d) {
    const tot = d.LEV + d.MOD + d.SEV + d.NULL || 1;
    const parts = [["LEV",d.LEV,"#2E7D32"],["MOD",d.MOD,"#E8A317"],["SEV",d.SEV,"#C0392B"],["s/d",d.NULL,"#9AA5B1"]];
    $(id).innerHTML = parts.filter(p=>p[1]>0).map(([lab,v,col])=>{
      const w = Math.max(6, 100*v/tot);
      return `<div class="seg" style="background:${col};flex:${v}" title="${lab}: ${fmt(v)} (${(100*v/tot).toFixed(1)}%)">${lab} ${(100*v/tot).toFixed(0)}%</div>`;
    }).join("");
  }

  function renderVolumen(s) {
    const rows = [["Gestantes con anemia", s.gestantes, "#2E5496"],
                  ["Controles CRED", s.cred, "#3B7DD8"],
                  ["Niños <36m con anemia", s.ninos, "#6FA8DC"]];
    const max = Math.max(...rows.map(r=>r[1]),1);
    $("volumen").innerHTML = rows.map(([lab,v,col])=>
      `<div class="funnel-row"><div class="k" style="width:150px">${lab}</div>
       <div class="funnel-bar"><i style="width:${100*v/max}%;background:${col}"></i><span>${fmt(v)}</span></div></div>`
    ).join("");
  }

  function renderTabla() {
    const tb = $("tabla").querySelector("tbody");
    let rows = D.distritos.filter(d => !prov || d.Provincia===prov);
    if (dist) rows = rows.filter(d => d.Distrito===dist);
    $("tblScope").textContent = prov ? "· "+cap(prov) : "· Región Junín ("+rows.length+" distritos)";
    rows = rows.slice().sort((a,b)=>{
      let x=a[sortCol], y=b[sortCol];
      if (typeof x==="string"){ x=x||""; y=y||""; return x.localeCompare(y)*sortDir; }
      x = x==null?-1:x; y = y==null?-1:y; return (x-y)*sortDir;
    });
    tb.innerHTML = rows.map(r=>`<tr data-d="${r.Distrito}" data-p="${r.Provincia}" style="cursor:pointer">
      <td>${cap(r.Distrito)}</td>
      <td>${cap(r.Provincia)}</td>
      <td class="num">${fmt(r.ninos)}</td>
      <td class="num ${clsAbandono(r.ind03)}">${pct(r.ind03)}</td>
      <td class="num ${clsAdher(r.ind04)}">${pct(r.ind04)}</td>
      <td class="num ${clsRecup(r.ind05)}">${pct(r.ind05)}</td>
      <td><span class="pill ${r.alerta}">${({verde:"Verde",ambar:"Ámbar",rojo:"Rojo",sin_datos:"s/d"})[r.alerta]||r.alerta}</span></td>
    </tr>`).join("");
    tb.querySelectorAll("tr").forEach(tr=>tr.addEventListener("click",()=>{
      prov = tr.dataset.p; dist = tr.dataset.d;
      $("selProv").value = prov; fillDistritos(); $("selDist").value = dist; render();
      document.querySelector(".dash").scrollTo({top:0,behavior:"smooth"});
    }));
  }

  // ---------- resaltado temporal ----------
  function clearHl() {
    document.querySelectorAll(".kpi.hl,.panel.hl,tbody tr.hl").forEach(e => e.classList.remove("hl"));
  }
  function setFunnel(key) {
    if (!key) return;
    funnelKey = key;
    document.querySelectorAll(".funnel-tabs button").forEach(b =>
      b.classList.toggle("on", b.dataset.f === key));
  }

  // ---------- API publica para el asistente ----------
  window.ACDashboard = {
    setFiltro(provincia, distrito) {
      prov = provincia || "";
      dist = distrito || "";
      $("selProv").value = prov;
      fillDistritos();
      $("selDist").value = dist;
      render();
    },
    // enfoque contextual segun la pregunta: {prov, dist, kpi, funnel, tabla}
    enfocar(opts) {
      opts = opts || {};
      if (opts.prov !== undefined || opts.dist !== undefined) {
        prov = opts.prov || ""; dist = opts.dist || "";
        $("selProv").value = prov; fillDistritos(); $("selDist").value = dist;
      }
      if (opts.funnel) setFunnel(opts.funnel);
      render();
      clearHl();
      // resaltar el elemento relevante tras el render
      requestAnimationFrame(() => {
        if (opts.kpi) {
          const el = document.querySelector(`.kpi[data-k="${opts.kpi}"]`);
          if (el) { el.classList.add("hl"); el.scrollIntoView({behavior:"smooth",block:"nearest"}); }
        }
        if (opts.panel) {
          const p = $(opts.panel); if (p){ p.classList.add("hl"); p.scrollIntoView({behavior:"smooth",block:"nearest"}); }
        }
        if (opts.tablaRojos) { $("panelTabla").classList.add("hl"); $("panelTabla").scrollIntoView({behavior:"smooth",block:"nearest"}); }
      });
      // quitar resaltado a los 2.5s
      clearTimeout(window.__hlT); window.__hlT = setTimeout(clearHl, 2500);
    }
  };

  // ---------- init ----------
  initFiltros();
  render();
})();
