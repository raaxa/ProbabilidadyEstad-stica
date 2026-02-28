import streamlit as st
import pdfplumber
import re
import numpy as np
import matplotlib.pyplot as plt
import io

st.set_page_config(page_title="Analizador CFE Estadístico", page_icon="⚡")
st.title("⚡ Analizador de Historial CFE (Múltiples Recibos)")
st.markdown("Sube **varios recibos** en PDF para consolidar los datos de todos ellos y obtener estadísticas globales.")

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
    Busca los montos de la columna 'Importe' en el historial de consumos de un único PDF.
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
        return []

    # Eliminar duplicados manteniendo el orden
    pagos_unicos = []
    for p in pagos:
        if p not in pagos_unicos:
            pagos_unicos.append(p)
    return pagos_unicos

# --- INTERFAZ DE USUARIO ---
archivos_subidos = st.file_uploader(
    "Sube tus recibos CFE en PDF (puedes seleccionar varios)",
    type=["pdf"],
    accept_multiple_files=True
)

if archivos_subidos:
    st.info(f"Se recibieron {len(archivos_subidos)} archivo(s). Procesando...")
    
    todos_los_pagos = []          # Lista global con todos los pagos de todos los recibos
    resumen_por_archivo = []       # Para mostrar detalles

    with st.spinner('Escaneando historial de pagos en todos los recibos...'):
        for archivo in archivos_subidos:
            # Leer el archivo (es necesario resetear el puntero porque ya se leyó al obtener el nombre)
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

        # --- CÁLCULOS ESTADÍSTICOS GLOBALES ---
        media = np.mean(todos_los_pagos)
        varianza = np.var(todos_los_pagos, ddof=1)   # Varianza muestral
        maximo = max(todos_los_pagos)

        col1, col2, col3 = st.columns(3)
        col1.metric("MEDIA GLOBAL (Promedio)", f"${media:.2f}")
        col2.metric("VARIANZA GLOBAL (muestral)", f"{varianza:.2f}")
        col3.metric("MÁXIMO GLOBAL", f"${maximo:.2f}")

        # --- GRÁFICA DE BARRAS GLOBAL ---
        st.subheader("Gráfica Global de Pagos Históricos (todos los recibos)")
        fig, ax = plt.subplots(figsize=(12, 6))
        # Mostramos los pagos en el orden que fueron agregados (podríamos ordenarlos si se desea)
        indices = range(len(todos_los_pagos))
        barras = ax.bar(indices, todos_los_pagos, color='skyblue', edgecolor='navy')
        ax.axhline(media, color='red', linestyle='--', label=f'Media Global: ${media:.2f}')
        ax.set_ylabel("Monto Pagado ($)")
        ax.set_xlabel("Periodos (orden de extracción)")
        ax.set_title("Evolución de Pagos CFE - Consolidado")
        ax.legend()
        # Añadir etiquetas solo si no hay demasiados datos
        if len(todos_los_pagos) <= 30:
            for bar in barras:
                yval = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2, yval + 5, f'${int(yval)}',
                        ha='center', va='bottom', fontsize=8, fontweight='bold')
        st.pyplot(fig)

        # --- DETALLE POR ARCHIVO ---
        with st.expander("Ver detalles por cada recibo"):
            for item in resumen_por_archivo:
                st.markdown(f"**{item['nombre']}** - {item['cantidad']} pagos detectados")
                if item['pagos']:
                    st.write(item['pagos'])
                else:
                    st.warning("No se encontraron datos en este recibo.")
    else:
        st.error("No se encontraron datos en ningún recibo. Asegúrate de que los PDF contengan la tabla de 'Consumo Histórico'.")
