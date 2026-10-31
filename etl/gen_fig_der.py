# -*- coding: utf-8 -*-
"""Genera el nuevo Diagrama de Clases / DER (Figura 3.1) con las 5 tablas de
hecho (incluye los 2 datasets nuevos). Estilo consistente con el original:
encabezado azul oscuro, cuerpo gris claro, relaciones con cardinalidad."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.lines import Line2D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "etl", "_media_tmp", "nuevo_der.png")

AZUL = "#1F3864"
GRIS = "#DCE3EF"
BORDE = "#1F3864"
TXT = "#20252e"

fig, ax = plt.subplots(figsize=(20, 11.5), dpi=150)
ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis("off")

def entidad(x, y, w, titulo, campos, hh=3.0):
    """Dibuja una clase/entidad. (x,y) esquina sup-izq."""
    rh = len(campos) * 1.55 + 1.2
    # cuerpo
    ax.add_patch(Rectangle((x, y - rh - hh), w, rh, facecolor=GRIS,
                           edgecolor=BORDE, linewidth=1.3, zorder=2))
    # encabezado
    ax.add_patch(Rectangle((x, y - hh), w, hh, facecolor=AZUL,
                           edgecolor=BORDE, linewidth=1.3, zorder=3))
    ax.text(x + w/2, y - hh/2, titulo, ha="center", va="center",
            color="white", fontsize=12.5, fontweight="bold", zorder=4)
    for i, c in enumerate(campos):
        ax.text(x + 0.8, y - hh - 1.2 - i*1.55, "+ " + c, ha="left", va="center",
                color=TXT, fontsize=9.2, family="monospace", zorder=4)
    return (x, y, w, rh + hh)  # bbox

def rel(p1, p2, etiqueta, c1="1", c2="N"):
    ax.add_line(Line2D([p1[0], p2[0]], [p1[1], p2[1]], color=AZUL,
                       linewidth=1.3, zorder=1))
    mx, my = (p1[0]+p2[0])/2, (p1[1]+p2[1])/2
    ax.text(mx, my+1.0, etiqueta, ha="center", va="center", fontsize=9,
            style="italic", color="#555")
    ax.text(p1[0], p1[1]+0.6, c1, fontsize=8.5, color="#555", ha="center")
    ax.text(p2[0]-1.2, p2[1]+1.0, c2, fontsize=8.5, color="#555", ha="center")

ax.text(50, 58.3, "Figura 3.1 · Diagrama de Clases — Modelo de Datos AnemiaCero Junín",
        ha="center", fontsize=16, fontweight="bold", color=AZUL)

# --- fila superior: dimensiones ---
ubic = entidad(3, 54, 26,  "Ubicacion", [
    "id_ubicacion: SERIAL (PK)", "provincia: VARCHAR", "distrito: VARCHAR",
    "red / microred: VARCHAR", "departamento: VARCHAR", "ubigeo: VARCHAR"])
esta = entidad(37, 55.5, 28, "Establecimiento", [
    "renaes: VARCHAR (PK)", "id_establecimiento: VARCHAR",
    "nombre_establecimiento", "categoria: VARCHAR", "cod_disa / disa",
    "id_ubicacion: INT (FK)"])

# relacion Ubicacion 1 - N Establecimiento
rel((29, 46), (37, 46.5), "ubica", "1", "N")

# --- fila inferior: 5 tablas de hecho ---
y2 = 30
gest = entidad(1,  y2, 18, "Gestante", [
    "id_gestante: SERIAL (PK)", "renaes: VARCHAR (FK)", "severidad: VARCHAR",
    "fecha_dx: DATE", "hemoglobina_1..5", "flag_recuperada"])
cred = entidad(21, y2, 18, "ControlCred", [
    "id_cred: SERIAL (PK)", "renaes: VARCHAR (FK)", "anio / mes: INT",
    "fecha_cred_mes1..11", "num_cred_mes1..11"])
nino = entidad(41, y2, 18, "NinoAnemia", [
    "id_nino: SERIAL (PK)", "renaes: VARCHAR (FK)", "severidad: VARCHAR",
    "hb_dx: NUMERIC", "flag_recuperado", "fecha_supT1..T6"])
# NUEVAS
crn = entidad(61, y2, 18, "CredNutricion", [
    "id_atencion: SERIAL (PK)", "renaes: VARCHAR (FK)", "edad_meses: INT",
    "dx_te / dx_pe / dx_pt", "dcronica (0/1)", "supl_ok (0/1)"])
nac = entidad(81, y2, 18, "NacidoVivo", [
    "id_cnv: SERIAL (PK)", "id_ubicacion: INT (FK)", "peso_nacido: NUMERIC",
    "bajo_peso (0/1)", "prematuro (0/1)", "cesarea (0/1)"])

# relaciones Establecimiento 1 - N (gest, cred, nino, credn)
for ent, lbl in [(gest,"atiende"),(cred,"atiende"),(nino,"atiende"),(crn,"atiende")]:
    ex = ent[0] + ent[2]/2
    rel((51, 46), (ex, 30.3), lbl, "1", "N")
# NacidoVivo depende de Ubicacion (no de Establecimiento).
# Sale desde el borde derecho de Ubicacion para no cruzar el bloque de hechos.
nx = nac[0] + nac[2]/2
ax.add_line(Line2D([29, nx], [48, 30.3], color=AZUL, linewidth=1.3, zorder=1))
ax.text((29+nx)/2, 40.5, "registra", ha="center", va="center", fontsize=9,
        style="italic", color="#555")
ax.text(29.4, 48.6, "1", fontsize=8.5, color="#555", ha="center")
ax.text(nx-1.2, 31.3, "N", fontsize=8.5, color="#555", ha="center")

# leyenda etiqueta de las nuevas
ax.text(70, 11.5, "Tablas de hecho añadidas con los datasets integrados (DS4 y DS5)",
        ha="center", fontsize=9.5, style="italic", color="#2E7D32")
ax.add_line(Line2D([60.5,99],[12.8,12.8], color="#2E7D32", linewidth=1.0, linestyle="--"))

plt.tight_layout()
fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
print("DER generado:", OUT)
