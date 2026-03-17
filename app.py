import streamlit as st
import pdfplumber
import re
import numpy as np
import matplotlib.pyplot as plt
import io

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="Probabilidad y Estadística", page_icon="📊", layout="centered")

# ============================================
#  MEJORAS ESTÉTICAS (igual que antes)
# ============================================

# Texto centrado arriba de la imagen
st.markdown(
    "<h1 style='text-align: center; color: #FFFAFA;; font-family: Comic Sans, sans-serif;'>Trabajos y Proyectos de Probabilidad y Estadística</h1>",
    unsafe_allow_html=True
)

# Imagen de logo (desde internet)
try:
    st.image("https://static.vecteezy.com/system/resources/thumbnails/054/955/152/small/a-retro-styled-computer-with-a-colorful-geometric-screen-and-a-classic-keyboard-design-png.png", width=600)
except:
    pass

# CSS personalizado
st.markdown(
    """
    <style>
    .stApp {
        background-color: #000000;
    }
    h1, h2, h3 {
        color: #003366;
    }
    .stButton > button {
        border-radius: 8px;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.5rem 1rem;
    }
    .stButton > button:hover {
        background-color: #FFFAFA;;
    }
    .css-1xarl3l {
        background-color: white;
        border-radius: 10px;
        padding: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .streamlit-expanderHeader {
        background-color: #f0f0f0;
        border-radius: 5px;
    }
    .stAlert {
        border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================
#  FUNCIONES PARA EL ANALIZADOR CFE (sin cambios)
# ============================================

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

# ============================================
#  FUNCIONES PARA EL AJUSTE LINEAL (adaptadas a Streamlit)
# ============================================

def ajuste_lineal(X, Y):
    """Calcula la recta de mínimos cuadrados y = m*x + b usando ecuaciones normales."""
    X = np.array(X, dtype=float)
    Y = np.array(Y, dtype=float)
    unos = np.ones_like(X)
    M = np.vstack([X, unos]).T
    MTM = M.T @ M
    MTY = M.T @ Y
    sol = np.linalg.solve(MTM, MTY)
    m, b = sol
    Y_pred = m * X + b
    return m, b, Y_pred

def graficar_ajuste(X, Y, m, b):
    """Genera la gráfica con los datos y la recta ajustada."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Subplot 1: datos originales
    ax1.scatter(X, Y, color='blue', label='Datos')
    ax1.set_xlabel('x')
    ax1.set_ylabel('y')
    ax1.set_title('Datos de entrada')
    ax1.grid(True)
    ax1.legend()
    
    # Subplot 2: ajuste
    ax2.scatter(X, Y, color='blue', label='Datos')
    x_line = np.linspace(min(X), max(X), 100)
    y_line = m * x_line + b
    ax2.plot(x_line, y_line, color='red', label=f'Ajuste: y = {m:.4f}x + {b:.4f}')
    ax2.set_xlabel('x')
    ax2.set_ylabel('y')
    ax2.set_title('Mínimos cuadrados')
    ax2.grid(True)
    ax2.legend()
    
    plt.tight_layout()
    return fig

# ============================================
#  INTERFAZ PRINCIPAL CON PESTAÑAS
# ============================================

tab1, tab2 = st.tabs(["📄 Analizador CFE", "📈 Ajuste Lineal (Mínimos Cuadrados)"])

with tab1:
    st.header("Analizador de Historial CFE")
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

with tab2:
    st.header("Ajuste Lineal por Mínimos Cuadrados")
    st.markdown("Ingresa los puntos (x, y) para calcular la recta de mejor ajuste.")

    # Opción de entrada: manual o pegar tabla
    input_method = st.radio("Método de entrada:", ["Ingresar manualmente", "Pegar tabla (x y por línea)"])

    X = []
    Y = []

    if input_method == "Ingresar manualmente":
        n = st.number_input("Número de puntos:", min_value=2, value=3, step=1)
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**x**")
            x_vals = [st.number_input(f"x{i+1}", key=f"x{i}", format="%f") for i in range(int(n))]
        with cols[1]:
            st.markdown("**y**")
            y_vals = [st.number_input(f"y{i+1}", key=f"y{i}", format="%f") for i in range(int(n))]
        X = x_vals
        Y = y_vals
    else:
        st.markdown("Pega los datos en el siguiente formato:")
        st.code("x1 y1\nx2 y2\nx3 y3\n...")
        texto = st.text_area("Datos (cada línea: x y)")
        if texto:
            lineas = texto.strip().split('\n')
            for linea in lineas:
                partes = linea.strip().split()
                if len(partes) >= 2:
                    try:
                        x = float(partes[0])
                        y = float(partes[1])
                        X.append(x)
                        Y.append(y)
                    except:
                        pass

    if st.button("Calcular ajuste", type="primary"):
        if len(X) >= 2 and len(X) == len(Y):
            try:
                m, b, Y_pred = ajuste_lineal(X, Y)
                
                st.success("Ajuste realizado con éxito.")
                st.write(f"**Pendiente (m):** {m:.6f}")
                st.write(f"**Intercepto (b):** {b:.6f}")
                st.write(f"**Ecuación:** y = {m:.6f} x + {b:.6f}")

                # Tabla comparativa
                st.subheader("Tabla de valores")
                data = {
                    "x": X,
                    "y real": Y,
                    "y estimado": Y_pred,
                    "residuo": [Y[i] - Y_pred[i] for i in range(len(Y))]
                }
                st.dataframe(data)

                # Gráfica
                st.subheader("Gráfica")
                fig = graficar_ajuste(X, Y, m, b)
                st.pyplot(fig)
            except np.linalg.LinAlgError:
                st.error("Error en el cálculo. Verifica que los datos no sean colineales o constantes.")
        else:
            st.warning("Debes ingresar al menos 2 puntos válidos (misma cantidad de x e y).")
