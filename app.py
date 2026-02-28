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
    # Eliminar todo excepto dígitos y punto decimal
    limpio = re.sub(r'[^\d.]', '', str(texto))
    try:
        valor = float(limpio)
        # Rango típico de pagos CFE
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
            for page_num, page in enumerate(pdf.pages):
                texto = page.extract_text() or ""
                
                # Buscar si esta página contiene la tabla de historial
                if "periodo" in texto.lower() and "importe" in texto.lower():
                    # Dividir el texto en líneas
                    lineas = texto.split('\n')
                    for linea in lineas:
                        linea = linea.strip()
                        # Las líneas de historial suelen comenzar con "del" (ej: "del 14 OCT 25 al 12 DIC 25")
                        if linea.startswith("del") and "al" in linea:
                            # Extraer todos los números de la línea
                            numeros = re.findall(r'\d+\.?\d*', linea)
                            # Convertir a float los que sean números válidos
                            valores = []
                            for num in numeros:
                                try:
                                    v = float(num)
                                    valores.append(v)
                                except:
                                    pass
                            # En la línea típica, el último número es el importe
                            if valores:
                                posible_importe = valores[-1]
                                # Verificar que esté en el rango
                                if 50 < posible_importe < 20000:
                                    pagos.append(posible_importe)
                    
                    # Si ya encontramos pagos en esta página, no seguimos buscando en otras
                    if pagos:
                        break
                
                # Si no se encontró la tabla por texto, intentar con extracción de tablas
                if not pagos:
                    tablas = page.extract_tables()
                    for tabla in tablas:
                        # Buscar encabezados que contengan "importe"
                        if tabla and len(tabla) > 0:
                            encabezados = tabla[0]
                            idx_importe = None
                            for i, celda in enumerate(encabezados):
                                if celda and "importe" in celda.lower():
                                    idx_importe = i
                                    break
                            if idx_importe is not None:
                                for fila in tabla[1:]:
                                    if len(fila) > idx_importe:
                                        monto = limpiar_monto(fila[idx_importe])
                                        if monto:
                                            pagos.append(monto)
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
        # Invertir para que el más reciente quede a la derecha (opcional)
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
