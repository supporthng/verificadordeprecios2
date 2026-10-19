"""Navegación principal: conserva las páginas originales sin cambiar la consulta."""
import streamlit as st

st.set_page_config(page_title="Consulta de Precios", page_icon="🏷️", layout="wide")

pages = {
    "Principal": [
        st.Page("consulta_precios.py", title="Consulta de Precios", icon="🏷️", default=True),
        st.Page("pages/1_Administracion.py", title="Cargar Archivo Local", icon="📁"),
        st.Page("pages/4_Listado_Productos.py", title="Consulta de Base de Datos", icon="📋"),
    ],
    "Configuración": [
        st.Page("pages/2_Fuentes_de_datos.py", title="Fuentes de Datos", icon="🔌"),
        st.Page("pages/3_Consulta_Bases_de_Datos.py", title="Configurar Consulta", icon="⚙️"),
    ],
}
st.navigation(pages, position="sidebar").run()
