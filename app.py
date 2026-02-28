import streamlit as st
import pdfplumber
import re
import numpy as np
import matplotlib.pyplot as plt
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import io

st.set_page_config(page_title="Analizador CFE OCR", page_icon="⚡", layout="wide")
st.title("⚡ Analizador de Recibos CFE")

def buscar_total_en_texto(texto):
    # Patrón 1: Busca el número grande después de "TOTAL A PAGAR"
    # Patrón 2: Busca el número que sigue al signo $ en grande
    patrones = [
        r"TOTAL A PAGAR\s*\$?\s*(\d+)", 
        r"\$\s*(\d{2,5})",
        r"Total a pagar\s*\$?\s*(\d+)"
    ]
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None

def extraer_monto(file):
    file_bytes = file.read()
    monto = None
    
    # Intentar como PDF digital primero
    if file.type == "application/pdf":
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                texto = "".join([p.extract_text() or "" for p in pdf.pages])
                monto = buscar_total_en_texto(texto)
        except: pass

    # Si no funcionó o es imagen, usar OCR
    if monto is None:
        try:
            if file.type == "application/pdf":
                images = convert_from_bytes(file_bytes)
                texto_ocr = "".join([pytesseract.image_to_string(img) for img in images])
            else:
                img = Image.open(io.BytesIO(file_bytes))
                texto_ocr = pytesseract.image_to_string(img)
            monto = buscar_total_en_texto(texto_ocr)
        except Exception as e:
            st.error(f"Error técnico: {e}")
            
    return monto

# Interfaz
archivos = st.file_uploader("Sube tus recibos", type=["pdf", "jpg", "png"], accept_multiple_files=True)

if st.button("Analizar") and archivos:
    pagos = []
    for f in archivos:
        monto = extraer_monto(f)
        if monto:
            pagos.append(monto)
            st.success(f"✅ {f.name}: ${monto}")
        else:
            st.warning(f"❌ {f.name}: No se detectó el monto.")

    if pagos:
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("Media", f"${np.mean(pagos):.2f}")
        c2.metric("Varianza", f"{np.var(pagos):.2f}")
        
        fig, ax = plt.subplots()
        ax.bar(range(len(pagos)), pagos, color='green')
        ax.set_ylabel("Pesos $")
        st.pyplot(fig)
