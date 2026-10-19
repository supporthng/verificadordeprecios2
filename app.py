"""Navegación con permisos; la consulta de precios permanece pública."""
import streamlit as st
from auth_usuarios import PERMISOS, allowed, bootstrap, cambiar_password, current_user, login

st.set_page_config(page_title="Consulta de Precios", page_icon="🏷️", layout="wide")

try:
    bootstrap()
except Exception as exc:
    st.error("No se pudo inicializar el sistema de usuarios: " + str(exc))
    st.stop()

login()
user = current_user()
if user and user["must_change_password"]:
    st.title("Cambio obligatorio de contraseña")
    st.warning("Debes cambiar la contraseña inicial antes de entrar a Configuración.")
    with st.form("cambio_inicial"):
        a = st.text_input("Nueva contraseña", type="password")
        b = st.text_input("Repetir contraseña", type="password")
        guardar = st.form_submit_button("Cambiar contraseña")
    if guardar:
        if a != b:
            st.error("Las contraseñas no coinciden.")
        elif a == "admin":
            st.error("Debes elegir una contraseña diferente de admin.")
        else:
            try:
                cambiar_password(user, a)
                st.success("Contraseña cambiada.")
                st.rerun()
            except (ValueError, RuntimeError) as exc:
                st.error(str(exc))
    st.stop()

pages = {"Principal": [
    st.Page("consulta_precios.py", title="Consulta de Precios", icon="🏷️", default=True)
]}
config = [
    ("cargar_archivo", "pages/1_Administracion.py", "Cargar Archivo Local", "📁"),
    ("consultar_base", "pages/4_Listado_Productos.py", "Consulta de Base de Datos", "📋"),
    ("fuentes", "pages/2_Fuentes_de_datos.py", "Fuentes de Datos", "🔌"),
    ("configurar", "pages/3_Consulta_Bases_de_Datos.py", "Configurar Consulta", "⚙️"),
    ("logo", "pages/3_Logo_del_negocio.py", "Logo del Negocio", "🖼️"),
    ("usuarios", "pages/5_Administrador_Usuarios.py", "Administrador de Usuarios", "👥"),
]
habilitadas = [st.Page(path, title=title, icon=icon)
                for perm, path, title, icon in config if allowed(user, perm)]
if habilitadas:
    pages["Configuración"] = habilitadas
st.navigation(pages, position="sidebar").run()
