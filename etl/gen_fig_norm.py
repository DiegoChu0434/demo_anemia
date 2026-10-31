# -*- coding: utf-8 -*-
"""Figura 3.2 actualizada: proceso de normalizacion con las 5 tablas de hecho
(incluye hecho_cred_nutricion y hecho_nacido_vivo). Estilo consistente:
caja roja (crudo) -> dimensiones azules -> hechos verdes, flechas 1FN/2FN/3FN."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "etl", "_media_tmp", "nuevo_norm.png")

ROJO="#8E1B4B"; ROJO_BG="#F7D9E3"
AZUL="#1F4E79"; AZUL_BG="#C5D9F1"
VERDE="#2E7D32"; VERDE_BG="#D6E9D4"

fig, ax = plt.subplots(figsize=(20, 11.5), dpi=150)
ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis("off")

def caja(x, y, w, h, titulo, lineas, color, bg, tsize=12, lsize=9.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=0.8",
                 facecolor=bg, edgecolor=color, linewidth=1.8, zorder=2))
    ax.text(x+w/2, y+h-1.6, titulo, ha="center", va="top", color=color,
            fontsize=tsize, fontweight="bold", zorder=3)
    ax.text(x+w/2, y+h-4.0, "\n".join(lineas), ha="center", va="top", color="#222",
            fontsize=lsize, zorder=3, linespacing=1.4)

ax.text(50, 58.3, "Figura 3.2 · Proceso de normalización del modelo AnemiaCero Junín",
        ha="center", fontsize=16, fontweight="bold", color=AZUL)
ax.text(30, 54.5, "Dimensiones (datos maestros, sin redundancia)", ha="center",
        fontsize=10.5, style="italic", color=AZUL)
ax.text(85, 55.3, "Hechos (una fila por evento)", ha="center",
        fontsize=10.5, style="italic", color=VERDE)

# --- caja roja: dato crudo ---
caja(1, 20, 24, 28, "Dato crudo (CSV)\nTabla plana · redundante", [
    "renaes", "nombre_establecimiento · categoria",
    "provincia · distrito · red · micro-red", "",
    "severidad · hb_dx · dx_te · dx_pe",
    "peso_nacido · dur_emb · cesarea", "fecha_dx · recup · supT1..T6", "",
    "(5 datasets: gestantes, CRED,", "niños anemia, nutrición CRED, CNV)", "",
    "! la geografía se repite en cada fila"], ROJO, ROJO_BG, lsize=8.8)

# --- dimensiones (azul) ---
caja(30, 40, 26, 11, "dim_ubicacion  (3FN)", [
    "id_ubicacion  PK", "provincia · distrito",
    "red · micro-red · ubigeo"], AZUL, AZUL_BG)
caja(30, 20, 26, 11, "dim_establecimiento  (3FN)", [
    "renaes  PK", "nombre · categoria", "id_ubicacion  FK"], AZUL, AZUL_BG)
# flecha ubicacion -> establecimiento
ax.add_line(Line2D([43,43],[40,31], color=AZUL, linewidth=1.8, zorder=1))
ax.annotate("", xy=(43,31), xytext=(43,33),
            arrowprops=dict(arrowstyle="-|>", color=AZUL, lw=1.8))

# --- flechas 1FN/2FN/3FN desde el crudo ---
for yy, lbl, col, sub in [
    (44, "1FN", ROJO, "atomicidad: separa\ngrupos repetitivos"),
    (34, "2FN", "#555", "separa datos que\ndependen del establec."),
    (24, "3FN", VERDE, "separa geografía\n→ dimensiones")]:
    ax.annotate("", xy=(30, yy), xytext=(25, yy),
                arrowprops=dict(arrowstyle="-|>", color=col, lw=2.0))
    ax.text(27.5, yy+1.4, lbl, ha="center", fontsize=11, fontweight="bold",
            style="italic", color=col)
    ax.text(27.5, yy-2.2, sub, ha="center", fontsize=7.6, color=col, linespacing=1.2)

# --- hechos (verde): 5 tablas ---
hx = 72; hw = 26
hechos = [
    (46.5, "hecho_gestante", "id_gestante PK · renaes FK\nseveridad · hb_1..5"),
    (37.0, "hecho_cred", "id_cred PK · renaes FK\ncred_mes1..11"),
    (27.5, "hecho_nino_anemia", "id_nino PK · renaes FK\nseveridad · hb_dx · supT1..6"),
    (18.0, "hecho_cred_nutricion", "id_atencion PK · renaes FK\ndx_te · dcronica · supl_ok"),
    (8.5,  "hecho_nacido_vivo", "id_cnv PK · id_ubicacion FK\npeso_nacido · prematuro · cesarea"),
]
for i, (yy, nom, det) in enumerate(hechos):
    nuevo = i >= 3
    col = VERDE
    caja(hx, yy, hw, 8, nom, [det], col, VERDE_BG, tsize=11, lsize=8.6)
    # flecha desde dim_establecimiento (o dim_ubicacion para el ultimo)
    orig_x, orig_y = (56, 25.5)
    if nom == "hecho_nacido_vivo":
        orig_x, orig_y = (56, 45.5)  # depende de ubicacion
    ax.add_line(Line2D([orig_x, hx], [orig_y, yy+4], color=AZUL, linewidth=1.3, zorder=1))
    ax.annotate("", xy=(hx, yy+4), xytext=(hx-2, yy+4),
                arrowprops=dict(arrowstyle="-|>", color=AZUL, lw=1.3))

# marca de los nuevos
ax.text(85, 2.6, "Tablas de hecho añadidas con los datasets integrados (DS4 y DS5)",
        ha="center", fontsize=9, style="italic", color=VERDE)
ax.add_line(Line2D([71,99],[4.0,4.0], color=VERDE, linewidth=1.0, linestyle="--"))

plt.tight_layout()
fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
print("Normalizacion generada:", OUT)
