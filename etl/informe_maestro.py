# -*- coding: utf-8 -*-
"""
Script MAESTRO: incorpora los 2 datasets nuevos al Informe_Final.docx partiendo
del ORIGINAL (3 datasets), en el orden correcto y con formato consistente.
Robusto: nunca reutiliza un Paragraph devuelto por una insercion previa; relocaliza
cada ancla por texto; y para la seccion final usa addprevious() sobre BIBLIOGRAFIA.
"""
import io, sys, os, copy
from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import _Row, Table
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "Informe_Final.docx")
doc = Document(SRC)

# -------------------- helpers --------------------
def P(i): return doc.paragraphs[i]

def idx_prefix(prefix, start=0, end=None):
    end = end if end is not None else len(doc.paragraphs)
    for i in range(start, end):
        if doc.paragraphs[i].text.strip().startswith(prefix):
            return i
    return -1

def idx_exact(text, start=0, end=None):
    end = end if end is not None else len(doc.paragraphs)
    for i in range(start, end):
        if doc.paragraphs[i].text.strip() == text.strip():
            return i
    return -1

def par_prefix(prefix, start=0):
    i = idx_prefix(prefix, start)
    if i < 0: raise ValueError("No encontrado (prefix): " + prefix)
    return doc.paragraphs[i]

def _blank_clone(ref_par):
    new_p = copy.deepcopy(ref_par._p)
    for r in new_p.findall(qn('w:r')): new_p.remove(r)
    for el in new_p.findall(qn('w:hyperlink')): new_p.remove(el)
    return new_p

def insert_paragraphs_after(ref_par, items, index_font_from=None):
    last = ref_par._p
    for text, style in items:
        new_p = _blank_clone(ref_par)
        last.addnext(new_p); last = new_p
        p = Paragraph(new_p, ref_par._parent)
        if style: p.style = doc.styles[style]
        if text:
            r = p.add_run(text)
            if index_font_from is not None and index_font_from.runs:
                s = index_font_from.runs[0]
                r.font.name = s.font.name; r.font.size = s.font.size
                r.font.bold = s.font.bold; r.font.italic = s.font.italic
    return last

def find_table(h):
    for tb in doc.tables:
        if not tb.rows: continue
        cells = " | ".join(c.text.strip() for c in tb.rows[0].cells)
        if cells.startswith(h): return tb
    raise ValueError("Tabla no encontrada: " + h)

def append_rows(tb, rows):
    ncol = len(tb.columns)
    for vals in rows:
        tr = copy.deepcopy(tb.rows[-1]._tr)
        tb._tbl.append(tr)
        row = _Row(tr, tb)
        for ci in range(ncol):
            p0 = row.cells[ci].paragraphs[0]
            for r in list(p0.runs): r.text = ""
            for extra in row.cells[ci].paragraphs[1:]:
                extra._p.getparent().remove(extra._p)
            v = vals[ci] if ci < len(vals) else ""
            (p0.runs[0].text if p0.runs else None)
            if p0.runs: p0.runs[0].text = v
            else: p0.add_run(v)

def mk_par(text, model_par, style):
    new_p = _blank_clone(model_par)
    p = Paragraph(new_p, model_par._parent)
    p.style = doc.styles[style]
    if text: p.add_run(text)
    return new_p

def mk_table(model_table, rows):
    tbl_el = copy.deepcopy(model_table._tbl)
    for tr in tbl_el.findall(qn('w:tr')): tbl_el.remove(tr)
    t = Table(tbl_el, doc.paragraphs[0]._parent)
    ncol = len(model_table.columns)
    src_rows = model_table.rows
    for ri, rowvals in enumerate(rows):
        model_tr = src_rows[0]._tr if ri == 0 else src_rows[min(1, len(src_rows)-1)]._tr
        tr = copy.deepcopy(model_tr); tbl_el.append(tr)
        row = _Row(tr, t)
        for ci in range(ncol):
            p0 = row.cells[ci].paragraphs[0]
            for r in list(p0.runs): r.text = ""
            for extra in row.cells[ci].paragraphs[1:]:
                extra._p.getparent().remove(extra._p)
            v = rowvals[ci] if ci < len(rowvals) else ""
            if p0.runs: p0.runs[0].text = v
            else: p0.add_run(v)
    return tbl_el

print("Base:", len(doc.paragraphs), "parrafos,", len(doc.tables), "tablas")

# El INDICE (texto plano) ocupa el inicio. El cuerpo real empieza en el
# encabezado "CAPÍTULO 1 - ASPECTOS GENERALES" (con "1", no romano "I").
BODY0 = idx_prefix("CAPÍTULO 1", start=60)
if BODY0 < 0:
    BODY0 = idx_prefix("CAPÍTULO I - ASPECTOS GENERALES", start=64)
print("  cuerpo inicia en parrafo", BODY0)

# ===== A) Descripcion DS4/DS5 (tras Dataset 3, antes de 2.3) =====
anchor = P(idx_prefix("2.3 Análisis exploratorio", start=BODY0) - 1)
insert_paragraphs_after(anchor, [
 ("Dataset 4: Niños de Junín con Controles CRED y Estado Nutricional", "Normal"),
 ("Contiene 76,064 atenciones de niños menores de 5 años (padrón nominal de la Región Junín) con "
  "su evaluación antropométrica y nutricional. Complementa al Dataset 2 aportando el resultado "
  "nutricional del control, no solo su cobertura.", "Normal"),
 ("Estructura (41 columnas):", "Normal"),
 ("Identificación geográfica del establecimiento: Diresa, Red, Microred, EESS, Dpto_EESS, "
  "Prov_EESS, Dist_EESS, Ubigeo_EESS, Renipress.", "List Paragraph"),
 ("Identificación del niño: Sexo, FechaNacimiento, EdadMeses (0 a 60) y residencia.", "List Paragraph"),
 ("Antropometría: Peso, Talla y puntajes Z (PTZ peso/talla, ZTE talla/edad, ZPE peso/edad).", "List Paragraph"),
 ("Diagnósticos nutricionales: Dx_PT (peso/talla), Dx_TE (talla/edad: desnutrición crónica) y "
  "Dx_PE (peso/edad: desnutrición global).", "List Paragraph"),
 ("Atención y programas sociales: Cred, Suplementacion, Consejeria, Sesion (0/1) y Juntos, SIS, "
  "Qaliwarma.", "List Paragraph"),
 ("Clave de unicidad: Renipress + FechaNacimiento + FechaAtencion. Todo el dataset pertenece al "
  "departamento de Junín (Dpto_EESS = JUNIN en los 76,064 registros).", "List Paragraph"),
 ("Dataset 5: Certificado de Nacido Vivo (CNV – MINSA)", "Normal"),
 ("Padrón nacional de certificados de nacido vivo con corte al 30/11/2025. El archivo completo "
  "tiene aproximadamente 4.87 millones de registros (unos 832 MB); para este proyecto se filtró al "
  "departamento de Junín (ubigeo INEI con prefijo 12), obteniéndose 210,808 nacimientos del "
  "período 2015–2025. Aporta el punto de partida del embudo: las condiciones del nacimiento y el "
  "perfil de la madre.", "Normal"),
 ("Estructura (22 columnas):", "Normal"),
 ("Datos del nacimiento: FecNac_Año, FecNac_Mes, PESO_NACIDO (g), TALLA_NACIDO (cm), DUR_EMB_PARTO "
  "(semanas), Condicion_Parto (eutócico/cesárea/instrumentado), Tipo_Parto, sexo_nacido.", "List Paragraph"),
 ("Perfil de la madre: Edad_Madre, Estado_Civil, Nivel_Intrucción_Madre, DESC_OCUPACION, "
  "Num_embar_madre, Hijos_vivo_madre, Hijos_fallec_madre, nacmuer_abort_madre, Pais_Madre.", "List Paragraph"),
 ("Geografía e institución: IdUbigeoInei, Ipress, Lugar_Nacido, Atiende_Parto, Financiador_Parto.", "List Paragraph"),
 ("Clave de integración: al no tener código RENAES ni nombre de distrito, el cruce con el resto de "
  "datasets se hace a nivel de provincia mediante el ubigeo INEI, coherente con la estrategia de "
  "integración geográfico-institucional del proyecto.", "List Paragraph"),
])
print("A) OK")

# ===== B) Analisis exploratorio 2.3.5/2.3.6 DESPUES de 2.3.4 =====
anchor = P(idx_prefix("2.4 Problemas de calidad de datos", start=BODY0) - 1)
insert_paragraphs_after(anchor, [
 ("2.3.5 Análisis del Dataset de Estado Nutricional en CRED (76,064 atenciones)", "Heading 3"),
 ("Distribución del estado nutricional del niño al momento del control:", "Normal"),
 ("Estado normal: 59,186 atenciones (77.8%)", "List Paragraph"),
 ("Desnutrición crónica (talla/edad baja): 15,375 casos (20.2%)", "List Paragraph"),
 ("Desnutrición global (peso/edad bajo): 4,426 casos (5.8%)", "List Paragraph"),
 ("Desnutrición aguda (peso/talla bajo): 1,481 casos (1.9%)", "List Paragraph"),
 ("La desnutrición crónica es la forma predominante: afecta a 1 de cada 5 niños evaluados en "
  "Junín. Es un problema estructural asociado a la pobreza y la altitud, y guarda relación directa "
  "con la anemia que monitorea el resto del sistema.", "Normal"),
 ("Cobertura de intervenciones: suplementación con hierro en el 45.6% de las atenciones y control "
  "CRED registrado en el 76.9%. La consejería nutricional aparece en una fracción menor de "
  "registros, lo que sugiere subregistro de esa actividad.", "Normal"),
 ("Cobertura geográfica: 9 provincias de Junín. Satipo concentra la mayor prevalencia de "
  "desnutrición crónica (30.7%), consistente con su condición de zona de selva.", "Normal"),
 ("2.3.6 Análisis del Dataset de Nacidos Vivos – CNV (210,808 nacimientos en Junín)", "Heading 3"),
 ("Distribución del peso al nacer:", "Normal"),
 ("Peso normal (2500–3999 g): 187,531 nacimientos (88.9%)", "List Paragraph"),
 ("Bajo peso al nacer (<2500 g): 15,864 nacimientos (7.5%)", "List Paragraph"),
 ("Peso muy bajo (<1500 g): 1,866 nacimientos (0.9%)", "List Paragraph"),
 ("Peso alto (>=4000 g): 7,413 nacimientos (3.5%)", "List Paragraph"),
 ("El bajo peso al nacer (7.5%) es un factor de riesgo directo para la anemia infantil; por eso "
  "este dataset actúa como la etapa inicial (nacimiento) del proceso de atención.", "Normal"),
 ("Condición del parto: 140,049 partos eutócicos (66.4%) frente a 70,130 cesáreas (33.3%). La "
  "proporción de cesáreas supera el rango recomendado por la OMS (10–15%).", "Normal"),
 ("Prematuridad: 12,255 nacimientos antes de las 37 semanas (5.8%). Perfil de la madre: edad "
  "promedio 28.0 años, nivel de instrucción más frecuente secundaria completa y principal "
  "financiador del parto el SIS (77.2%).", "Normal"),
 ("Cobertura geográfica: 9 provincias, período 2015–2025. Yauli presenta la mayor proporción de "
  "bajo peso al nacer (9.7%).", "Normal"),
])
print("B) OK")

# ===== C) Tabla fuentes ETL =====
append_rows(find_table("Dataset | Archivo fuente"), [
 ["DS4 – Estado nutricional CRED", "Niños JUNIN.csv", "76,064", "41", ", (coma) / UTF-8"],
 ["DS5 – Nacidos vivos (CNV)", "CNV_MINSA_CORTE_30112025.csv (filtrado a Junín)", "210,808", "22", "; / UTF-8"],
])
print("C) OK")

# ===== D) Tabla 3.6 definicion =====
append_rows(find_table("Código | Indicador | Definición"), [
 ["IND-08", "Tasa de desnutrición crónica infantil",
  "Porcentaje de niños con control CRED cuyo diagnóstico talla/edad corresponde a desnutrición crónica.",
  "hecho_cred_nutricion", "CRED / Nutrición"],
 ["IND-09", "Cobertura de suplementación en CRED",
  "Porcentaje de atenciones CRED que registran entrega de suplementación con hierro.",
  "hecho_cred_nutricion", "CRED / Nutrición"],
 ["IND-10", "Tasa de bajo peso al nacer",
  "Porcentaje de nacidos vivos con peso al nacer menor a 2500 gramos.", "hecho_nacido_vivo", "Nacimiento"],
 ["IND-11", "Tasa de prematuridad",
  "Porcentaje de nacimientos con duración de embarazo menor a 37 semanas.", "hecho_nacido_vivo", "Nacimiento"],
 ["IND-12", "Proporción de parto por cesárea",
  "Porcentaje de nacimientos cuya condición de parto es cesárea.", "hecho_nacido_vivo", "Nacimiento"],
])
print("D) OK")

# ===== E) Modelo 3.2 =====
insert_paragraphs_after(par_prefix("Un ESTABLECIMIENTO atiende a muchas GESTANTES"), [
 ("El mismo ESTABLECIMIENTO genera, además, muchas ATENCIONES DE ESTADO NUTRICIONAL en el control "
  "CRED (1:N), y cada UBICACIÓN concentra muchos NACIMIENTOS registrados en el certificado de "
  "nacido vivo (1:N). Con ello el modelo abarca el proceso completo, del nacimiento al tratamiento "
  "de la anemia.", "List Paragraph"),
])
append_rows(find_table("Tabla | Tipo | Clave primaria"), [
 ["hecho_cred_nutricion", "Hecho", "id_atencion", "renaes → dim_establecimiento", "DS4 Estado nutricional CRED"],
 ["hecho_nacido_vivo", "Hecho", "id_cnv", "id_ubicacion → dim_ubicacion", "DS5 Nacidos vivos (CNV)"],
])
insert_paragraphs_after(par_prefix("hecho_nino_anemia: id_nino"), [
 ("hecho_cred_nutricion: id_atencion (PK), renaes (FK), fecha_atencion, sexo, edad_meses, peso, "
  "talla, ptz, zte, zpe, dx_pt, dx_te, dx_pe, dcronica (0/1), cred_ok, supl_ok, consej_ok, juntos, "
  "sis, qaliwarma.", "List Paragraph"),
 ("hecho_nacido_vivo: id_cnv (PK), id_ubicacion (FK), fecnac_anio, fecnac_mes, peso_nacido, "
  "bajo_peso (0/1), dur_emb_parto, prematuro (0/1), condicion_parto, cesarea (0/1), sexo_nacido, "
  "edad_madre, nivel_instruccion_madre, financiador_parto.", "List Paragraph"),
])
insert_paragraphs_after(P(idx_prefix("Resultado. Tras el proceso", start=BODY0) - 1), [
 ("Normalización de los datasets integrados (DS4 y DS5). Las dos nuevas tablas de hecho siguen el "
  "mismo criterio. En hecho_cred_nutricion, los atributos geográficos e institucionales del "
  "establecimiento que venían repetidos en cada atención se trasladan a dim_establecimiento y "
  "dim_ubicacion, de modo que el hecho solo conserva la clave foránea renaes; los puntajes "
  "antropométricos y los diagnósticos nutricionales dependen del propio hecho y cumplen 3FN. En "
  "hecho_nacido_vivo, al no disponer de código RENAES, la dependencia geográfica se resuelve con "
  "la clave foránea id_ubicacion hacia dim_ubicacion; los atributos del nacimiento y de la madre "
  "son propios del hecho. Ambas tablas quedan en 3FN respecto de sus atributos descriptivos, con "
  "la misma salvedad documentada para el resto del modelo.", "Normal"),
])
append_rows(find_table("Tabla / grupo de atributos"), [
 ["hecho_cred_nutricion (atributos descriptivos)", "3FN",
  "Geografía del establecimiento movida a dimensión; antropometría y diagnósticos dependen del hecho."],
 ["hecho_nacido_vivo (atributos descriptivos)", "3FN",
  "Dependencia geográfica resuelta con id_ubicacion (FK); datos del nacimiento y de la madre propios del hecho."],
])
print("E) OK")

# ===== F) Formulas 3.4.2 =====
insert_paragraphs_after(P(idx_prefix("3.4.3 Justificación", start=BODY0) - 1), [
 ("Indicadores de los datasets integrados (DS4 y DS5)", "Normal"),
 ("Los cinco indicadores añadidos se calculan con la misma lógica de razón numerador/denominador "
  "por nivel geográfico, sumando conteos y no promediando porcentajes:", "Normal"),
 ("IND-08. Desnutrición crónica infantil = (N° atenciones CRED con diagnóstico talla/edad de "
  "desnutrición crónica ÷ N° total de atenciones CRED) × 100. Valor global: 15,375 / 76,064 = 20.2%.", "Normal"),
 ("IND-09. Cobertura de suplementación en CRED = (N° atenciones con suplementación ÷ N° total de "
  "atenciones CRED) × 100. Valor global: 45.6%.", "Normal"),
 ("IND-10. Bajo peso al nacer = (N° nacidos vivos con peso < 2500 g ÷ N° total de nacidos vivos) "
  "× 100. Valor global: 15,864 / 210,808 = 7.5%.", "Normal"),
 ("IND-11. Prematuridad = (N° nacimientos con duración de embarazo < 37 semanas ÷ N° total de "
  "nacidos vivos) × 100. Valor global: 5.8%.", "Normal"),
 ("IND-12. Parto por cesárea = (N° nacimientos con condición de parto cesárea ÷ N° total de "
  "nacidos vivos) × 100. Valor global: 70,130 / 210,808 = 33.3%. A diferencia del resto, este "
  "indicador es descriptivo (no tiene una dirección «buena» o «mala» por sí mismo).", "Normal"),
])
print("F) OK")

# ===== G) Resultados 4.2.5 (addprevious sobre la BIBLIOGRAFIA REAL, Heading 1) =====
# OJO: "BIBLIOGRAFÍA" aparece 2 veces: en el INDICE (estilo Normal) y como
# encabezado real del capitulo (Heading 1). Debemos usar la de Heading 1.
def par_heading(text, style_contains="Heading 1"):
    for p in doc.paragraphs:
        if p.text.strip() == text and style_contains in p.style.name:
            return p
    raise ValueError("No encontrado heading: " + text)
biblio_el = par_heading("BIBLIOGRAFÍA")._p
mn = P(idx_prefix("Resultado. Tras el proceso", start=BODY0))
mh = P(idx_prefix("4.2.4 Detalle por distrito", start=BODY0))
molde3 = find_table("Indicador | Descripción | Valor regional")
molde6 = find_table("Provincia | Niños dx")
elementos = [
 mk_par("4.2.5 Indicadores de nacimiento y estado nutricional (datasets integrados)", mh, "Heading 3"),
 mk_par("La incorporación de los datasets de estado nutricional (DS4) y de nacidos vivos (DS5) "
        "amplía el monitoreo a los extremos del proceso de atención: el nacimiento (punto de "
        "partida) y el estado nutricional del niño durante el control CRED. El dashboard presenta "
        "estos cinco indicadores en una segunda fila de tarjetas, agrupados como «Nacimiento y "
        "estado nutricional». La Tabla 4.6 recoge los valores regionales calculados por el sistema.",
        mn, "Normal"),
 mk_par("Tabla 4.6. Indicadores de nacimiento y estado nutricional de la región Junín.", mn, "Normal"),
 mk_table(molde3, [
    ["Indicador", "Descripción", "Valor regional"],
    ["IND-08", "Desnutrición crónica infantil (CRED, talla/edad)", "20.2%"],
    ["IND-09", "Cobertura de suplementación con hierro en CRED", "45.6%"],
    ["IND-10", "Bajo peso al nacer (<2500 g)", "7.5%"],
    ["IND-11", "Prematuridad (<37 semanas)", "5.8%"],
    ["IND-12", "Parto por cesárea", "33.3%"],
 ]),
 mk_par("A nivel provincial, Satipo presenta la mayor desnutrición crónica (30.7%) y Yauli el "
        "mayor bajo peso al nacer (9.7%). Huancayo, que concentra el mayor volumen de nacimientos y "
        "atenciones, registra 15.9% de desnutrición crónica y 60.8% de cobertura de suplementación. "
        "La Tabla 4.7 detalla los cinco indicadores por provincia.", mn, "Normal"),
 mk_par("Tabla 4.7. Indicadores de nacimiento y estado nutricional por provincia.", mn, "Normal"),
 mk_table(molde6, [
    ["Provincia", "D. crónica", "Cob. supl.", "Bajo peso", "Prematuridad", "Cesárea"],
    ["Chanchamayo", "13.1%", "32.0%", "5.6%", "5.1%", "36.5%"],
    ["Chupaca", "17.1%", "54.6%", "7.9%", "5.7%", "35.0%"],
    ["Concepción", "20.4%", "54.2%", "8.5%", "5.5%", "29.9%"],
    ["Huancayo", "15.9%", "60.8%", "7.9%", "5.9%", "38.2%"],
    ["Jauja", "17.7%", "37.5%", "8.1%", "6.7%", "34.0%"],
    ["Junín", "19.5%", "42.0%", "8.7%", "6.2%", "21.7%"],
    ["Satipo", "30.7%", "39.0%", "7.5%", "5.6%", "25.1%"],
    ["Tarma", "16.5%", "31.5%", "7.0%", "6.3%", "21.0%"],
    ["Yauli", "18.5%", "33.8%", "9.7%", "7.3%", "35.3%"],
 ]),
]
for el in elementos:
    biblio_el.addprevious(el)
print("G) OK (4.2.5 antes de BIBLIOGRAFIA)")

# ===== H) Indice =====
CUERPO = idx_prefix("CAPÍTULO 1", start=60)
if CUERPO < 0: CUERPO = idx_prefix("CAPÍTULO I - ASPECTOS GENERALES", start=64)
SANG = "      "
ref23 = P(idx_exact("2.3  Análisis exploratorio de datos", 0, CUERPO))
insert_paragraphs_after(ref23, [
 (SANG + "2.3.5  Dataset de estado nutricional en CRED", "Normal"),
 (SANG + "2.3.6  Dataset de nacidos vivos (CNV)", "Normal"),
], index_font_from=ref23)
CUERPO = idx_prefix("CAPÍTULO 1", start=60)
ref42 = P(idx_exact("4.2  Visualización de datos", 0, CUERPO))
insert_paragraphs_after(ref42, [
 (SANG + "4.2.5  Indicadores de nacimiento y estado nutricional", "Normal"),
], index_font_from=ref42)
print("H) OK")

doc.save(SRC)
print("\n=== RECONSTRUIDO ===", len(doc.paragraphs), "parrafos,", len(doc.tables), "tablas")
