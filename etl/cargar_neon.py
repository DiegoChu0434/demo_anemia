# -*- coding: utf-8 -*-
"""
Carga los dos datasets nuevos a la base Neon/PostgreSQL del proyecto AnemiaCero Junin:
  - hecho_cred_nutricion  (DS4 - Ninos JUNIN, estado nutricional en CRED)
  - hecho_nacido_vivo     (DS5 - Certificado de Nacido Vivo CNV, filtrado a Junin)

Sigue el patron del modelo en estrella ya existente (dim_ubicacion, dim_establecimiento,
hecho_cred, hecho_gestante, hecho_nino_anemia). Reutiliza la logica de limpieza de
etl/etl_indicadores.py (encoding por archivo, normalizacion de texto/diagnosticos,
filtro del CNV a Junin por ubigeo INEI 12, deduplicacion).

Uso:
    python etl/cargar_neon.py            # crea tablas (si no existen) y carga
    python etl/cargar_neon.py --recreate # DROP + CREATE + carga (reemplaza datos)

La cadena de conexion se lee de DATABASE_URL en el archivo .env (no se versiona).
"""
import os
import re
import sys
import unicodedata
import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_values

# -------------------- rutas y entorno --------------------
PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(PROYECTO, "data", "raw")

CREDN_CSV = os.path.join(RAW_DIR, "Niños JUNIN.csv")
CNV_CSV = os.path.join(RAW_DIR, "CNV_MINSA_CORTE_30112025.csv")

UBIGEO_PROV = {
    "01": "HUANCAYO", "02": "CONCEPCION", "03": "CHANCHAMAYO", "04": "JAUJA",
    "05": "JUNIN", "06": "SATIPO", "07": "TARMA", "08": "YAULI", "09": "CHUPACA",
}


def load_env():
    env = {}
    with open(os.path.join(PROYECTO, ".env"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


# -------------------- helpers de limpieza (del ETL) --------------------
def strip_acentos(s):
    return "".join(ch for ch in unicodedata.normalize("NFD", s)
                   if unicodedata.category(ch) != "Mn")


def norm_txt(s):
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s)).strip().upper()


def norm_key(s):
    return strip_acentos(norm_txt(s))


def is_null(v):
    return v is None or str(v).strip().upper() in ("", "NULL", "NAN")


def num(serie):
    return pd.to_numeric(
        serie.astype(str).str.strip().str.replace(",", ".", regex=False),
        errors="coerce")


def to_iso(v):
    """Fecha a ISO. DS4 usa m/d/Y (ej 3/15/2025); intentamos ambos ordenes."""
    if is_null(v):
        return None
    for fmt in ("%m/%d/%Y", "%d/%m/%Y"):
        d = pd.to_datetime(v, format=fmt, errors="coerce")
        if not pd.isna(d):
            return d.strftime("%Y-%m-%d")
    d = pd.to_datetime(v, errors="coerce", dayfirst=False)
    return None if pd.isna(d) else d.strftime("%Y-%m-%d")


def ival(v):
    """int o None."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def fval(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    try:
        f = float(v)
        return None if np.isnan(f) else f
    except (ValueError, TypeError):
        return None


# -------------------- DDL --------------------
DDL_CREDN = """
CREATE TABLE IF NOT EXISTS hecho_cred_nutricion (
    id_atencion     SERIAL PRIMARY KEY,
    renaes          VARCHAR(10) REFERENCES dim_establecimiento(renaes),
    id_ubicacion    INTEGER REFERENCES dim_ubicacion(id_ubicacion),
    provincia       VARCHAR(60),
    distrito        VARCHAR(60),
    fecha_atencion  DATE,
    sexo            VARCHAR(12),
    edad_meses      NUMERIC(5,2),
    peso            NUMERIC(6,2),
    talla           NUMERIC(6,2),
    ptz             NUMERIC(6,2),
    zte             NUMERIC(6,2),
    zpe             NUMERIC(6,2),
    dx_pt           VARCHAR(20),
    dx_te           VARCHAR(20),
    dx_pe           VARCHAR(20),
    dcronica        SMALLINT DEFAULT 0,
    dglobal         SMALLINT DEFAULT 0,
    daguda          SMALLINT DEFAULT 0,
    cred_ok         SMALLINT DEFAULT 0,
    supl_ok         SMALLINT DEFAULT 0,
    consej_ok       SMALLINT DEFAULT 0,
    juntos          SMALLINT DEFAULT 0,
    sis             SMALLINT DEFAULT 0,
    qaliwarma       SMALLINT DEFAULT 0
);
"""

DDL_CNV = """
CREATE TABLE IF NOT EXISTS hecho_nacido_vivo (
    id_cnv                  SERIAL PRIMARY KEY,
    id_ubicacion            INTEGER REFERENCES dim_ubicacion(id_ubicacion),
    provincia               VARCHAR(60),
    fecnac_anio             SMALLINT,
    fecnac_mes              SMALLINT,
    peso_nacido             INTEGER,
    talla_nacido            NUMERIC(5,1),
    bajo_peso               SMALLINT DEFAULT 0,
    muy_bajo                SMALLINT DEFAULT 0,
    dur_emb_parto           SMALLINT,
    prematuro               SMALLINT DEFAULT 0,
    condicion_parto         VARCHAR(30),
    cesarea                 SMALLINT DEFAULT 0,
    sexo_nacido             VARCHAR(15),
    tipo_parto              VARCHAR(20),
    edad_madre              SMALLINT,
    adolescente             SMALLINT DEFAULT 0,
    estado_civil            VARCHAR(30),
    nivel_instruccion_madre VARCHAR(60),
    financiador_parto       VARCHAR(30)
);
"""

DROP = """
DROP TABLE IF EXISTS hecho_cred_nutricion CASCADE;
DROP TABLE IF EXISTS hecho_nacido_vivo CASCADE;
"""


# -------------------- carga DS4 (nutricion) --------------------
def cargar_credn(cur):
    print("\n== DS4 Estado nutricional (Ninos JUNIN) ==")
    cn = pd.read_csv(CREDN_CSV, sep=",", encoding="utf-8",
                     dtype=str, keep_default_na=False)
    print(f"  leidas: {len(cn)} filas, {len(cn.columns)} columnas")

    cn["Provincia"] = cn["Prov_EESS"].map(norm_txt)
    cn["Distrito"] = cn["Dist_EESS"].map(norm_txt)
    cn["cred_ok"] = (cn["Cred"].str.strip() == "1").astype(int)
    cn["supl_ok"] = (cn["Suplementacion"].str.strip() == "1").astype(int)
    cn["consej_ok"] = (cn["Consejeria"].str.strip() == "1").astype(int)
    cn["juntos"] = (cn["Juntos"].str.strip() == "1").astype(int)
    cn["sis"] = (cn["SIS"].str.strip() == "1").astype(int)
    cn["qaliwarma"] = (cn["Qaliwarma"].str.strip() == "1").astype(int)
    cn["dcronica"] = cn["Dx_TE"].map(norm_key).str.contains("CRONICA").astype(int)
    cn["dglobal"] = cn["Dx_PE"].map(norm_key).str.contains("GLOBAL").astype(int)
    cn["daguda"] = cn["Dx_PT"].map(norm_key).str.contains("AGUDA").astype(int)
    dup = cn.duplicated().sum()
    cn = cn.drop_duplicates().reset_index(drop=True)
    print(f"  duplicadas eliminadas: {dup} -> quedan {len(cn)}")

    # mapa renaes -> id_ubicacion desde dim_establecimiento
    cur.execute("SELECT renaes, id_ubicacion FROM dim_establecimiento;")
    renaes2ub = {r[0]: r[1] for r in cur.fetchall()}
    # set de renaes validos (FK)
    renaes_validos = set(renaes2ub.keys())

    filas = []
    sin_renaes = 0
    for _, r in cn.iterrows():
        renaes = str(r["Renipress"]).strip()
        if renaes not in renaes_validos:
            renaes_db = None  # no forzamos FK invalida
            idub = None
            sin_renaes += 1
        else:
            renaes_db = renaes
            idub = renaes2ub.get(renaes)
        filas.append((
            renaes_db, idub, r["Provincia"], r["Distrito"],
            to_iso(r["FechaAtencion"]), norm_txt(r["Sexo"]),
            fval(num(pd.Series([r["EdadMeses"]]))[0]),
            fval(num(pd.Series([r["Peso"]]))[0]),
            fval(num(pd.Series([r["Talla"]]))[0]),
            fval(num(pd.Series([r["PTZ"]]))[0]),
            fval(num(pd.Series([r["ZTE"]]))[0]),
            fval(num(pd.Series([r["ZPE"]]))[0]),
            r["Dx_PT"].strip()[:20] or None,
            r["Dx_TE"].strip()[:20] or None,
            r["Dx_PE"].strip()[:20] or None,
            int(r["dcronica"]), int(r["dglobal"]), int(r["daguda"]),
            int(r["cred_ok"]), int(r["supl_ok"]), int(r["consej_ok"]),
            int(r["juntos"]), int(r["sis"]), int(r["qaliwarma"]),
        ))
    print(f"  renipress sin match en dim_establecimiento: {sin_renaes}")

    cols = ("renaes,id_ubicacion,provincia,distrito,fecha_atencion,sexo,edad_meses,"
            "peso,talla,ptz,zte,zpe,dx_pt,dx_te,dx_pe,dcronica,dglobal,daguda,"
            "cred_ok,supl_ok,consej_ok,juntos,sis,qaliwarma")
    execute_values(cur,
        f"INSERT INTO hecho_cred_nutricion ({cols}) VALUES %s",
        filas, page_size=5000)
    print(f"  INSERTADAS: {len(filas)} filas en hecho_cred_nutricion")
    return len(filas)


# -------------------- carga DS5 (CNV) --------------------
def cargar_cnv(cur):
    print("\n== DS5 Nacidos vivos (CNV) - filtrando a Junin por chunks ==")
    partes = []
    reader = pd.read_csv(CNV_CSV, sep=";", dtype=str, keep_default_na=False,
                         encoding="utf-8", encoding_errors="replace",
                         on_bad_lines="skip", engine="c", chunksize=200000)
    total_leidas = 0
    for ch in reader:
        total_leidas += len(ch)
        ub = ch["IdUbigeoInei"].astype(str).str.strip()
        jun = ch[ub.str.startswith("12")].copy()
        if len(jun):
            partes.append(jun)
    cv = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
    print(f"  leidas {total_leidas:,} filas (nacional) -> {len(cv):,} de Junin")
    if not len(cv):
        print("  SIN datos de Junin, nada que cargar.")
        return 0

    ub = cv["IdUbigeoInei"].astype(str).str.strip().str.zfill(6)
    cv["Provincia"] = ub.str[2:4].map(UBIGEO_PROV).fillna("")
    peso = num(cv["PESO_NACIDO"])
    # peso <= 0 es centinela de "sin dato": no cuenta como bajo/muy bajo peso
    peso = peso.where(peso > 0)
    dur = num(cv["DUR_EMB_PARTO"])
    dur = dur.where(dur > 0)
    edad = num(cv["Edad_Madre"])
    edad = edad.where(edad > 0)
    cond = cv["Condicion_Parto"].map(norm_key)
    cv["peso_num"] = peso
    cv["bajo_peso"] = ((peso >= 0) & (peso < 2500)).fillna(False).astype(int)
    cv["muy_bajo"] = ((peso >= 0) & (peso < 1500)).fillna(False).astype(int)
    cv["prematuro"] = ((dur >= 0) & (dur < 37)).fillna(False).astype(int)
    cv["cesarea"] = (cond == "CESAREA").astype(int)
    cv["edad_m"] = edad
    cv["adolescente"] = (edad < 18).astype(int)
    dup = cv.duplicated().sum()
    cv = cv.drop_duplicates().reset_index(drop=True)
    print(f"  duplicadas eliminadas: {dup} -> quedan {len(cv):,}")

    # id_ubicacion representativo por provincia (el menor id de esa provincia)
    cur.execute("SELECT provincia, MIN(id_ubicacion) FROM dim_ubicacion GROUP BY provincia;")
    prov2ub = {r[0]: r[1] for r in cur.fetchall()}

    tall = num(cv["TALLA_NACIDO"])
    filas = []
    for i, r in cv.iterrows():
        prov = r["Provincia"]
        filas.append((
            prov2ub.get(prov), prov,
            ival(num(pd.Series([r["FecNac_Año"]]))[0]),
            ival(num(pd.Series([r["FecNac_Mes"]]))[0]),
            ival(r["peso_num"]),
            fval(tall.iloc[i]),
            int(r["bajo_peso"]), int(r["muy_bajo"]),
            ival(num(pd.Series([r["DUR_EMB_PARTO"]]))[0]),
            int(r["prematuro"]),
            norm_txt(r["Condicion_Parto"])[:30] or None,
            int(r["cesarea"]),
            norm_txt(r["sexo_nacido"])[:15] or None,
            norm_txt(r["Tipo_Parto"])[:20] or None,
            ival(r["edad_m"]), int(r["adolescente"]),
            norm_txt(r["Estado_Civil"])[:30] or None,
            norm_txt(r["Nivel_Intrucción_Madre"])[:60] or None,
            norm_txt(r["Financiador_Parto"])[:30] or None,
        ))

    cols = ("id_ubicacion,provincia,fecnac_anio,fecnac_mes,peso_nacido,talla_nacido,"
            "bajo_peso,muy_bajo,dur_emb_parto,prematuro,condicion_parto,cesarea,"
            "sexo_nacido,tipo_parto,edad_madre,adolescente,estado_civil,"
            "nivel_instruccion_madre,financiador_parto")
    execute_values(cur,
        f"INSERT INTO hecho_nacido_vivo ({cols}) VALUES %s",
        filas, page_size=10000)
    print(f"  INSERTADAS: {len(filas):,} filas en hecho_nacido_vivo")
    return len(filas)


# -------------------- main --------------------
def main():
    recreate = "--recreate" in sys.argv
    dsn = load_env()["DATABASE_URL"]
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        if recreate:
            print("== DROP tablas nuevas (--recreate) ==")
            cur.execute(DROP)
        cur.execute(DDL_CREDN)
        cur.execute(DDL_CNV)
        print("== DDL aplicado (tablas creadas si no existian) ==")

        # evitar duplicar si ya tienen datos y no es recreate
        cur.execute("SELECT COUNT(*) FROM hecho_cred_nutricion;")
        n_cn = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM hecho_nacido_vivo;")
        n_cv = cur.fetchone()[0]
        if (n_cn or n_cv) and not recreate:
            print(f"\nLas tablas ya tienen datos (nutricion={n_cn}, nacidos={n_cv}).")
            print("Usa --recreate para reemplazarlos. No se cargo nada.")
            conn.rollback()
            return

        c1 = cargar_credn(cur)
        c2 = cargar_cnv(cur)
        conn.commit()

        print("\n== VERIFICACION ==")
        for t in ("hecho_cred_nutricion", "hecho_nacido_vivo"):
            cur.execute(f"SELECT COUNT(*) FROM {t};")
            print(f"  {t}: {cur.fetchone()[0]:,} filas")
        print("\nCarga COMPLETA y confirmada (commit).")
    except Exception as e:
        conn.rollback()
        print("\nERROR -> rollback. Detalle:", e)
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
