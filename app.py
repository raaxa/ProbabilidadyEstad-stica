import streamlit as st
import pdfplumber
import re
import numpy as np
import matplotlib.pyplot as plt
import io

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="Analizador CFE Estadístico", page_icon="⚡")
st.title("⚡ Analizador de Historial CFE")
st.markdown("Extrae datos del **Consumo Histórico** para calcular estadísticas reales de tus pagos.")

def limpiar_monto(texto):
    """Limpia el texto y devuelve un float si parece un monto de pago real."""
    if not texto: return None
    # Quitamos $, espacios y comas
    limpio = texto.replace('$', '').replace(',', '').strip()
    try:
        valor = float(limpio)
        # Filtro: Los pagos de CFE suelen estar entre $100 y $15,000. 
        # Esto ignora números de servicio o RMU que son de 10+ dígitos.
        if 50 < valor < 20000: 
            return valor
    except:
        return None
    return None

def extraer_datos_cfe(file):
    """Busca montos de dinero en las tablas de historial del recibo."""
    pagos_detectados = []
    try:
        with pdfplumber.open(io.BytesIO(file.read())) as pdf:
            for page in pdf.pages:
                # 1. Intentar extraer tablas (Método estándar)
                tablas = page.extract_tables()
                for tabla in tablas:
                    for fila in tabla:
                        for celda in fila:
                            if celda and ('$' in celda or '.' in celda):
                                monto = limpiar_monto(celda)
                                if monto: pagos_detectados.append(monto)
                
                # 2. Si no encontró mucho, buscar por texto plano (Fuerza bruta)
                if len(pagos_detectados) < 3:
                    texto = page.extract_text() or ""
                    # Busca patrones de dinero como $1,234.00 o 567.00
                    encontrados = re.findall(r'\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})', texto)
                    for item in encontrados:
                        monto = limpiar_monto(item)
                        if monto: pagos_detectados.append(monto)
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
    
    # Eliminamos duplicados manteniendo el orden y limitamos a los últimos 12-24 meses
    return list(dict.fromkeys(pagos_detectados))

# --- INTERFAZ DE USUARIO ---
archivo_subido = st.file_uploader("Sube tu recibo CFE en PDF", type=["pdf"])

if archivo_subido:
    with st.spinner('Escaneando historial de pagos...'):
        # Extraemos los datos del historial 
        datos = extraer_datos_cfe(archivo_subido)
    
    if len(datos) > 1:
        st.success(f"¡Éxito! Se detectaron {len(datos)} periodos de pago en el historial.")
        
        # --- CÁLCULOS ESTADÍSTICOS ---
        # Media: $\mu = \frac{1}{n} \sum_{i=1}^{n} x_i$
        media = np.mean(datos)
        # Varianza muestral: $s^2 = \frac{\sum (x_i - \mu)^2}{n-1}$
        varianza = np.var(datos, ddof=1)   # <-- CORRECCIÓN: ahora es varianza muestral
        
        # Mostrar Métricas en pantalla
        col1, col2, col3 = st.columns(3)
        col1.metric("MEDIA (Promedio)", f"${media:.2f}")
        col2.metric("VARIANZA (muestral)", f"{varianza:.2f}")
        col3.metric("MÁXIMO", f"${max(datos):.2f}")

        # --- GRÁFICA DE BARRAS ---
        st.subheader("Gráfica de Pagos Históricos")
        fig, ax = plt.subplots(figsize=(10, 5))
        
        # Invertimos los datos para que el más reciente aparezca a la derecha
        datos_grafica = datos[::-1]
        indices = range(len(datos_grafica))
        
        barras = ax.bar(indices, datos_grafica, color='skyblue', edgecolor='navy')
        ax.axhline(media, color='red', linestyle='--', label=f'Media: ${media:.2f}')
        
        ax.set_ylabel("Monto Pagado ($)")
        ax.set_xlabel("Periodos Anteriores (Historial)")
        ax.set_title("Evolución de Pagos CFE")
        ax.legend()

        # Añadir etiquetas de valor sobre cada barra
        for bar in barras:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval + 5, f'${int(yval)}', 
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

        st.pyplot(fig)
        
        # Tabla detallada para verificar
        with st.expander("Ver lista de montos detectados"):
            st.write(datos)

    elif len(datos) == 1:
        st.warning(f"Solo se detectó un pago (${datos[0]}). Necesitas al menos 2 para calcular la varianza.")
    else:
        st.error("No se encontraron datos en el historial. Asegúrate de que el PDF contenga la tabla de 'Consumo Histórico'.")
