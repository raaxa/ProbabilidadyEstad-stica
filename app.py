import streamlit as st
import pdfplumber
import re
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Analizador CFE", page_icon="📊")
st.title("📊 Analizador de Recibos CFE")

def extraer_monto(file):
    try:
        with pdfplumber.open(file) as pdf:
            texto = ""
            for page in pdf.pages:
                texto += page.extract_text()
            
            # Buscamos el monto con un patrón más flexible
            match = re.search(r"(?:TOTAL A PAGAR|Total a pagar|TOTAL A PAGAR \.\.\.).*?(\d+[\d,.]*)", texto)
            if match:
                monto_str = match.group(1).replace(",", "")
                # Si termina en punto, lo quitamos
                if monto_str.endswith('.'): monto_str = monto_str[:-1]
                return float(monto_str)
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
    return None

archivos_subidos = st.file_uploader("Sube tus recibos de CFE (PDF)", type="pdf", accept_multiple_files=True)

if archivos_subidos:
    pagos = []
    for f in archivos_subidos:
        monto = extraer_monto(f)
        if monto is not None:
            pagos.append(monto)
            st.success(f"Recibo procesado: ${monto:,.2f}")
        else:
            st.warning(f"No se encontró el monto en el archivo: {f.name}")
    
    if len(pagos) > 0:
        st.divider()
        # --- LOS TRES RESULTADOS QUE PEDISTE ---
        col1, col2 = st.columns(2)
        
        with col1:
            st.header("Media")
            st.subheader(f"${np.mean(pagos):,.2f}")
        
        with col2:
            st.header("Varianza")
            st.subheader(f"{np.var(pagos):,.2f}")
        
        st.write("### Gráfica de Historial")
        fig, ax = plt.subplots()
        # Usamos nombres de archivos como etiquetas en el eje X
        nombres = [f"Recibo {i+1}" for i in range(len(pagos))]
        ax.bar(nombres, pagos, color='#00a859')
        ax.set_ylabel("Pesos ($)")
        st.pyplot(fig)
    else:
        st.error("No se pudieron extraer datos de los archivos subidos. Verifica que sean recibos oficiales de CFE.")
