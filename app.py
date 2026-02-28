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
    """Convierte una cadena con formato de dinero a float, si es un monto válido."""
    if not texto:
        return None
    # Eliminar caracteres no numéricos (excepto punto decimal)
    limpio = re.sub(r'[^\d.]', '', texto.replace(',', ''))
    try:
        valor = float(limpio)
        # Rango típico de recibos CFE (ajustable)
        if 50 < valor < 20000:
            return valor
    except:
        pass
    return None

def extraer_datos_cfe(file):
    """
    Busca los montos de la columna 'Importe' en la tabla de historial de consumos.
    """
    pagos = []
    try:
        with pdfplumber.open(io.BytesIO(file.read())) as pdf:
            for page in pdf.pages:
                # ----- Estrategia 1: extraer tablas y buscar la columna 'Importe' -----
                tablas = page.extract_tables()
                for tabla in tablas:
                    # Intentar identificar el índice de la columna "Importe"
                    encabezados = tabla[0] if tabla else []
                    idx_importe = None
                    for i, celda in enumerate(encabezados):
                        if celda and "importe" in celda.lower():
                            idx_importe = i
                            break
                    if idx_importe is not None:
                        # Extraer valores de esa columna (saltando encabezado)
                        for fila in tabla[1:]:
                            if len(fila) > idx_importe:
                                monto = limpiar_monto(fila[idx_importe])
                                if monto:
                                    pagos.append(monto)
                        # Si encontramos la columna, no seguimos con otras estrategias en esta página
                        if pagos:
                            break
                    else:
                        # Si no hay encabezado claro, recorrer toda la tabla buscando celdas con $
                        for fila in tabla:
                            for celda in fila:
                                if celda and ('$' in celda or re.search(r'\d+\.\d{2}', celda)):
                                    monto = limpiar_monto(celda)
                                    if monto:
                                        pagos.append(monto)

                # ----- Estrategia 2: si no se encontraron suficientes pagos, buscar por texto -----
                if len(pagos) < 3:
                    texto = page.extract_text() or ""
                    # Buscar líneas que contengan "Importe" y capturar el número que le sigue
                    lineas = texto.split('\n')
                    for linea in lineas:
                        if "importe" in linea.lower():
                            # Buscar un patrón de dinero en esa línea
                            numeros = re.findall(r'\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})', linea)
                            for num in numeros:
                                monto = limpiar_monto(num)
                                if monto:
                                    pagos.append(monto)
                    # Si aún no hay datos, buscar cualquier número con formato de dinero en toda la página
                    if len(pagos) < 3:
                        candidatos = re.findall(r'\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})', texto)
                        for cand in candidatos:
                            monto = limpiar_monto(cand)
                            if monto:
                                pagos.append(monto)
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

        # Cálculos estadísticos
        media = np.mean(datos)
        varianza = np.var(datos, ddof=1)   # Varianza muestral

        col1, col2, col3 = st.columns(3)
        col1.metric("MEDIA (Promedio)", f"${media:.2f}")
        col2.metric("VARIANZA (muestral)", f"{varianza:.2f}")
        col3.metric("MÁXIMO", f"${max(datos):.2f}")

        # Gráfica de barras
        st.subheader("Gráfica de Pagos Históricos")
        fig, ax = plt.subplots(figsize=(10, 5))
        # Ordenar de más antiguo a más reciente (el PDF suele mostrar el más reciente al inicio)
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
