# -*- coding: utf-8 -*-
"""
Agrega al Diccionario_Datos_CRED.docx los diccionarios de los 2 datasets nuevos:
  DS4 - Niños de Junín con Controles CRED y Estado Nutricional (Niños JUNIN.csv)
  DS5 - Certificado de Nacido Vivo (CNV - MINSA)
Replica el formato del documento (titulos bold por tamano, tablas Columna/Ejemplo/Que significa).
Idempotente: aborta si ya existe el titulo del DS4.
"""
import io, sys, os, copy
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import _Row, Table
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "Diccionario_Datos_CRED.docx")
doc = Document(SRC)

if any("Estado Nutricional" in p.text and "Dataset" in p.text for p in doc.paragraphs):
    print("El diccionario ya contiene los datasets nuevos. No se modifica.")
    sys.exit(0)

body = doc.element.body
sectpr = body.find(qn('w:sectPr'))  # insertaremos antes de esto (fin del doc)

modelo_par = doc.paragraphs[2]          # un Normal simple
modelo_tabla = doc.tables[0]            # tabla Columna/Ejemplo/Que significa

def _blank_clone(ref_par):
    new_p = copy.deepcopy(ref_par._p)
    for r in new_p.findall(qn('w:r')): new_p.remove(r)
    for el in new_p.findall(qn('w:hyperlink')): new_p.remove(el)
    return new_p

def add_par(text, bold=False, size=None, space_before=False):
    new_p = _blank_clone(modelo_par)
    sectpr.addprevious(new_p)
    p = Paragraph(new_p, modelo_par._parent)
    r = p.add_run(text)
    r.font.bold = bold
    if size: r.font.size = Pt(size)
    return p

def add_blank():
    new_p = _blank_clone(modelo_par)
    sectpr.addprevious(new_p)

def add_table(rows):
    tbl_el = copy.deepcopy(modelo_tabla._tbl)
    for tr in tbl_el.findall(qn('w:tr')): tbl_el.remove(tr)
    sectpr.addprevious(tbl_el)
    t = Table(tbl_el, doc.paragraphs[0]._parent)
    ncol = len(modelo_tabla.columns)
    src_rows = modelo_tabla.rows
    for ri, vals in enumerate(rows):
        model_tr = src_rows[0]._tr if ri == 0 else src_rows[min(1, len(src_rows)-1)]._tr
        tr = copy.deepcopy(model_tr); tbl_el.append(tr)
        row = _Row(tr, t)
        for ci in range(ncol):
            p0 = row.cells[ci].paragraphs[0]
            for r in list(p0.runs): r.text = ""
            for extra in row.cells[ci].paragraphs[1:]:
                extra._p.getparent().remove(extra._p)
            v = vals[ci] if ci < len(vals) else ""
            if p0.runs: p0.runs[0].text = v
            else: p0.add_run(v)

H = ["Columna", "Ejemplo", "Qué significa"]

# ================= DS4 =================
add_blank()
add_par("Dataset: Niños de Junín con Controles CRED y Estado Nutricional — Padrón Nominal (DIRESA Junín)", bold=True, size=12)
add_par("76,064 registros · 41 columnas")
add_par("Este dataset registra cada atención de control CRED de niños menores de 5 años en Junín, "
        "incluyendo la evaluación antropométrica (peso, talla y puntajes Z) y el diagnóstico "
        "nutricional. Complementa al dataset CRED aportando el resultado nutricional, no solo la "
        "cobertura del control.")
add_blank()

add_par("1. Identificación del niño y de la atención", bold=True, size=13)
add_par("Datos básicos del niño o niña y del momento en que se realizó la atención.")
add_table([
 H,
 ["sw", "1", "Marca interna de registro del sistema."],
 ["FechaAtencion", "3/15/2025", "Fecha en que se realizó la atención o control."],
 ["Pais", "PER", "País de la atención (Perú en todos los registros)."],
 ["Sexo", "F", "Sexo del niño/a: F = femenino, M = masculino."],
 ["FechaNacimiento", "4/23/2020", "Fecha de nacimiento del niño/a."],
 ["EdadMeses", "58.71", "Edad del niño/a en meses al momento de la atención (0 a 60)."],
])
add_blank()

add_par("2. Residencia del niño (lugar donde vive)", bold=True, size=13)
add_par("Ubicación geográfica del domicilio del niño/a (padrón nominal).")
add_table([
 H,
 ["UbigeoPN", "120431", "Código de ubigeo del domicilio del niño/a."],
 ["DepartamentoPN", "JUNIN", "Departamento de residencia."],
 ["ProvinciaPN", "JAUJA", "Provincia de residencia."],
 ["DistritoPN", "SINCOS", "Distrito de residencia."],
 ["CentroPobladoPN", "LLACUARI - ANEXO", "Centro poblado o anexo de residencia."],
])
add_blank()

add_par("3. Evaluación antropométrica y diagnóstico nutricional", bold=True, size=13)
add_par("Medidas físicas del niño/a y su clasificación nutricional. Los puntajes Z comparan al niño "
        "con el patrón de crecimiento de la OMS; los diagnósticos resumen su estado.")
add_table([
 H,
 ["Peso", "16.8", "Peso del niño/a en kilogramos."],
 ["Talla", "97.2", "Talla del niño/a en centímetros."],
 ["PTZ", "1.62", "Puntaje Z de peso para la talla (desnutrición aguda / sobrepeso)."],
 ["ZTE", "-2.45", "Puntaje Z de talla para la edad (desnutrición crónica)."],
 ["ZPE", "-.47", "Puntaje Z de peso para la edad (desnutrición global)."],
 ["Dx_PT", "Normal", "Diagnóstico peso/talla: Normal, D.Aguda, Sobrepeso u Obesidad."],
 ["Dx_TE", "D.Crónica", "Diagnóstico talla/edad: Normal o D.Crónica (desnutrición crónica)."],
 ["Dx_PE", "Normal", "Diagnóstico peso/edad: Normal o D.Global (desnutrición global)."],
])
add_blank()

add_par("4. Intervenciones y programas sociales", bold=True, size=13)
add_par("Acciones realizadas en el control y programas sociales a los que pertenece el niño/a (0 = no, 1 = sí).")
add_table([
 H,
 ["Cred", "1", "Indica si se realizó el control CRED (1) o no (0)."],
 ["Suplementacion", "1", "Indica si recibió suplementación con hierro (1) o no (0)."],
 ["Consejeria", "0", "Indica si recibió consejería nutricional (1) o no (0)."],
 ["Sesion", "0", "Indica si participó en una sesión demostrativa (1) o no (0)."],
 ["Juntos", "1", "Pertenece al programa Juntos (1) o no (0)."],
 ["SIS", "1", "Cuenta con Seguro Integral de Salud (1) o no (0)."],
 ["Pin", "", "Pertenece al Programa Integral de Nutrición (1) o no (0)."],
 ["Qaliwarma", "0", "Pertenece al programa Qali Warma (1) o no (0)."],
])
add_blank()

add_par("5. Ubicación del establecimiento de salud", bold=True, size=13)
add_par("Identifican el establecimiento donde se realizó la atención. Renipress es el código "
        "equivalente a RENAES y actúa como clave de cruce con el resto de datasets.")
add_table([
 H,
 ["Diresa", "JUNIN", "Dirección Regional de Salud a la que pertenece el establecimiento."],
 ["Red", "JAUJA", "Red de Salud a la que pertenece el establecimiento."],
 ["Microred", "MARGEN DERECHA", "Micro Red (subdivisión de la red)."],
 ["EESS", "I-1 - 00000405 - LLACUARIPAMPA", "Descripción del establecimiento (categoría, código y nombre)."],
 ["Dpto_EESS", "JUNIN", "Departamento del establecimiento."],
 ["Prov_EESS", "JAUJA", "Provincia del establecimiento (usada para el cruce geográfico)."],
 ["Dist_EESS", "SINCOS", "Distrito del establecimiento (usado para el cruce geográfico)."],
 ["Ubigeo_EESS", "120431", "Código de ubigeo del establecimiento."],
 ["Renipress", "405", "Código único nacional del establecimiento (equivale a RENAES)."],
 ["UbigeoREN / DepartamentoREN / ProvinciaREN / DistritoREN", "120431 / JUNIN / JAUJA / SINCOS", "Ubicación del establecimiento según el registro RENIPRESS."],
 ["AlturaREN", "3280", "Altitud del establecimiento en metros sobre el nivel del mar."],
])
add_blank()

# ================= DS5 =================
add_par("Dataset: Certificado de Nacido Vivo — CNV (MINSA)", bold=True, size=12)
add_par("210,808 registros (Junín) · 22 columnas")
add_par("Este dataset registra los certificados de nacido vivo. El archivo original es nacional "
        "(~4.87 millones de registros); para este proyecto se filtró al departamento de Junín "
        "mediante el ubigeo INEI (prefijo 12). Describe las condiciones del nacimiento y el perfil "
        "de la madre, y constituye la etapa inicial (nacimiento) del proceso de atención.")
add_blank()

add_par("1. Datos del nacimiento", bold=True, size=13)
add_par("Características del parto y del recién nacido.")
add_table([
 H,
 ["FecNac_Año", "2021", "Año de nacimiento."],
 ["FecNac_Mes", "08", "Mes de nacimiento."],
 ["PESO_NACIDO", "3620", "Peso al nacer en gramos (bajo peso si es menor a 2500)."],
 ["TALLA_NACIDO", "52", "Talla al nacer en centímetros."],
 ["DUR_EMB_PARTO", "40", "Duración del embarazo en semanas (prematuro si es menor a 37)."],
 ["Condicion_Parto", "EUTOCICO", "Tipo de parto: eutócico (natural), cesárea o instrumentado."],
 ["sexo_nacido", "MASCULINO", "Sexo del recién nacido."],
 ["Tipo_Parto", "UNICO", "Número de nacidos: único, doble, triple o más de tres."],
])
add_blank()

add_par("2. Perfil de la madre", bold=True, size=13)
add_par("Datos sociodemográficos y antecedentes obstétricos de la madre.")
add_table([
 H,
 ["Edad_Madre", "34", "Edad de la madre en años (adolescente si es menor a 18)."],
 ["Estado_Civil", "SOLTERO", "Estado civil de la madre."],
 ["Nivel_Intrucción_Madre", "SECUNDARIA COMPLETA", "Nivel educativo alcanzado por la madre."],
 ["DESC_OCUPACION", "AMA DE CASA", "Ocupación de la madre."],
 ["Num_embar_madre", "3", "Número total de embarazos de la madre."],
 ["Hijos_vivo_madre", "2", "Número de hijos vivos."],
 ["Hijos_fallec_madre", "-1", "Número de hijos fallecidos (-1 = sin dato)."],
 ["nacmuer_abort_madre", "1", "Número de nacidos muertos o abortos previos."],
 ["Pais_Madre", "PERU", "País de origen de la madre."],
])
add_blank()

add_par("3. Ubicación e institución del nacimiento", bold=True, size=13)
add_par("Dónde y bajo qué cobertura ocurrió el nacimiento. El IdUbigeoInei permite el cruce "
        "geográfico a nivel de provincia (no hay código RENAES en este dataset).")
add_table([
 H,
 ["IdUbigeoInei", "120101", "Código de ubigeo INEI (prefijo 12 = departamento de Junín)."],
 ["Ipress", "6211", "Código de la institución prestadora de salud donde ocurrió el parto."],
 ["Lugar_Nacido", "ESTABLECIMIENTO DE SALUD", "Lugar del nacimiento (establecimiento, domicilio, etc.)."],
 ["Atiende_Parto", "OBSTETRA", "Profesional que atendió el parto."],
 ["Financiador_Parto", "SIS", "Quién financió el parto: SIS, EsSalud, particular, etc."],
])
add_blank()

add_par("4. Conclusión — claves de relación", bold=True, size=13)
add_par("El dataset de estado nutricional (Niños JUNIN) se relaciona con el resto del modelo por "
        "el código Renipress del establecimiento (equivalente a RENAES). El dataset de nacidos "
        "vivos (CNV) no incluye RENAES, por lo que se relaciona a nivel de provincia mediante el "
        "IdUbigeoInei. Así, ambos datasets se integran con el enfoque geográfico-institucional del "
        "proyecto AnemiaCero Junín.")

doc.save(SRC)
print("Diccionario actualizado. parrafos:", len(doc.paragraphs), "tablas:", len(doc.tables))
