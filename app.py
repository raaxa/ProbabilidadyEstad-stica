import streamlit as st
import pdfplumber
import re
import numpy as np
import matplotlib.pyplot as plt
import io

# Configuración de la interfaz
st.set_page_config(page_title="Analizador CFE Pro", page_icon="⚡")
st.title("⚡ Analizador Estadístico CFE")
st.markdown("Extrae el historial de la segunda página para calcular Media y Varianza reales.")

def limpiar_valor(texto):
    if not texto: return None
    # Quitamos signos de pesos, comas y espacios
    limpio = texto.replace('$', '').replace(',', '').strip()
    try:
        valor = float(limpio)
        # FILTRO DE SEGURIDAD: Un recibo residencial rara vez pasa de $20,000
        # Esto evita leer el RMU o el No. de Servicio (que son millones)
        if 10 < valor < 20000:
            return valor
    except:
        return None
    return None

def extraer_historial_cfe(file):
    datos_validos = []
    with pdfplumber.open(io.BytesIO(file.read())) as pdf:
        # Buscamos principalmente en la página 2 (donde está la tabla histórica)
        for page in pdf.pages:
            tablas = page.extract_tables()
            for tabla in tablas:
                for fila in tabla:
                    # En la tabla de CFE, el importe suele estar en la columna 2 o 3
                    for celda in fila:
                        if celda and '$' in celda:
                            valor = limpiar_valor(celda)
                            if valor:
                                datos_validos.append(valor)
    
    # Si subes un PDF de CFE, la tabla trae los últimos 12-24 meses
    # Eliminamos duplicados manteniendo el orden
    return list(dict.fromkeys(datos_validos))

# --- INTERFAZ DE USUARIO ---
archivo = st.file_uploader("Sube tu recibo CFE (PDF)", type=["pdf"])

if archivo:
    with st.spinner('Analizando historial...'):
        pagos = extraer_historial_cfe(archivo)
    
    if pagos:
        st.success(f"Se detectaron {len(pagos)} periodos en el historial.")
        
        # --- CÁLCULOS ESTADÍSTICOS ---
        media = np.mean(pagos)
        varianza = np.var(pagos)
        
        # Mostrar Métricas
        col1, col2 = st.columns(2)
        col1.metric("MEDIA (Promedio)", f"${media:.2f}")
        col2.metric("VARIANZA", f"{varianza:.2f}")
        
        # --- GRÁFICA DE BARRAS ---
        st.subheader("Visualización de Consumos")
        fig, ax = plt.subplots(figsize=(10, 5))
        
        # Invertimos para que el más reciente salga al final
        pagos_grafica = pagos[::-1]
        x_labels = [f"Periodo {i+1}" for i in range(len(pagos_grafica))]
        
        barras = ax.bar(x_labels, pagos_grafica, color='#2ecc71', edgecolor='black')
        ax.axhline(media, color='red', linestyle='--', label=f'Media: ${media:.2f}')
        
        ax.set_ylabel("Importe en Pesos ($)")
        ax.set_title("Historial de Pagos Extraído")
        ax.legend()
        
        # Etiquetas de valor sobre las barras
        for bar in barras:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval + 5, f'${yval:.0f}', 
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        st.pyplot(fig)
        
        # Tabla de datos para auditoría
        with st.expander("Ver desglose de montos detectados"):
            st.write(pagos)
    else:
        st.error("No se pudo extraer el historial. Asegúrate de que el PDF sea original de CFE.")
