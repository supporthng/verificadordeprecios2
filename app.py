"""Navegación con inicio de sesión obligatorio, incluso para consultar precios."""
import time
import streamlit as st
from auth_usuarios import allowed, bootstrap, cambiar_password, current_user, get_user, verificar

st.set_page_config(page_title="Consulta de Precios", page_icon="🏷️", layout="wide")

try:
    bootstrap()
except Exception as exc:
    st.error("No se pudo inicializar el sistema de usuarios: " + str(exc))
    st.stop()

st.session_state.setdefault("usuario_id", None)
st.session_state.setdefault("fallos_login", 0)
st.session_state.setdefault("bloqueo_hasta", 0.0)

user = current_user()
if not user:
    st.title("🔐 Acceso al Verificador de Precios")
    st.write("Introduce tu usuario y contraseña para iniciar la consulta.")
    with st.form("inicio_sesion"):
        nombre = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")
        entrar = st.form_submit_button("Iniciar sesión", use_container_width=True)
    if entrar:
        if time.monotonic() < st.session_state.bloqueo_hasta:
            st.error("Demasiados intentos. Espera 5 minutos.")
        else:
            try:
                cuenta = get_user(nombre)
                valido = bool(cuenta and cuenta["active"] and verificar(clave, cuenta["password_hash"]))
            except RuntimeError as exc:
                st.error(str(exc))
                valido = False
                cuenta = None
            if valido:
                st.session_state.usuario_id = cuenta["id"]
                st.session_state.fallos_login = 0
                st.rerun()
            else:
                st.session_state.fallos_login += 1
                if st.session_state.fallos_login >= 5:
                    st.session_state.bloqueo_hasta = time.monotonic() + 300
                    st.session_state.fallos_login = 0
                st.error("Usuario o contraseña incorrectos.")
    st.stop()

with st.sidebar:
    st.caption("Sesión: " + user["username"])
    if st.button("Cerrar sesión"):
        st.session_state.usuario_id = None
        st.rerun()

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
