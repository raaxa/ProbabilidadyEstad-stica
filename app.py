import streamlit as st
import pdfplumber
import re
import numpy as np
import matplotlib.pyplot as plt
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import io

# 1. CONFIGURACIÓN VISUAL
st.set_page_config(page_title="Calculadora CFE: Probabilidad", page_icon="📊")
st.title("📊 Analizador de Recibos CFE")
st.markdown("Extrae datos de tus recibos, calcula la **media**, la **varianza** y genera una **gráfica**.")

# 2. FUNCIÓN PARA EXTRAER EL MONTO (Lógica de Búsqueda)
def extraer_monto_total(texto):
    # Buscamos patrones comunes en recibos de CFE: "TOTAL A PAGAR" o "$" seguido de números
    patrones = [
        r"TOTAL A PAGAR\s*\$?\s*([\d,]+\.?\d*)",
        r"\$\s*([\d,]+\.\d{2})",
        r"Total a pagar\s*\$?\s*([\d,]+)"
    ]
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            # Limpiamos el número (quitamos comas) y lo convertimos a decimal
            valor_str = match.group(1).replace(',', '')
            return float(valor_str)
    return None

# 3. PROCESAMIENTO DE ARCHIVOS (PDF o IMAGEN)
def procesar_recibo(archivo):
    bytes_data = archivo.read()
    texto_extraido = ""

    # Si es PDF, intentamos leer texto digital primero
    if archivo.type == "application/pdf":
        try:
            with pdfplumber.open(io.BytesIO(bytes_data)) as pdf:
                texto_extraido = " ".join([pag.extract_text() or "" for pag in pdf.pages])
        except:
            pass
    
    # Si no hay texto (es una foto) o es imagen (JPG/PNG), usamos OCR
    if len(texto_extraido.strip()) < 5:
        try:
            if archivo.type == "application/pdf":
                imagenes = convert_from_bytes(bytes_data)
                texto_extraido = " ".join([pytesseract.image_to_string(img) for img in imagenes])
            else:
                img = Image.open(io.BytesIO(bytes_data))
                texto_extraido = pytesseract.image_to_string(img)
        except Exception as e:
            st.error(f"Error procesando {archivo.name}: {e}")
            
    return extraer_monto_total(texto_extraido)

# 4. INTERFAZ DE USUARIO
archivos_subidos = st.file_uploader(
    "Sube uno o varios recibos de CFE (PDF, JPG, PNG)", 
    type=["pdf", "jpg", "png", "jpeg"], 
    accept_multiple_files=True
)

if st.button("CALCULAR ESTADÍSTICAS"):
    if archivos_subidos:
        montos = []
        nombres_archivos = []

        for archivo in archivos_subidos:
            monto = procesar_recibo(archivo)
            if monto is not None:
                montos.append(monto)
                nombres_archivos.append(archivo.name)
                st.write(f"✅ **{archivo.name}**: ${monto:.2f}")
            else:
                st.warning(f"⚠️ No se detectó el monto en: {archivo.name}")

        if len(montos) > 0:
            st.divider()
            
            # --- CÁLCULOS ESTADÍSTICOS ---
            media = np.mean(montos)
            varianza = np.var(montos)
            
            # Mostrar resultados destacados
            col1, col2 = st.columns(2)
            col1.metric("MEDIA (Promedio)", f"${media:.2f}")
            col2.metric("VARIANZA", f"{varianza:.2f}")
            
            # --- GENERACIÓN DE GRÁFICA ---
            st.subheader("Gráfica de Pagos")
            fig, ax = plt.subplots(figsize=(8, 4))
            
            # Crear barras
            x_labels = [n[:10] for n in nombres_archivos] # Acortamos nombres para que quepan
            ax.bar(x_labels, montos, color='skyblue', edgecolor='navy')
            
            # Etiquetas y estilo
            ax.set_ylabel("Monto en Pesos ($)")
            ax.set_xlabel("Recibos")
            ax.set_title("Comparativa de Pagos CFE")
            
            # Mostrar valores sobre las barras
            for i, v in enumerate(montos):
                ax.text(i, v + (max(montos)*0.02), f"${v:.0f}", ha='center', fontweight='bold')

            st.pyplot(fig)
            
        else:
            st.error("No se pudo extraer ningún monto. Intenta con una imagen más clara.")
    else:
        st.info("Primero sube al menos un archivo.")
