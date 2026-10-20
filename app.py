"""Navegación con inicio de sesión obligatorio, incluso para consultar precios."""
import time
import json
import hmac
import hashlib
import base64
import streamlit as st
from streamlit_cookies_controller import CookieController
from auth_usuarios import allowed, bootstrap, cambiar_password, current_user, get_user, verificar

st.set_page_config(
    page_title="Consulta de Precios",
    page_icon="🏷️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

try:
    bootstrap()
except Exception as exc:
    st.error("No se pudo inicializar el sistema de usuarios: " + str(exc))
    st.stop()

# Sesión persistente y cifrada en una cookie del navegador.
# No se guardan contraseñas en el navegador.
_cookie_secret = str(st.secrets.get("SESSION_COOKIE_KEY", "")).strip()
if not _cookie_secret:
    st.error("Falta SESSION_COOKIE_KEY en Streamlit Secrets para activar las sesiones persistentes.")
    st.stop()
cookies = CookieController()

COOKIE_NAME = "consulta_precios_login_v2"
COOKIE_SECONDS = 60 * 60 * 24 * 30

def _token(usuario):
    payload = {"id": str(usuario["id"]), "exp": int(time.time()) + COOKIE_SECONDS,
               "v": hashlib.sha256(usuario["password_hash"].encode()).hexdigest()[:24]}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    sig = hmac.new(_cookie_secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return body + "." + sig

def _recover(token):
    try:
        body, sig = token.rsplit(".", 1)
        correct = hmac.new(_cookie_secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, correct):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if int(payload["exp"]) <= time.time():
            return None
        from auth_usuarios import api
        rows = api("GET", {"id": "eq." + str(payload["id"]), "select": "id,password_hash,active", "limit": 1})
        if not rows or not rows[0]["active"]:
            return None
        version = hashlib.sha256(rows[0]["password_hash"].encode()).hexdigest()[:24]
        if not hmac.compare_digest(payload["v"], version):
            return None
        return rows[0]["id"]
    except (ValueError, KeyError, TypeError, RuntimeError, OverflowError):
        return None

st.session_state.setdefault("usuario_id", None)
st.session_state.setdefault("fallos_login", 0)
st.session_state.setdefault("bloqueo_hasta", 0.0)

# Recuperar sesión al refrescar la página o reabrir el navegador.
if not st.session_state.usuario_id:
    token = cookies.get(COOKIE_NAME)
    if token:
        restored_id = _recover(token)
        if restored_id:
            st.session_state.usuario_id = restored_id
        else:
            cookies.remove(COOKIE_NAME)

user = current_user()
if not user:
    st.markdown("""
    <style>
      .stApp { background: radial-gradient(ellipse at 4% 92%, #dce8ff 0%, transparent 46%),
                radial-gradient(ellipse at 98% 0%, #e9f1ff 0%, transparent 40%), #f7faff; }
      [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
      .block-container { max-width: 1100px; padding-top: clamp(35px, 9vh, 115px); }
      .login-head { text-align:center; padding: 20px 10px 15px; width:100%; margin:0 auto; }
      .login-icon { display:inline-flex; align-items:center; justify-content:center;
          width:70px; height:70px; border-radius:20px; background:#eaf1ff;
          font-size:36px; margin-bottom:14px; }
      .login-title { font-weight:800; font-size:clamp(18px, 3.1vw, 40px); color:#172f56;
          margin:0 0 8px; line-height:1.2; white-space:nowrap; letter-spacing:-.5px; }
      .login-subtitle { color:#71809a; font-size:15px; margin:10px 0 8px; }
      [data-testid="stForm"] { background:white; border:1px solid #e3eaf6;
          border-radius:22px; padding:22px 28px 30px;
          box-shadow:0 16px 45px rgba(27, 57, 112, .11); }
      [data-testid="stForm"] [data-testid="stTextInput"] input {
          background:#f9fbff; border-radius:11px; min-height:46px; }
      [data-testid="stForm"] button[kind="secondaryFormSubmit"] {
          background:linear-gradient(105deg,#1679ee,#265cf1); color:white;
          border:0; border-radius:11px; min-height:48px; font-weight:700;
          box-shadow:0 5px 15px rgba(24,102,232,.20); }
      [data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover {
          color:white; background:#165cda; }
      @media (max-width:600px) {
          .block-container { padding:24px 12px 20px; }
          [data-testid="stForm"] { padding:16px 18px 22px; }
          .login-icon { width:60px; height:60px; font-size:30px; }
          .login-title { font-size:clamp(13px, 3.4vw, 20px); letter-spacing:-.6px; }
      }
    </style>
    """, unsafe_allow_html=True)
    # Encabezado a todo el ancho para centrar el título sin saltos de línea.
    st.markdown("""
    <div class="login-head">
      <div class="login-icon">🔐</div>
      <h1 class="login-title">Sistema de Consulta de Precios</h1>
      <p class="login-subtitle">Inicia sesión para acceder al sistema</p>
    </div>
    """, unsafe_allow_html=True)
    _, centro, _ = st.columns([1, 1.05, 1], gap="small")
    with centro:
        with st.form("inicio_sesion"):
            nombre = st.text_input("👤 Usuario", placeholder="Ingresa tu usuario")
            clave = st.text_input("🔒 Contraseña", type="password", placeholder="Ingresa tu contraseña")
            entrar = st.form_submit_button("➜  Iniciar sesión", use_container_width=True)
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
                    cookies.set(COOKIE_NAME, _token(cuenta), max_age=COOKIE_SECONDS)
                    st.session_state.fallos_login = 0
                    st.rerun()
                else:
                    st.session_state.fallos_login += 1
                    if st.session_state.fallos_login >= 5:
                        st.session_state.bloqueo_hasta = time.monotonic() + 300
                        st.session_state.fallos_login = 0
                    st.error("Usuario o contraseña incorrectos.")
    st.stop()

def _cerrar_sesion():
    st.session_state.usuario_id = None
    try:
        cookies.remove(COOKIE_NAME)
    except Exception:
        pass
    st.rerun()

with st.sidebar:
    st.caption("Sesión: " + user["username"])
    if st.button("🚪 Cerrar sesión", key="sidebar_logout"):
        _cerrar_sesion()

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
                # La contraseña cambió: renovar cookie con el nuevo hash.
                updated = current_user()
                cookies.set(COOKIE_NAME, _token(updated), max_age=COOKIE_SECONDS)
                st.success("Contraseña cambiada.")
                st.rerun()
            except (ValueError, RuntimeError) as exc:
                st.error(str(exc))
    st.stop()

pages = {"Principal": [
    st.Page("consulta_precios.py", title="Consulta de Precios", icon="🏷️", default=True)
]}
if user.get("role") == "admin":
    pages["Principal"].append(st.Page("pages/6_Prueba_del_Cursor.py", title="Prueba del Cursor", icon="🧪"))
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
# Menú expandible en la página, independiente de los permisos de configuración.
with st.expander("☰ Menú / Mi cuenta", expanded=False):
    st.caption("Sesión: " + user["username"])
    if st.button("🏷️ Consulta de Precios", key="menu_consulta", use_container_width=True):
        st.switch_page(pages["Principal"][0])
    if user.get("role") == "admin":
        if st.button("🧪 Prueba del Cursor", key="menu_prueba_cursor", use_container_width=True):
            st.switch_page(pages["Principal"][1])
    if habilitadas:
        st.markdown("**Configuración**")
        for i, pagina in enumerate(habilitadas):
            if st.button(pagina.title, key=f"menu_config_{i}", use_container_width=True):
                st.switch_page(pagina)
    st.divider()
    if st.button("🚪 Cerrar sesión", key="menu_cerrar_sesion", use_container_width=True):
        _cerrar_sesion()

st.navigation(pages, position="sidebar").run()
