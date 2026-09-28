# -*- coding: utf-8 -*-
"""
AnemiaCero Junin - Demo ETL + Indicadores
------------------------------------------
Reproduce el pipeline descrito en el Informe Final (cap. 3):
  1) Extraccion de los 3 CSV de la DIRESA Junin
  2) Transformacion: NULL->None, fechas ISO, severidad UPPER + dominio,
     deduplicacion, banderas derivadas, normalizacion de textos.
  3) Agregacion por nivel geografico (provincia/distrito) y calculo de los
     7 indicadores analiticos (IND-01..IND-07) + embudo de seguimiento.
  4) Exporta dashboard_data.json que consume el dashboard web.

Ejecutar:  python etl_indicadores.py
"""
import os, re, json
import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # carpeta kiro/
OUT  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_data.json")

FILES = {
    "gestantes": (os.path.join(BASE, "DATOS_ABIERTOS_GESTANTES_ANEMIA_DIRESAJUNIN.csv"), "cp1252"),
    "cred":      (os.path.join(BASE, "NIÑAS Y NIÑOS DE 364 DÍAS DE EDAD, QUE CUENTAN CON ONCE (11) CONTROLES CRED.csv"), "utf-8-sig"),
    "ninos":     (os.path.join(BASE, "Niños_menores_de_36_meses_con_dx_de_anemia_en_la_Región_ Junín.csv"), "cp1252"),
}

# ----------------------------------------------------------------------
# Utilidades de transformacion
# ----------------------------------------------------------------------
def norm_txt(s):
    """TRIM + colapso de espacios + mayusculas para cruces consistentes."""
    if s is None:
        return ""
    s = re.sub(r"\s+", " ", str(s)).strip().upper()
    return s

def is_null(v):
    return v is None or str(v).strip().upper() in ("", "NULL", "NAN")

def sev_std(v):
    """UPPER + dominio {LEV,MOD,SEV}; fuera de dominio -> None."""
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

# ----------------------------------------------------------------------
# EXTRACCION
# ----------------------------------------------------------------------
def load(name):
    path, enc = FILES[name]
    df = pd.read_csv(path, sep=";", encoding=enc, dtype=str, keep_default_na=False)
    return df

print("== EXTRACCION ==")
g = load("gestantes"); print(f"  gestantes: {len(g)} filas")
c = load("cred");      print(f"  cred:      {len(c)} filas")
n = load("ninos");     print(f"  ninos:     {len(n)} filas")

# ----------------------------------------------------------------------
# TRANSFORMACION
# ----------------------------------------------------------------------
print("== TRANSFORMACION ==")

# --- Gestantes (DS1) ---
g["Provincia"] = g["Provincia"].map(norm_txt)
g["Distrito"]  = g["Distrito"].map(norm_txt)
g["severidad"] = g["valor_labo"].map(sev_std)
for k in range(1, 6):
    g[f"hb{k}_ok"] = g[f"hemoglobina_{k}"].map(lambda v: 0 if is_null(v) else 1)
g["flag_recuperada"] = g["fecha_7_recuperada"].map(lambda v: 0 if is_null(v) else 1)
dup_g = g.duplicated().sum()
g = g.drop_duplicates()
print(f"  gestantes: {dup_g} filas duplicadas eliminadas; severidad NULL={g['severidad'].isna().sum()}")

# --- CRED (DS2) ---
c["Provincia"] = c["Provincia"].map(norm_txt)
c["Distrito"]  = c["Distrito"].map(norm_txt)
for k in range(1, 12):
    c[f"cred{k}"] = (c[f"num_cred_mes{k}"] == "1").astype(int)
dup_c = c.duplicated().sum()
c = c.drop_duplicates()
print(f"  cred: {dup_c} filas duplicadas eliminadas")

# --- Ninos <36m (DS3) ---
n["Provincia"] = n["Provincia"].map(norm_txt)
n["Distrito"]  = n["Distrito"].map(norm_txt)
n["severidad"] = n["valor_lab_dx"].map(sev_std)
n["flag_recuperado"] = (n["recup"] == "1").astype(int)
for k in range(1, 6):  # T6 excluido (campo no operativo, sec 2.4)
    n[f"supT{k}_ok"] = n[f"fecha_supT{k}"].map(lambda v: 0 if is_null(v) else 1)
n["hb_dx_num"] = pd.to_numeric(n["hb_dx"].where(~n["hb_dx"].map(is_null)), errors="coerce")
dup_n = n.duplicated().sum()
n = n.drop_duplicates()
print(f"  ninos: {dup_n} filas duplicadas eliminadas; severidad NULL={n['severidad'].isna().sum()}")

# ----------------------------------------------------------------------
# INDICADORES  (definiciones del informe, sec 3.4)
# ----------------------------------------------------------------------
def pct(num, den):
    return round(100.0 * num / den, 1) if den else None

def indicadores_de(gg, cc, nn):
    """Calcula los 7 indicadores sobre subconjuntos (para global o por nivel)."""
    out = {}
    # IND-01 continuidad seguimiento Hb gestantes: dosaje5 / total gestantes
    tg = len(gg)
    out["ind01_continuidad_hb"] = pct(gg["hb5_ok"].sum(), tg) if tg else None
    # IND-02 tasa recuperacion gestantes
    out["ind02_recup_gestantes"] = pct(gg["flag_recuperada"].sum(), tg) if tg else None
    # IND-03 abandono CRED: (mes1 - mes11)/mes1
    m1 = cc["cred1"].sum(); m11 = cc["cred11"].sum()
    out["ind03_abandono_cred"] = pct(m1 - m11, m1) if m1 else None
    # IND-04 adherencia suplementacion (T5 / total ninos dx)
    tn = len(nn)
    out["ind04_adherencia_sup"] = pct(nn["supT5_ok"].sum(), tn) if tn else None
    # IND-05 recuperacion anemia infantil
    out["ind05_recup_ninos"] = pct(nn["flag_recuperado"].sum(), tn) if tn else None
    # IND-06 retencion del embudo (ultimo punto CRED sobre mes1 ya cubierto; aqui guardamos series)
    out["_tg"] = tg; out["_tn"] = tn; out["_m1"] = int(m1); out["_m11"] = int(m11)
    return out

def semaforo(ind05, ind03):
    """IND-07 nivel de alerta (reglas Tabla 3.7). Rojo si recup<30 o abandono>50;
       ambar si recup<50 o abandono>40; verde en otro caso."""
    if ind05 is None and ind03 is None:
        return "sin_datos"
    rojo  = (ind05 is not None and ind05 < 30) or (ind03 is not None and ind03 > 50)
    ambar = (ind05 is not None and ind05 < 50) or (ind03 is not None and ind03 > 40)
    if rojo:  return "rojo"
    if ambar: return "ambar"
    return "verde"

# ---- GLOBAL ----
G = indicadores_de(g, c, n)

# Embudo global (3 series de retencion Rk)
funnel = {
    "gestantes_dosaje": [int(g[f"hb{k}_ok"].sum()) for k in range(1, 6)],
    "cred_mes":         [int(c[f"cred{k}"].sum()) for k in range(1, 12)],
    "sup_toma":         [int(n[f"supT{k}_ok"].sum()) for k in range(1, 6)],
}

# Distribucion de severidad (para graficos)
def sev_dist(df):
    vc = df["severidad"].value_counts(dropna=False).to_dict()
    return {
        "LEV": int(vc.get("LEV", 0)),
        "MOD": int(vc.get("MOD", 0)),
        "SEV": int(vc.get("SEV", 0)),
        "NULL": int(df["severidad"].isna().sum()),
    }

# ---- POR NIVEL GEOGRAFICO ----
# La agregacion se hace por Provincia/Distrito (cruce geografico-institucional, sec 2.3.4)
def agg_geografico(nivel_cols):
    filas = []
    # universo de claves = union de las 3 tablas en esos niveles
    keys = pd.concat([
        g[nivel_cols], c[nivel_cols], n[nivel_cols]
    ]).drop_duplicates().reset_index(drop=True)
    for _, key in keys.iterrows():
        mask_g = np.ones(len(g), dtype=bool)
        mask_c = np.ones(len(c), dtype=bool)
        mask_n = np.ones(len(n), dtype=bool)
        for col in nivel_cols:
            mask_g &= (g[col] == key[col])
            mask_c &= (c[col] == key[col])
            mask_n &= (n[col] == key[col])
        gg, cc, nn = g[mask_g], c[mask_c], n[mask_n]
        ind = indicadores_de(gg, cc, nn)
        row = {col: key[col] for col in nivel_cols}
        row.update({
            "gestantes": int(len(gg)),
            "cred": int(len(cc)),
            "ninos": int(len(nn)),
            "ind01": ind["ind01_continuidad_hb"],
            "ind02": ind["ind02_recup_gestantes"],
            "ind03": ind["ind03_abandono_cred"],
            "ind04": ind["ind04_adherencia_sup"],
            "ind05": ind["ind05_recup_ninos"],
        })
        # IND-07 semaforo (con regla de denominador minimo 10 casos)
        den_min = ind["_tn"] >= 10
        row["alerta"] = semaforo(row["ind05"], row["ind03"]) if den_min else "sin_datos"
        filas.append(row)
    return filas

print("== AGREGACION GEOGRAFICA ==")
provincias = agg_geografico(["Provincia"])
distritos  = agg_geografico(["Provincia", "Distrito"])
print(f"  provincias: {len(provincias)} | distritos: {len(distritos)}")

# ----------------------------------------------------------------------
# SALIDA JSON
# ----------------------------------------------------------------------
data = {
    "meta": {
        "proyecto": "AnemiaCero Junin - Monitor de Seguimiento Integrado",
        "fuente": "DIRESA Junin - Plataforma Nacional de Datos Abiertos",
        "registros": {"gestantes": len(g), "cred": len(c), "ninos": len(n),
                      "total": len(g) + len(c) + len(n)},
    },
    "global": {
        "ind01_continuidad_hb":  G["ind01_continuidad_hb"],
        "ind02_recup_gestantes": G["ind02_recup_gestantes"],
        "ind03_abandono_cred":   G["ind03_abandono_cred"],
        "ind04_adherencia_sup":  G["ind04_adherencia_sup"],
        "ind05_recup_ninos":     G["ind05_recup_ninos"],
        "alerta": semaforo(G["ind05_recup_ninos"], G["ind03_abandono_cred"]),
    },
    "funnel": funnel,
    "severidad": {
        "gestantes": sev_dist(g),
        "ninos": sev_dist(n),
    },
    "provincias": sorted(provincias, key=lambda r: r["Provincia"]),
    "distritos": sorted(distritos, key=lambda r: (r["Provincia"], r["Distrito"])),
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# data.js embebido: permite abrir el dashboard con doble clic (sin servidor / sin CORS)
DATAJS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.js")
with open(DATAJS, "w", encoding="utf-8") as f:
    f.write("window.DASHBOARD_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")

print("\n== INDICADORES GLOBALES ==")
print(f"  IND-01 continuidad Hb gestantes (dosaje5): {G['ind01_continuidad_hb']}%")
print(f"  IND-02 recuperacion gestantes:             {G['ind02_recup_gestantes']}%")
print(f"  IND-03 abandono CRED:                      {G['ind03_abandono_cred']}%")
print(f"  IND-04 adherencia suplementacion (T5):     {G['ind04_adherencia_sup']}%")
print(f"  IND-05 recuperacion ninos:                 {G['ind05_recup_ninos']}%")
print(f"  IND-07 alerta global:                      {data['global']['alerta']}")
print(f"\nJSON generado: {OUT}")
