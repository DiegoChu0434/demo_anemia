# -*- coding: utf-8 -*-
"""Reemplaza, dentro del Informe_Final.docx, los binarios de las imagenes:
   - word/media/image2.png  -> nuevo DER (Figura 3.1)
   - word/media/image3.png  -> nueva figura de normalizacion (Figura 3.2)
Conserva todo lo demas (mockups image14-18 incluidos) y el tamano de
visualizacion definido en el XML del documento.
"""
import os, zipfile, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, "Informe_Final.docx")
TMP  = os.path.join(ROOT, "Informe_Final_tmp.docx")
MED  = os.path.join(ROOT, "etl", "_media_tmp")

REEMPLAZOS = {
    "word/media/image2.png": os.path.join(MED, "nuevo_der.png"),
    "word/media/image3.png": os.path.join(MED, "nuevo_norm.png"),
}
for k, v in REEMPLAZOS.items():
    assert os.path.exists(v), "Falta imagen nueva: " + v

zin = zipfile.ZipFile(SRC, "r")
zout = zipfile.ZipFile(TMP, "w", zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    data = zin.read(item.filename)
    if item.filename in REEMPLAZOS:
        with open(REEMPLAZOS[item.filename], "rb") as f:
            data = f.read()
        print("reemplazada:", item.filename, "(", len(data), "bytes )")
    zout.writestr(item, data)
zout.close(); zin.close()

shutil.move(TMP, SRC)
print("Documento actualizado con las imagenes nuevas.")

# validar
from docx import Document
d = Document(SRC)
print("abre OK, parrafos:", len(d.paragraphs), "tablas:", len(d.tables))
import zipfile as zf
print("ZIP:", "OK" if zf.ZipFile(SRC).testzip() is None else "CORRUPTO")
