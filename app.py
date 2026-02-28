import streamlit as st
import pdfplumber
import re
import numpy as np
import matplotlib.pyplot as plt
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import io

st.set_page_config(page_title="Analizador CFE Pro", page_icon="⚡", layout="wide")
st.title("⚡ Analizador de Recibos CFE")
st.markdown("Sube las imágenes o PDFs de tus recibos para calcular estadística.")

def buscar_monto_cfe(texto):
    """Busca el monto total usando varios métodos de detección."""
    # Eliminar saltos de línea para búsqueda lineal
    texto_plano = " ".join(texto.split())
    
    # 1. Intentar buscar después de la frase clave
    match_frase = re.search(r"TOTAL A PAGAR[:\s]*\$?\s*(\d+)", texto_plano, re.IGNORECASE)
    if match_frase:
        return float(match_frase.group(1))
    
    # 2. Intentar buscar cualquier signo de $ seguido de números (formato grande del recibo)
    match_dinero = re.findall(r"\$\s*(\d{2,5})", texto_plano)
    if match_dinero:
        # En los recibos de CFE, el total suele ser el número más repetido o el más grande cerca del inicio
        return float(match_dinero[0])
        
    return None

def extraer_datos(file):
    file_bytes = file.read()
    monto = None
    metodo = ""
    
    try:
        # Paso 1: Intentar lectura digital (PDF original)
        if file.type == "application/pdf":
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                texto = "".join([p.extract_text() or "" for p in pdf.pages])
                monto = buscar_monto_cfe(texto)
                if monto: metodo = "Digital"

        # Paso 2: Si falla, usar OCR (Imagen o PDF escaneado)
        if not monto:
            if file.type == "application/pdf":
                images = convert_from_bytes(file_bytes)
                texto_ocr = " ".join([pytesseract.image_to_string(img, lang='spa') for img in images])
            else:
                img = Image.open(io.BytesIO(file_bytes))
                texto_ocr = pytesseract.image_to_string(img, lang='spa')
            
            monto = buscar_monto_cfe(texto_ocr)
            if monto: metodo = "OCR (Escaneo)"
            
    except Exception as e:
        st.error(f"Error procesando {file.name}: {e}")
        
    return monto, metodo

# --- INTERFAZ ---
archivos = st.file_uploader("Carga tus recibos (Imagen o PDF)", type=["pdf", "jpg", "png", "jpeg"], accept_multiple_files=True)

if archivos:
    if st.button("🚀 Analizar Recibos"):
        pagos = []
        for f in archivos:
            monto, metodo = extraer_datos(f)
            if monto:
                pagos.append(monto)
                st.success(f"✅ **{f.name}**: ${monto:,.2f} (Detectado vía {metodo})")
            else:
                st.warning(f"⚠️ **{f.name}**: No se pudo extraer el monto automáticamente.")

        if len(pagos) > 0:
            st.divider()
            # RESULTADOS QUE PEDISTE
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Media (Promedio)", f"${np.mean(pagos):,.2f}")
            with col2:
                st.metric("Varianza", f"{np.var(pagos):.2f}")
            
            # Gráfica de Barras
            st.write("### Histórico de Pagos")
            fig, ax = plt.subplots()
            ax.bar([f"Recibo {i+1}" for i in range(len(pagos))], pagos, color='#00a859')
            ax.set_ylabel("Monto ($)")
            st.pyplot(fig)
