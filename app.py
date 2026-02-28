import streamlit as st
import pdfplumber
import re
import numpy as np
import matplotlib.pyplot as plt
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="CFE Stat Analyzer", page_icon="📈")
st.title("⚡ Analizador Estadístico CFE")
st.markdown("Calcula la **Media**, **Varianza** y visualiza tu historial de consumo.")

def limpiar_monto(texto):
    """Limpia strings de dinero y los convierte a float de forma segura"""
    if not texto:
        return None
    # Eliminar signo de pesos y espacios
    texto = texto.replace('$', '').replace(' ', '')
    # Buscar solo la parte numérica (incluyendo puntos y comas de miles/decimales)
    match = re.search(r"(\d[\d,.]*)", texto)
    if match:
        numero_str = match.group(1)
        try:
            # Si hay una coma seguida de dos dígitos al final, es decimal (estilo europeo/algunos recibos)
            if len(numero_str) > 3 and numero_str[-3] == ',':
                numero_str = numero_str[:-3].replace('.', '').replace(',', '') + '.' + numero_str[-2:]
            else:
                # Caso estándar: quitar comas de miles
                numero_str = numero_str.replace(',', '')
            return float(numero_str)
        except ValueError:
            return None
    return None

def extraer_datos(file):
    """Extrae montos del historial para tener una muestra estadística real"""
    bytes_data = file.read()
    lista_pagos = []
    
    if file.type == "application/pdf":
        with pdfplumber.open(io.BytesIO(bytes_data)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        for cell in row:
                            # Filtramos celdas que contienen el historial de pagos 
                            if cell and "$" in cell:
                                monto = limpiar_monto(cell)
                                if monto and monto > 50: # Filtro para evitar cargos pequeños que no son el total
                                    lista_pagos.append(monto)
            
            # Si la tabla falló, buscamos el Total a Pagar principal [cite: 18, 19]
            if not lista_pagos:
                texto = " ".join([p.extract_text() or "" for p in pdf.pages])
                match = re.search(r"TOTAL A PAGAR.*?\$?\s*([\d,.]+)", texto, re.I)
                if match:
                    m = limpiar_monto(match.group(1))
                    if m: lista_pagos.append(m)
    return lista_pagos

# --- INTERFAZ ---
archivos = st.file_uploader("Sube tus recibos CFE (PDF)", type=["pdf"], accept_multiple_files=True)

if st.button("CALCULAR ESTADÍSTICAS"):
    if archivos:
        todos_los_pagos = []
        for f in archivos:
            pagos_archivo = extraer_datos(f)
            todos_los_pagos.extend(pagos_archivo)
        
        if todos_los_pagos:
            # Convertimos a array de numpy para cálculos estadísticos
            datos = np.array(todos_los_pagos)
            
            # --- CÁLCULOS ---
            media = np.mean(datos)
            varianza = np.var(datos)
            
            st.divider()
            
            # --- MOSTRAR MÉTRICAS ---
            c1, c2, c3 = st.columns(3)
            c1.metric("MEDIA (Promedio)", f"${media:.2f}")
            c2.metric("VARIANZA", f"{varianza:.2f}")
            c3.metric("MUESTRAS DETECTADAS", len(datos))
            
            # --- GRÁFICA ---
            st.subheader("Gráfica de Barras: Historial de Pagos")
            fig, ax = plt.subplots(figsize=(10, 5))
            
            # Creamos la gráfica
            x_axis = range(1, len(datos) + 1)
            ax.bar(x_axis, datos, color='#2ecc71', edgecolor='#27ae60')
            
            # Línea de la media
            ax.axhline(media, color='red', linestyle='--', label=f'Media: ${media:.2f}')
            
            ax.set_ylabel("Monto ($)")
            ax.set_xlabel("Periodos Facturados")
            ax.set_xticks(x_axis)
            ax.legend()
            
            # Anotaciones sobre las barras
            for i, v in enumerate(datos):
                ax.text(i+1, v + 5, f"${int(v)}", ha='center', fontweight='bold')
                
            st.pyplot(fig)
        else:
            st.error("No se pudo extraer información. Verifica que el PDF sea un recibo de CFE válido.")
    else:
        st.info("Por favor, sube al menos un recibo.")
