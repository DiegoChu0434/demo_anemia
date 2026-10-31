# -*- coding: utf-8 -*-
import os, re, json
import pandas as pd
import numpy as np
import unicodedata

PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROYECTO, "data")
RAW_DIR  = os.path.join(DATA_DIR, "raw")
OUT      = os.path.join(DATA_DIR, "dashboard_data.json")

FILES = {
    "gestantes": (os.path.join(RAW_DIR, "DATOS_ABIERTOS_GESTANTES_ANEMIA_DIRESAJUNIN.csv"), "cp1252"),
    "cred":      (os.path.join(RAW_DIR, "NIÑAS Y NIÑOS DE 364 DÍAS DE EDAD, QUE CUENTAN CON ONCE (11) CONTROLES CRED.csv"), "utf-8-sig"),
    "ninos":     (os.path.join(RAW_DIR, "Niños_menores_de_36_meses_con_dx_de_anemia_en_la_Región_ Junín.csv"), "cp1252"),
    "credn":     (os.path.join(RAW_DIR, "Niños JUNIN.csv"), "utf-8"),
    "cnv":       (os.path.join(RAW_DIR, "CNV_MINSA_CORTE_30112025.csv"), "utf-8"),
}

UBIGEO_PROV = {
    "01": "HUANCAYO", "02": "CONCEPCION", "03": "CHANCHAMAYO", "04": "JAUJA",
    "05": "JUNIN", "06": "SATIPO", "07": "TARMA", "08": "YAULI", "09": "CHUPACA",
}

def strip_acentos(s):
    return "".join(ch for ch in unicodedata.normalize("NFD", s)
                   if unicodedata.category(ch) != "Mn")

def norm_txt(s):
    if s is None:
        return ""
    s = re.sub(r"\s+", " ", str(s)).strip().upper()
    return s

def norm_key(s):
    return strip_acentos(norm_txt(s))

def is_null(v):
    return v is None or str(v).strip().upper() in ("", "NULL", "NAN")

def sev_std(v):
    if is_null(v):
        return None
    u = str(v).strip().upper()
    return u if u in ("LEV", "MOD", "SEV") else None

def to_iso(v):
    if is_null(v):
        return None
    try:
        d = pd.to_datetime(v, format="%d/%m/%Y", errors="coerce")
        return None if pd.isna(d) else d.strftime("%Y-%m-%d")
    except Exception:
        return None

def load(name):
    path, enc = FILES[name]
    df = pd.read_csv(path, sep=";", encoding=enc, dtype=str, keep_default_na=False)
    return df

def num(serie):
    return pd.to_numeric(serie.astype(str).str.strip().str.replace(",", ".", regex=False), errors="coerce")

print("== EXTRACCION ==")
g = load("gestantes"); print(f"  gestantes: {len(g)} filas")
c = load("cred");      print(f"  cred:      {len(c)} filas")
n = load("ninos");     print(f"  ninos:     {len(n)} filas")

cn = pd.read_csv(FILES["credn"][0], sep=",", encoding="utf-8",
                 dtype=str, keep_default_na=False)
print(f"  credn (CRED nutricional): {len(cn)} filas")

cnv_parts = []
reader = pd.read_csv(FILES["cnv"][0], sep=";", dtype=str, keep_default_na=False,
                     encoding="utf-8", encoding_errors="replace",
                     on_bad_lines="skip", engine="c", chunksize=200000)
for ch in reader:
    ub = ch["IdUbigeoInei"].astype(str).str.strip()
    jun = ch[ub.str.startswith("12")].copy()
    if len(jun):
        cnv_parts.append(jun)
cv = pd.concat(cnv_parts, ignore_index=True) if cnv_parts else pd.DataFrame()
print(f"  cnv (nacidos vivos, Junin): {len(cv)} filas")

print("== TRANSFORMACION ==")

g["Provincia"] = g["Provincia"].map(norm_txt)
g["Distrito"]  = g["Distrito"].map(norm_txt)
g["severidad"] = g["valor_labo"].map(sev_std)
for k in range(1, 6):
    g[f"hb{k}_ok"] = g[f"hemoglobina_{k}"].map(lambda v: 0 if is_null(v) else 1)
g["flag_recuperada"] = g["fecha_7_recuperada"].map(lambda v: 0 if is_null(v) else 1)
dup_g = g.duplicated().sum()
g = g.drop_duplicates()
print(f"  gestantes: {dup_g} filas duplicadas eliminadas; severidad NULL={g['severidad'].isna().sum()}")

c["Provincia"] = c["Provincia"].map(norm_txt)
c["Distrito"]  = c["Distrito"].map(norm_txt)
for k in range(1, 12):
    c[f"cred{k}"] = (c[f"num_cred_mes{k}"] == "1").astype(int)
dup_c = c.duplicated().sum()
c = c.drop_duplicates()
print(f"  cred: {dup_c} filas duplicadas eliminadas")

n["Provincia"] = n["Provincia"].map(norm_txt)
n["Distrito"]  = n["Distrito"].map(norm_txt)
n["severidad"] = n["valor_lab_dx"].map(sev_std)
n["flag_recuperado"] = (n["recup"] == "1").astype(int)
for k in range(1, 6):
    n[f"supT{k}_ok"] = n[f"fecha_supT{k}"].map(lambda v: 0 if is_null(v) else 1)
n["hb_dx_num"] = pd.to_numeric(n["hb_dx"].where(~n["hb_dx"].map(is_null)), errors="coerce")
dup_n = n.duplicated().sum()
n = n.drop_duplicates()
print(f"  ninos: {dup_n} filas duplicadas eliminadas; severidad NULL={n['severidad'].isna().sum()}")

cn["Provincia"] = cn["Prov_EESS"].map(norm_txt)
cn["Distrito"]  = cn["Dist_EESS"].map(norm_txt)
cn["cred_ok"]   = (cn["Cred"].str.strip() == "1").astype(int)
cn["supl_ok"]   = (cn["Suplementacion"].str.strip() == "1").astype(int)
cn["consej_ok"] = (cn["Consejeria"].str.strip() == "1").astype(int)
dxte = cn["Dx_TE"].map(norm_key)
cn["dcronica"]  = dxte.str.contains("CRONICA").astype(int)
dxpe = cn["Dx_PE"].map(norm_key)
cn["dglobal"]   = dxpe.str.contains("GLOBAL").astype(int)
dxpt = cn["Dx_PT"].map(norm_key)
cn["daguda"]    = dxpt.str.contains("AGUDA").astype(int)
cn["sexo_std"]  = cn["Sexo"].map(norm_txt)
dup_cn = cn.duplicated().sum()
cn = cn.drop_duplicates()
print(f"  credn: {dup_cn} filas duplicadas eliminadas; "
      f"d.cronica={int(cn['dcronica'].sum())} de {len(cn)}")

if len(cv):
    ub = cv["IdUbigeoInei"].astype(str).str.strip().str.zfill(6)
    cv["Provincia"] = ub.str[2:4].map(UBIGEO_PROV).fillna("")
    cv["Distrito"]  = ""
    peso = num(cv["PESO_NACIDO"])
    cv["peso_num"]    = peso
    cv["bajo_peso"]   = (peso < 2500).astype(int)
    cv["muy_bajo"]    = (peso < 1500).astype(int)
    dur = num(cv["DUR_EMB_PARTO"])
    cv["prematuro"]   = (dur < 37).astype(int)
    cond = cv["Condicion_Parto"].map(norm_key)
    cv["cesarea"]     = (cond == "CESAREA").astype(int)
    cv["edad_madre"]  = num(cv["Edad_Madre"])
    cv["adolescente"] = (cv["edad_madre"] < 18).astype(int)
    dup_cv = cv.duplicated().sum()
    cv = cv.drop_duplicates()
    print(f"  cnv: {dup_cv} filas duplicadas eliminadas; "
          f"bajo_peso={int(cv['bajo_peso'].sum())} de {len(cv)}")
else:
    print("  cnv: SIN DATOS de Junin")

def pct(num_, den):
    return round(100.0 * num_ / den, 1) if den else None

def indicadores_de(gg, cc, nn, cnn=None, cvv=None):
    out = {}
    tg = len(gg)
    out["ind01_continuidad_hb"] = pct(gg["hb5_ok"].sum(), tg) if tg else None
    out["ind02_recup_gestantes"] = pct(gg["flag_recuperada"].sum(), tg) if tg else None
    m1 = cc["cred1"].sum(); m11 = cc["cred11"].sum()
    out["ind03_abandono_cred"] = pct(m1 - m11, m1) if m1 else None
    tn = len(nn)
    out["ind04_adherencia_sup"] = pct(nn["supT5_ok"].sum(), tn) if tn else None
    out["ind05_recup_ninos"] = pct(nn["flag_recuperado"].sum(), tn) if tn else None

    if cnn is not None:
        tcn = len(cnn)
        out["ind08_desnutricion_cronica"] = pct(cnn["dcronica"].sum(), tcn) if tcn else None
        out["ind09_cobertura_supl"] = pct(cnn["supl_ok"].sum(), tcn) if tcn else None
        out["_tcn"] = tcn
    if cvv is not None:
        tcv = len(cvv)
        out["ind10_bajo_peso"] = pct(cvv["bajo_peso"].sum(), tcv) if tcv else None
        out["ind11_prematuridad"] = pct(cvv["prematuro"].sum(), tcv) if tcv else None
        out["ind12_cesarea"] = pct(cvv["cesarea"].sum(), tcv) if tcv else None
        out["_tcv"] = tcv

    out["_tg"] = tg; out["_tn"] = tn; out["_m1"] = int(m1); out["_m11"] = int(m11)
    return out

def semaforo(ind05, ind03):
    if ind05 is None and ind03 is None:
        return "sin_datos"
    rojo  = (ind05 is not None and ind05 < 30) or (ind03 is not None and ind03 > 50)
    ambar = (ind05 is not None and ind05 < 50) or (ind03 is not None and ind03 > 40)
    if rojo:  return "rojo"
    if ambar: return "ambar"
    return "verde"

G = indicadores_de(g, c, n, cn, cv if len(cv) else None)

funnel = {
    "gestantes_dosaje": [int(g[f"hb{k}_ok"].sum()) for k in range(1, 6)],
    "cred_mes":         [int(c[f"cred{k}"].sum()) for k in range(1, 12)],
    "sup_toma":         [int(n[f"supT{k}_ok"].sum()) for k in range(1, 6)],
}

def sev_dist(df):
    vc = df["severidad"].value_counts(dropna=False).to_dict()
    return {
        "LEV": int(vc.get("LEV", 0)),
        "MOD": int(vc.get("MOD", 0)),
        "SEV": int(vc.get("SEV", 0)),
        "NULL": int(df["severidad"].isna().sum()),
    }

def nutri_dist(df):
    normal = int(((df["dcronica"] == 0) & (df["dglobal"] == 0) & (df["daguda"] == 0)).sum())
    return {
        "NORMAL": normal,
        "CRONICA": int(df["dcronica"].sum()),
        "GLOBAL": int(df["dglobal"].sum()),
        "AGUDA": int(df["daguda"].sum()),
    }

def peso_dist(df):
    p = df["peso_num"]
    return {
        "MUY_BAJO": int((p < 1500).sum()),
        "BAJO": int(((p >= 1500) & (p < 2500)).sum()),
        "NORMAL": int(((p >= 2500) & (p < 4000)).sum()),
        "ALTO": int((p >= 4000).sum()),
        "NULL": int(p.isna().sum()),
    }

def agg_geografico(nivel_cols):
    filas = []
    partes = [g[nivel_cols], c[nivel_cols], n[nivel_cols], cn[nivel_cols]]
    if len(cv):
        partes.append(cv[nivel_cols])
    keys = pd.concat(partes).drop_duplicates().reset_index(drop=True)
    for _, key in keys.iterrows():
        def mk(df):
            m = np.ones(len(df), dtype=bool)
            for col in nivel_cols:
                m &= (df[col] == key[col])
            return df[m]
        gg, cc, nn, cnn = mk(g), mk(c), mk(n), mk(cn)
        cvv = mk(cv) if len(cv) else None
        ind = indicadores_de(gg, cc, nn, cnn, cvv)
        row = {col: key[col] for col in nivel_cols}
        row.update({
            "gestantes": int(len(gg)),
            "cred": int(len(cc)),
            "ninos": int(len(nn)),
            "credn": int(len(cnn)),
            "nacidos": int(len(cvv)) if cvv is not None else 0,
            "ind01": ind["ind01_continuidad_hb"],
            "ind02": ind["ind02_recup_gestantes"],
            "ind03": ind["ind03_abandono_cred"],
            "ind04": ind["ind04_adherencia_sup"],
            "ind05": ind["ind05_recup_ninos"],
            "ind08": ind.get("ind08_desnutricion_cronica"),
            "ind09": ind.get("ind09_cobertura_supl"),
            "ind10": ind.get("ind10_bajo_peso"),
            "ind11": ind.get("ind11_prematuridad"),
            "ind12": ind.get("ind12_cesarea"),
        })
        den_min = ind["_tn"] >= 10
        row["alerta"] = semaforo(row["ind05"], row["ind03"]) if den_min else "sin_datos"
        filas.append(row)
    return filas

print("== AGREGACION GEOGRAFICA ==")
provincias = agg_geografico(["Provincia"])
distritos  = agg_geografico(["Provincia", "Distrito"])
print(f"  provincias: {len(provincias)} | distritos: {len(distritos)}")

data = {
    "meta": {
        "proyecto": "AnemiaCero Junin - Monitor de Seguimiento Integrado",
        "fuente": "DIRESA Junin / MINSA - Plataforma Nacional de Datos Abiertos",
        "registros": {"gestantes": len(g), "cred": len(c), "ninos": len(n),
                      "credn": len(cn), "nacidos": int(len(cv)),
                      "total": len(g) + len(c) + len(n) + len(cn) + int(len(cv))},
    },
    "global": {
        "ind01_continuidad_hb":  G["ind01_continuidad_hb"],
        "ind02_recup_gestantes": G["ind02_recup_gestantes"],
        "ind03_abandono_cred":   G["ind03_abandono_cred"],
        "ind04_adherencia_sup":  G["ind04_adherencia_sup"],
        "ind05_recup_ninos":     G["ind05_recup_ninos"],
        "ind08_desnutricion_cronica": G.get("ind08_desnutricion_cronica"),
        "ind09_cobertura_supl":       G.get("ind09_cobertura_supl"),
        "ind10_bajo_peso":            G.get("ind10_bajo_peso"),
        "ind11_prematuridad":         G.get("ind11_prematuridad"),
        "ind12_cesarea":              G.get("ind12_cesarea"),
        "alerta": semaforo(G["ind05_recup_ninos"], G["ind03_abandono_cred"]),
    },
    "funnel": funnel,
    "severidad": {
        "gestantes": sev_dist(g),
        "ninos": sev_dist(n),
    },
    "nutricion": nutri_dist(cn),
    "peso_nacer": peso_dist(cv) if len(cv) else None,
    "provincias": sorted(provincias, key=lambda r: r["Provincia"]),
    "distritos": sorted(distritos, key=lambda r: (r["Provincia"], r["Distrito"])),
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

DATAJS = os.path.join(DATA_DIR, "data.js")
with open(DATAJS, "w", encoding="utf-8") as f:
    f.write("window.DASHBOARD_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")

print("\n== INDICADORES GLOBALES ==")
print(f"  IND-01 continuidad Hb gestantes (dosaje5): {G['ind01_continuidad_hb']}%")
print(f"  IND-02 recuperacion gestantes:             {G['ind02_recup_gestantes']}%")
print(f"  IND-03 abandono CRED:                      {G['ind03_abandono_cred']}%")
print(f"  IND-04 adherencia suplementacion (T5):     {G['ind04_adherencia_sup']}%")
print(f"  IND-05 recuperacion ninos:                 {G['ind05_recup_ninos']}%")
print(f"  IND-08 desnutricion cronica (CRED):        {G.get('ind08_desnutricion_cronica')}%")
print(f"  IND-09 cobertura suplementacion (CRED):    {G.get('ind09_cobertura_supl')}%")
print(f"  IND-10 bajo peso al nacer:                 {G.get('ind10_bajo_peso')}%")
print(f"  IND-11 prematuridad:                       {G.get('ind11_prematuridad')}%")
print(f"  IND-12 parto por cesarea:                  {G.get('ind12_cesarea')}%")
print(f"  IND-07 alerta global:                      {data['global']['alerta']}")
print(f"\nJSON generado: {OUT}")
