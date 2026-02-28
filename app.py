import streamlit as st
import pdfplumber
import re
import numpy as np
import matplotlib.pyplot as plt
import io

# Configuración de la página
st.set_page_config(page_title="CFE Analizador Estadístico", page_icon="📊")
st.title("📊 Analizador de Probabilidad: Recibos CFE")
st.markdown("Extracción automática del **Historial de Importes** para Media y Varianza.")

def limpiar_monto(texto):
    """Extrae el número de strings como '$395.00' y evita números de servicio."""
    if not texto: return None
    # Solo buscamos números que tengan el formato de moneda (ej. 395.00)
    match = re.search(r"(\d{1,4}\.\d{2})", texto.replace(',', ''))
    if match:
        valor = float(match.group(1))
        # Filtro: Ignorar números gigantes (RMU/Servicio) y montos irrelevantes
        if 50 < valor < 10000:
            return valor
    return None

def extraer_historial(file):
    """Escanea el PDF buscando la tabla de Consumo Histórico."""
    datos_pagos = []
    try:
        with pdfplumber.open(io.BytesIO(file.read())) as pdf:
            # El historial casi siempre está en la página 2
            for page in pdf.pages:
                tablas = page.extract_tables()
                for tabla in tablas:
                    for fila in tabla:
                        for celda in fila:
                            if celda and '$' in celda:
                                valor = limpiar_monto(celda)
                                if valor:
                                    datos_pagos.append(valor)
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
    
    # Eliminamos duplicados y nos quedamos con los últimos registros (máximo 12)
    return list(dict.fromkeys(datos_pagos))[:12]

# --- Interfaz de Usuario ---
archivo = st.file_uploader("Sube tu recibo CFE (PDF)", type=["pdf"])

if archivo:
    with st.spinner('Procesando datos históricos...'):
        pagos = extraer_historial(archivo)

    if len(pagos) > 1:
        # Los datos en el PDF vienen del más reciente al más antiguo, los invertimos para la gráfica
        pagos_ordenados = pagos[::-1]
        
        # --- CÁLCULOS ESTADÍSTICOS ---
        media = np.mean(pagos_ordenados)
        varianza = np.var(pagos_ordenados)
        desviacion = np.std(pagos_ordenados)

        st.success(f"Se detectaron {len(pagos_ordenados)} periodos de pago.")

        # Mostrar métricas
        c1, c2, c3 = st.columns(3)
        c1.metric("MEDIA (Promedio)", f"${media:.2f}")
        c2.metric("VARIANZA", f"{varianza:.2f}")
        c3.metric("DESV. ESTÁNDAR", f"${desviacion:.2f}")

        # --- GRÁFICA DE BARRAS ---
        st.subheader("Gráfica de Consumo Histórico")
        fig, ax = plt.subplots(figsize=(10, 5))
        
        x_eje = [f"Bimestre {i+1}" for i in range(len(pagos_ordenados))]
        barras = ax.bar(x_eje, pagos_ordenados, color='#2ecc71', edgecolor='black')
        
        # Línea de la Media
        ax.axhline(media, color='red', linestyle='--', label=f'Media: ${media:.2f}')
        
        ax.set_ylabel("Monto en Pesos ($)")
        ax.set_title("Historial de Importes Detectados")
        ax.legend()

        # Etiquetas de valor sobre las barras
        for bar in barras:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval + 5, f'${int(yval)}', 
                    ha='center', va='bottom', fontweight='bold')

        st.pyplot(fig)
        
        # Mostrar tabla para comprobación
        with st.expander("Ver lista de valores extraídos"):
            st.write(pagos_ordenados)
    else:
        st.error("No se detectaron suficientes datos históricos. Verifica que el PDF tenga la tabla en la página 2.")
