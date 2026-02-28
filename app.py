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
        # Rango típico de pagos CFE (ajustable)
        if 50 < valor < 5000:
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
            # ----- Estrategia 1: extracción por tabla con encabezados -----
            for page in pdf.pages:
                tablas = page.extract_tables()
                for tabla in tablas:
                    if not tabla:
                        continue
                    # Buscar fila que contenga "Periodo" e "Importe"
                    for i, fila in enumerate(tabla):
                        fila_str = ' '.join([str(cell) for cell in fila if cell])
                        if 'periodo' in fila_str.lower() and 'importe' in fila_str.lower():
                            # Encontrar índice de la columna "Importe"
                            idx_importe = None
                            for j, cell in enumerate(fila):
                                if cell and 'importe' in str(cell).lower():
                                    idx_importe = j
                                    break
                            if idx_importe is not None:
                                # Extraer de las filas siguientes
                                for fila_datos in tabla[i+1:]:
                                    if idx_importe < len(fila_datos):
                                        monto = limpiar_monto(fila_datos[idx_importe])
                                        if monto:
                                            pagos.append(monto)
                                break  # Salir del bucle de filas
                    if pagos:
                        break  # Salir del bucle de tablas
                if pagos:
                    break  # Salir del bucle de páginas

            # ----- Estrategia 2: si no se encontró por tabla, buscar líneas "del ... al ..." -----
            if len(pagos) < 3:
                for page in pdf.pages:
                    texto = page.extract_text() or ""
                    lineas = texto.split('\n')
                    for linea in lineas:
                        if linea.strip().startswith("del") and "al" in linea:
                            # Extraer todos los números de la línea
                            numeros = re.findall(r'\d+\.?\d*', linea)
                            if len(numeros) >= 4:  # Debe contener fechas y al menos un monto
                                # El último número suele ser el importe
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

    # Eliminar duplicados manteniendo el orden
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
        # Invertir para que el más reciente quede a la derecha
        datos_grafica = datos[::-1]
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
