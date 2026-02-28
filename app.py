import streamlit as st
import pdfplumber
import re
import numpy as np
import matplotlib.pyplot as plt

# Configuración de la página
st.set_page_config(page_title="Analizador CFE")
st.title("📊 Analizador de Recibos CFE")

# Función de extracción
def extraer_monto(file):
    with pdfplumber.open(file) as pdf:
        texto = ""
        for page in pdf.pages:
            texto += page.extract_text()
        match = re.search(r"TOTAL A PAGAR.*?(\d+[\d,.]*)", texto, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(",", ""))
    return None

# Subida de archivos (múltiples)
archivos_subidos = st.file_uploader("Sube tus recibos de CFE (PDF)", type="pdf", accept_multiple_files=True)

if archivos_subidos:
    pagos = []
    for f in archivos_subidos:
        monto = extraer_monto(f)
        if monto:
            pagos.append(monto)
    
    if pagos:
        # --- LOS TRES RESULTADOS QUE PEDISTE ---
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Media del Pago", f"${np.mean(pagos):.2f}")
        
        with col2:
            st.metric("Varianza", f"{np.var(pagos):.2f}")
        
        # Gráfica de Barras
        fig, ax = plt.subplots()
        ax.bar(range(1, len(pagos) + 1), pagos, color='#00a859')
        ax.set_title("Evolución de Pagos")
        ax.set_ylabel("Pesos ($)")
        ax.set_xlabel("Recibos cargados")
        st.pyplot(fig)
