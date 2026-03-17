import streamlit as st
import pdfplumber
import re
import numpy as np
import matplotlib.pyplot as plt
import io

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="Analizador CFE Estadístico", page_icon="⚡", layout="centered")

# ============================================
#  INICIO DE MEJORAS ESTÉTICAS
# ============================================

# 1. Imagen de logo (si tienes un archivo local, descomenta la línea y ajusta el nombre)
# Si no tienes imagen, puedes poner un emoji grande o simplemente omitir esta línea.
# Si quieres usar una imagen desde internet, usa la URL.
try:
    st.image("https://static.vecteezy.com/system/resources/thumbnails/054/955/152/small/a-retro-styled-computer-with-a-colorful-geometric-screen-and-a-classic-keyboard-design-png.png", width=150)
except:
    pass  # Si no carga la imagen, no interrumpe la app

# 2. CSS personalizado para cambiar fondo, colores y estilos generales
st.markdown(
    """
    <style>
    /* Fondo de la app: un azul muy claro */
    .stApp {
        background-color: #e8f0fe;
    }
    /* Títulos principales en azul oscuro */
    h1 {
        color: #003366;
        text-align: center;
        font-family: 'Arial', sans-serif;
    }
    h2, h3 {
        color: #003366;
    }
    /* Mejorar aspecto de los botones */
    .stButton > button {
        border-radius: 8px;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.5rem 1rem;
    }
    .stButton > button:hover {
        background-color: #45a049;
    }
    /* Personalizar las tarjetas de métricas */
    .css-1xarl3l {
        background-color: white;
        border-radius: 10px;
        padding: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    /* Hacer que el texto de los expansores sea más legible */
    .streamlit-expanderHeader {
        background-color: #f0f0f0;
        border-radius: 5px;
    }
    /* Mensajes de éxito/advertencia con bordes redondeados */
    .stAlert {
        border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. Título decorado (reemplaza el st.title original)
st.markdown("<h1>⚡ Analizador de Historial CFE ⚡</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 1.2rem; color: #2c3e50;'>Sube varios recibos y obtén estadísticas globales de tus pagos</p>", unsafe_allow_html=True)

# ============================================
#  FIN DE MEJORAS ESTÉTICAS
# ============================================

# Las funciones limpiar_monto y extraer_datos_cfe se mantienen igual
def limpiar_monto(texto):
    """Convierte una cadena con posible formato de dinero a float."""
    if not texto:
        return None
    limpio = re.sub(r'[^\d.]', '', str(texto))
    try:
        valor = float(limpio)
        if 50 < valor < 5000:
            return valor
    except:
        pass
    return None

def extraer_datos_cfe(file):
    """Busca los montos de la columna 'Importe' en el historial de consumos de un único PDF."""
    pagos = []
    try:
        with pdfplumber.open(io.BytesIO(file.read())) as pdf:
            for page in pdf.pages:
                tablas = page.extract_tables()
                for tabla in tablas:
                    if not tabla:
                        continue
                    for i, fila in enumerate(tabla):
                        fila_str = ' '.join([str(cell) for cell in fila if cell])
                        if 'periodo' in fila_str.lower() and 'importe' in fila_str.lower():
                            idx_importe = None
                            for j, cell in enumerate(fila):
                                if cell and 'importe' in str(cell).lower():
                                    idx_importe = j
                                    break
                            if idx_importe is not None:
                                for fila_datos in tabla[i+1:]:
                                    if idx_importe < len(fila_datos):
                                        monto = limpiar_monto(fila_datos[idx_importe])
                                        if monto:
                                            pagos.append(monto)
                                break
                    if pagos:
                        break
                if pagos:
                    break

            if len(pagos) < 3:
                for page in pdf.pages:
                    texto = page.extract_text() or ""
                    lineas = texto.split('\n')
                    for linea in lineas:
                        if linea.strip().startswith("del") and "al" in linea:
                            numeros = re.findall(r'\d+\.?\d*', linea)
                            if len(numeros) >= 4:
                                try:
                                    posible = float(numeros[-1])
                                    if 50 < posible < 5000:
                                        pagos.append(posible)
                                except:
                                    pass
                    if pagos:
                        break
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return []

    pagos_unicos = []
    for p in pagos:
        if p not in pagos_unicos:
            pagos_unicos.append(p)
    return pagos_unicos

# --- INTERFAZ DE USUARIO ---
archivos_subidos = st.file_uploader(
    "📂 Selecciona tus recibos CFE en PDF (puedes elegir varios)",
    type=["pdf"],
    accept_multiple_files=True
)

if archivos_subidos:
    st.info(f"📄 Se recibieron {len(archivos_subidos)} archivo(s). Procesando...")
    
    todos_los_pagos = []
    resumen_por_archivo = []

    with st.spinner('⏳ Escaneando historial de pagos en todos los recibos...'):
        for archivo in archivos_subidos:
            archivo.seek(0)
            pagos_recibo = extraer_datos_cfe(archivo)
            if pagos_recibo:
                todos_los_pagos.extend(pagos_recibo)
                resumen_por_archivo.append({
                    "nombre": archivo.name,
                    "pagos": pagos_recibo,
                    "cantidad": len(pagos_recibo)
                })
            else:
                resumen_por_archivo.append({
                    "nombre": archivo.name,
                    "pagos": [],
                    "cantidad": 0
                })

    if todos_los_pagos:
        st.success(f"✅ Procesamiento completado. Se detectaron **{len(todos_los_pagos)}** periodos de pago en total.")

        media = np.mean(todos_los_pagos)
        varianza = np.var(todos_los_pagos, ddof=1)
        maximo = max(todos_los_pagos)

        col1, col2, col3 = st.columns(3)
        col1.metric("MEDIA GLOBAL", f"${media:.2f}")
        col2.metric("VARIANZA (muestral)", f"{varianza:.2f}")
        col3.metric("MÁXIMO", f"${maximo:.2f}")

        st.subheader("📊 Gráfica Global de Pagos Históricos")
        fig, ax = plt.subplots(figsize=(12, 6))
        indices = range(len(todos_los_pagos))
        barras = ax.bar(indices, todos_los_pagos, color='#3498db', edgecolor='#2c3e50')
        ax.axhline(media, color='#e74c3c', linestyle='--', linewidth=2, label=f'Media: ${media:.2f}')
        ax.set_ylabel("Monto Pagado ($)")
        ax.set_xlabel("Periodos (orden de extracción)")
        ax.set_title("Evolución de Pagos CFE - Consolidado", fontsize=14)
        ax.legend()
        if len(todos_los_pagos) <= 30:
            for bar in barras:
                yval = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2, yval + 5, f'${int(yval)}',
                        ha='center', va='bottom', fontsize=8, fontweight='bold')
        st.pyplot(fig)

        with st.expander("📋 Ver detalles por cada recibo"):
            for item in resumen_por_archivo:
                st.markdown(f"**{item['nombre']}** - {item['cantidad']} pagos detectados")
                if item['pagos']:
                    st.write(item['pagos'])
                else:
                    st.warning("No se encontraron datos en este recibo.")
    else:
        st.error("❌ No se encontraron datos en ningún recibo. Asegúrate de que los PDF contengan la tabla de 'Consumo Histórico'.")
