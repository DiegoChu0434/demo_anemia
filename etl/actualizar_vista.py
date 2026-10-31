# -*- coding: utf-8 -*-
"""Extiende el modelo integrando DS4 (nutricion) y DS5 (nacidos vivos):
   - Recrea mv_embudo_distrito agregando desnutricion cronica y cobertura de
     suplementacion (DS4, por id_ubicacion) a las columnas existentes.
   - Crea mv_nacimiento_provincia con los indicadores del CNV (DS5) agregados
     por provincia (el CNV solo cruza a nivel provincial).
   No altera las tablas de hecho; solo (re)crea vistas materializadas.
"""
import os
import psycopg2

def load_env():
    env = {}
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, ".env"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); env[k.strip()] = v.strip()
    return env

# mv_embudo_distrito extendida: conserva columnas originales + nutricion (DS4)
SQL_EMBUDO = """
DROP MATERIALIZED VIEW IF EXISTS mv_embudo_distrito;
CREATE MATERIALIZED VIEW mv_embudo_distrito AS
WITH g AS (
    SELECT id_ubicacion, COUNT(*) AS gestantes
    FROM hecho_gestante GROUP BY id_ubicacion
), c AS (
    SELECT id_ubicacion, COUNT(*) AS ninos_cred
    FROM hecho_cred GROUP BY id_ubicacion
), n AS (
    SELECT id_ubicacion, COUNT(*) AS ninos_anemia,
           AVG(CASE WHEN flag_recuperado=1 THEN 1.0 ELSE 0 END) AS tasa_recuperacion
    FROM hecho_nino_anemia GROUP BY id_ubicacion
), nut AS (
    SELECT id_ubicacion,
           COUNT(*) AS atenciones_nutri,
           AVG(CASE WHEN dcronica=1 THEN 1.0 ELSE 0 END) AS tasa_desnutricion_cronica,
           AVG(CASE WHEN supl_ok=1 THEN 1.0 ELSE 0 END)  AS tasa_cobertura_supl
    FROM hecho_cred_nutricion
    WHERE id_ubicacion IS NOT NULL
    GROUP BY id_ubicacion
)
SELECT u.provincia, u.distrito,
       COALESCE(g.gestantes,0)        AS gestantes,
       COALESCE(c.ninos_cred,0)       AS ninos_cred,
       COALESCE(n.ninos_anemia,0)     AS ninos_anemia,
       COALESCE(n.tasa_recuperacion,0) AS tasa_recuperacion,
       COALESCE(nut.atenciones_nutri,0)          AS atenciones_nutri,
       COALESCE(nut.tasa_desnutricion_cronica,0) AS tasa_desnutricion_cronica,
       COALESCE(nut.tasa_cobertura_supl,0)       AS tasa_cobertura_supl
FROM dim_ubicacion u
LEFT JOIN g   ON g.id_ubicacion   = u.id_ubicacion
LEFT JOIN c   ON c.id_ubicacion   = u.id_ubicacion
LEFT JOIN n   ON n.id_ubicacion   = u.id_ubicacion
LEFT JOIN nut ON nut.id_ubicacion = u.id_ubicacion;
"""

# mv_nacimiento_provincia: indicadores del CNV por provincia
SQL_NACIMIENTO = """
DROP MATERIALIZED VIEW IF EXISTS mv_nacimiento_provincia;
CREATE MATERIALIZED VIEW mv_nacimiento_provincia AS
SELECT provincia,
       COUNT(*) AS nacidos_vivos,
       ROUND(100.0*AVG(bajo_peso), 1)  AS pct_bajo_peso,
       ROUND(100.0*AVG(muy_bajo), 1)   AS pct_muy_bajo_peso,
       ROUND(100.0*AVG(prematuro), 1)  AS pct_prematuridad,
       ROUND(100.0*AVG(cesarea), 1)    AS pct_cesarea,
       ROUND(AVG(edad_madre) FILTER (WHERE edad_madre IS NOT NULL), 1) AS edad_madre_prom
FROM hecho_nacido_vivo
WHERE provincia <> ''
GROUP BY provincia
ORDER BY provincia;
"""

def main():
    conn = psycopg2.connect(load_env()["DATABASE_URL"])
    conn.autocommit = False
    cur = conn.cursor()
    try:
        cur.execute(SQL_EMBUDO)
        cur.execute(SQL_NACIMIENTO)
        conn.commit()
        print("== Vistas recreadas ==")
        cur.execute("SELECT COUNT(*) FROM mv_embudo_distrito;")
        print("  mv_embudo_distrito:", cur.fetchone()[0], "filas")
        cur.execute("SELECT COUNT(*) FROM mv_nacimiento_provincia;")
        print("  mv_nacimiento_provincia:", cur.fetchone()[0], "filas")
        print("\n== mv_nacimiento_provincia ==")
        cur.execute("SELECT provincia, nacidos_vivos, pct_bajo_peso, pct_prematuridad, pct_cesarea FROM mv_nacimiento_provincia;")
        print(f"  {'PROVINCIA':14s} {'NACIDOS':>8s} {'BAJO%':>6s} {'PREM%':>6s} {'CESAR%':>7s}")
        for r in cur.fetchall():
            print(f"  {r[0]:14s} {r[1]:>8,} {float(r[2]):>6.1f} {float(r[3]):>6.1f} {float(r[4]):>7.1f}")
    except Exception as e:
        conn.rollback()
        print("ERROR -> rollback:", e)
        raise
    finally:
        cur.close(); conn.close()

if __name__ == "__main__":
    main()
