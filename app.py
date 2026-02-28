import streamlit as st
import pdfplumber
import re
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="CFE Stat Analyzer", page_icon="📈")
st.title("⚡ Analizador Estadístico de Recibos CFE")
st.markdown("Este sistema extrae el **historial de pagos** para calcular estadísticas reales.")

def limpiar_monto(texto):
    """Limpia strings de dinero como '$395.00' a float 395.0"""
    if not texto: return None
    numeros = re.findall(r"[\d,.]+", texto)
    if numeros:
        return float(numeros[0].replace(',', ''))
    return None

def extraer_datos(file):
    """Extrae montos del historial o el total principal"""
    bytes_data = file.read()
    lista_pagos = []
    
    if file.type == "application/pdf":
        with pdfplumber.open(io.BytesIO(bytes_data)) as pdf:
            # 1. Intentar buscar la tabla de historial en la página 2
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        # Buscamos filas que parezcan dinero (ej. $395.00)
                        for cell in row:
                            if cell and "$" in cell:
                                monto = limpiar_monto(cell)
                                if monto and monto > 10: # Evitar cargos mínimos
                                    lista_pagos.append(monto)
            
            # 2. Si no encontró tabla, buscar el TOTAL A PAGAR en el texto
            if not lista_pagos:
                texto = " ".join([p.extract_text() or "" for p in pdf.pages])
                match = re.search(r"TOTAL A PAGAR.*?\$?\s*([\d,.]+)", texto, re.I)
                if match:
                    lista_pagos.append(limpiar_monto(match.group(1)))
    else:
        # Procesamiento para IMÁGENES (OCR)
        img = Image.open(io.BytesIO(bytes_data))
        texto_ocr = pytesseract.image_to_string(img)
        match = re.search(r"TOTAL A PAGAR.*?\$?\s*([\d,.]+)", texto_ocr, re.I)
        if match:
            lista_pagos.append(limpiar_monto(match.group(1)))

    return lista_pagos

# --- INTERFAZ ---
archivos = st.file_uploader("Sube tus recibos CFE", type=["pdf", "png", "jpg"], accept_multiple_files=True)

if st.button("GENERAR ANÁLISIS ESTADÍSTICO"):
    if archivos:
        todos_los_pagos = []
        for f in archivos:
            pagos_archivo = extraer_datos(f)
            todos_los_pagos.extend(pagos_archivo)
        
        if todos_los_pagos:
            # Eliminar duplicados si los hay y ordenar
            datos = np.array(todos_los_pagos)
            
            st.divider()
            
            # --- CÁLCULOS ---
            media = np.mean(datos)
            varianza = np.var(datos)
            
            # --- MOSTRAR MÉTRICAS ---
            c1, c2, c3 = st.columns(3)
            c1.metric("MEDIA (Promedio)", f"${media:.2f}")
            c2.metric("VARIANZA", f"{varianza:.2f}")
            c3.metric("MUESTRAS", f"{len(datos)}")
            
            # --- GRÁFICA ---
            st.subheader("Gráfica de Barras de Consumos")
            fig, ax = plt.subplots(figsize=(10, 5))
            colores = plt.cm.viridis(np.linspace(0, 1, len(datos)))
            
            ax.bar(range(len(datos)), datos, color=colores, edgecolor='black')
            ax.axhline(media, color='red', linestyle='--', label=f'Media: ${media:.2f}')
            
            ax.set_ylabel("Monto en Pesos ($)")
            ax.set_xlabel("Periodos detectados")
            ax.legend()
            
            # Etiquetas en las barras
            for i, v in enumerate(datos):
                ax.text(i, v + 5, f"${int(v)}", ha='center', fontsize=9)
                
            st.pyplot(fig)
            
            # Mostrar tabla de datos para verificar
            with st.expander("Ver lista de montos detectados"):
                st.write(datos)
        else:
            st.error("No se detectaron montos. Asegúrate de que el recibo sea legible.")
    else:
        st.warning("Por favor, sube un archivo primero.")
