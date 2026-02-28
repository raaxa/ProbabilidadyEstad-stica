import streamlit as st
import pdfplumber
import re
import numpy as np
import matplotlib.pyplot as plt
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import io

# Configuración básica de la página
st.set_page_config(page_title="Analizador CFE OCR", page_icon="📊", layout="wide")
st.title("📊 Analizador Avanzado de Recibos CFE")
st.markdown("Sube tus recibos de CFE en formato PDF o Imagen (JPG, PNG). El sistema intentará extraer el total a pagar automáticamente.")

def limpiar_monto(monto_str):
    """Limpia la cadena de texto extraída para convertirla a un número flotante."""
    if not monto_str:
        return None
    # Eliminar caracteres que no sean dígitos ni puntos decimales
    monto_limpio = re.sub(r'[^\d.]', '', monto_str)
    try:
        return float(monto_limpio)
    except ValueError:
        return None

def buscar_total_en_texto(texto):
    """Busca patrones comunes de 'Total a Pagar' en el texto extraído."""
    patrones = [
        # Patrón típico con signo de pesos y decimales opcionales
        r"(?:TOTAL A PAGAR|Total a pagar|TOTAL A PAGAR \.\.\.|Total a Pagar)\s*(?:[\$\s]*)?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
        # Patrón para el recuadro grande en algunos recibos (solo el número grande)
        r"^\s*(\d+)\s*$", # Busca una línea que solo contenga un número grande
    ]
    
    for patron in patrones:
        match = re.search(patron, texto, re.MULTILINE)
        if match:
            return limpiar_monto(match.group(1))
    return None

def procesar_con_ocr(file_bytes, es_pdf=False):
    """Utiliza OCR para extraer texto de una imagen o PDF escaneado."""
    texto_extraido = ""
    try:
        if es_pdf:
            # Convertir PDF a imágenes (una por página)
            imagenes = convert_from_bytes(file_bytes)
            for i, img in enumerate(imagenes):
                texto_extraido += pytesseract.image_to_string(img, lang='spa') # Usar español si está disponible
        else:
            # Procesar imagen directamente
            img = Image.open(io.BytesIO(file_bytes))
            texto_extraido = pytesseract.image_to_string(img, lang='spa')
            
        # Intentar buscar el total en el texto OCR
        return buscar_total_en_texto(texto_extraido)
    except Exception as e:
        st.error(f"Error durante el procesamiento OCR: {e}")
        return None

def extraer_monto(file):
    """Intenta extraer el monto primero como texto digital y luego con OCR."""
    file_bytes = file.read()
    
    # 1. Intentar como texto digital (si es PDF)
    if file.type == "application/pdf":
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                texto_digital = ""
                for page in pdf.pages:
                    texto_digital += page.extract_text() or ""
                
                monto = buscar_total_en_texto(texto_digital)
                if monto is not None:
                    return monto, "Texto Digital"
        except Exception:
            pass # Si falla como texto digital, intentaremos OCR

    # 2. Intentar con OCR (tanto para imagen como para PDF escaneado)
    es_pdf = (file.type == "application/pdf")
    monto_ocr = procesar_con_ocr(file_bytes, es_pdf=es_pdf)
    if monto_ocr is not None:
        return monto_ocr, "OCR (Imagen)"
        
    return None, None

# Sección de subida de archivos en la barra lateral
with st.sidebar:
    st.header("Cargar Recibos")
    archivos_subidos = st.file_uploader("Sube tus recibos (PDF, JPG, PNG)", type=["pdf", "jpg", "jpeg", "png"], accept_multiple_files=True)
    procesar_btn = st.button("Procesar Recibos")

# Procesamiento y visualización de resultados
if archivos_subidos and procesar_btn:
    pagos = []
    nombres_archivos = []
    
    progreso = st.progress(0)
    for i, f in enumerate(archivos_subidos):
        with st.spinner(f"Procesando {f.name}..."):
            monto, metodo = extraer_monto(f)
            if monto is not None:
                pagos.append(monto)
                nombres_archivos.append(f.name)
                st.success(f"**{f.name}**: Se encontró un total de **${monto:,.2f}** usando **{metodo}**.")
            else:
                st.warning(f"**{f.name}**: No se pudo encontrar el monto total automáticamente. Verifica que sea un recibo de CFE válido o intenta con una imagen más clara.")
        progreso.progress((i + 1) / len(archivos_subidos))
    
    st.divider()
    
    # Visualización de Estadísticas y Gráfica
    if len(pagos) > 0:
        st.header("Análisis de Resultados")
        
        # Métricas principales
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Recibos", len(pagos))
        with col2:
            st.metric("Gasto Promedio (Media)", f"${np.mean(pagos):,.2f}")
        with col3:
            st.metric("Varianza", f"{np.var(pagos):,.2f}")
            
        st.divider()
        
        # Gráfica de barras
        st.subheader("Historial de Pagos")
        fig, ax = plt.subplots(figsize=(10, 5))
        
        # Usar índices para el eje X para evitar problemas con nombres largos
        indices = range(len(pagos))
        ax.bar(indices, pagos, color='#00a859', edgecolor='black') # Color verde CFE
        
        # Configuración de ejes y etiquetas
        ax.set_ylabel("Monto en Pesos ($)", fontsize=12)
        ax.set_title("Evolución del Gasto en Energía Eléctrica", fontsize=14)
        ax.set_xticks(indices)
        
        # Rotar las etiquetas del eje X si hay muchos archivos
        etiquetas_x = [name if len(name) < 15 else name[:12]+'...' for name in nombres_archivos]
        ax.set_xticklabels(etiquetas_x, rotation=45, ha='right')
        
        # Añadir cuadrícula y ajustar diseño
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        st.pyplot(fig)
        
    else:
        st.error("No se pudieron extraer datos de los archivos subidos. Por favor, asegúrate de subir recibos de CFE legibles.")

elif not archivos_subidos and procesar_btn:
    st.info("Por favor, sube al menos un recibo en la barra lateral antes de presionar 'Procesar Recibos'.")
