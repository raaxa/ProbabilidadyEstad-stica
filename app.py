import streamlit as st
import pdfplumber
import re
import numpy as np
import matplotlib.pyplot as plt
import io

st.set_page_config(page_title="Analizador CFE Estadístico", page_icon="⚡")
st.title("⚡ Analizador de Historial CFE")
st.markdown("Extrae datos del **Consumo Histórico** para calcular estadísticas reales de tus pagos.")

def limpiar_monto(texto):
    """Convierte una cadena con posible formato de dinero a float."""
    if not texto:
        return None
    limpio = re.sub(r'[^\d.]', '', str(texto))
    try:
        valor = float(limpio)
        if 50 < valor < 20000:
            return valor
    except:
        pass
    return None

def extraer_datos_cfe(file):
    """
    Busca los montos de la columna 'Importe' en el historial de consumos.
    """
    pagos = []
    try:
        with pdfplumber.open(io.BytesIO(file.read())) as pdf:
            # ----- Estrategia 1: extraer tablas con configuración mejorada -----
            for page in pdf.pages:
                # Configuración para detectar tablas basadas en texto (útil cuando no hay bordes)
                table_settings = {
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                }
                tablas = page.extract_tables(table_settings)
                for tabla in tablas:
                    if not tabla or len(tabla) < 2:
                        continue
                    # Convertir a matriz de strings
                    n_filas = len(tabla)
                    n_cols = max(len(fila) for fila in tabla) if tabla else 0
                    # Buscar columnas que contengan montos
                    for col in range(n_cols):
                        valores_col = []
                        for fila in tabla:
                            if col < len(fila):
                                m = limpiar_monto(fila[col])
                                if m:
                                    valores_col.append(m)
                        # Si la columna tiene al menos 3 valores en rango, la consideramos válida
                        if len(valores_col) >= 3:
                            pagos.extend(valores_col)
                            break  # Tomamos la primera columna que cumpla
                    if pagos:
                        break
                if pagos:
                    break

            # ----- Estrategia 2: si no se encontraron, buscar por texto (líneas "del ...") -----
            if len(pagos) < 3:
                for page in pdf.pages:
                    texto = page.extract_text() or ""
                    lineas = texto.split('\n')
                    for linea in lineas:
                        if linea.strip().startswith("del") and "al" in linea:
                            # Extraer todos los números de la línea
                            numeros = re.findall(r'\d+\.?\d*', linea)
                            # Convertir a float y filtrar
                            for num in numeros:
                                try:
                                    v = float(num)
                                    if 50 < v < 20000:
                                        pagos.append(v)
                                        break  # Tomamos el primer número válido (suele ser el importe)
                                except:
                                    pass
                    if pagos:
                        break
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")

    # Eliminar duplicados manteniendo orden
    pagos_unicos = []
    for p in pagos:
        if p not in pagos_unicos:
            pagos_unicos.append(p)
    return pagos_unicos

# --- INTERFAZ DE USUARIO ---
archivo_subido = st.file_uploader("Sube tu recibo CFE en PDF", type=["pdf"])

if archivo_subido:
    with st.spinner('Escaneando historial de pagos...'):
        datos = extraer_datos_cfe(archivo_subido)

    if len(datos) > 1:
        st.success(f"¡Éxito! Se detectaron {len(datos)} periodos de pago.")

        media = np.mean(datos)
        varianza = np.var(datos, ddof=1)   # Varianza muestral

        col1, col2, col3 = st.columns(3)
        col1.metric("MEDIA (Promedio)", f"${media:.2f}")
        col2.metric("VARIANZA (muestral)", f"{varianza:.2f}")
        col3.metric("MÁXIMO", f"${max(datos):.2f}")

        # Gráfica de barras
        st.subheader("Gráfica de Pagos Históricos")
        fig, ax = plt.subplots(figsize=(10, 5))
        datos_grafica = datos[::-1]   # Más reciente a la derecha
        indices = range(len(datos_grafica))
        barras = ax.bar(indices, datos_grafica, color='skyblue', edgecolor='navy')
        ax.axhline(media, color='red', linestyle='--', label=f'Media: ${media:.2f}')
        ax.set_ylabel("Monto Pagado ($)")
        ax.set_xlabel("Periodos Anteriores")
        ax.set_title("Evolución de Pagos CFE")
        ax.legend()
        for bar in barras:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval + 5, f'${int(yval)}',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
        st.pyplot(fig)

        with st.expander("Ver lista de montos detectados"):
            st.write(datos)

    elif len(datos) == 1:
        st.warning(f"Solo se detectó un pago (${datos[0]}). Se necesitan al menos 2 para calcular la varianza.")
    else:
        st.error("No se encontraron datos en el historial. Asegúrate de que el PDF contenga la tabla de 'Consumo Histórico'.")
