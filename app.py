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
        rows = api("GET", {"id": "eq." + str(payload["id"]), "select": "id,username,password_hash,active", "limit": 1})
        if not rows or not rows[0]["active"] or str(rows[0]["username"]).strip().lower() == "admin":
            return None
        version = hashlib.sha256(rows[0]["password_hash"].encode()).hexdigest()[:24]
        if not hmac.compare_digest(payload["v"], version):
            return None
        return rows[0]["id"]
    except (ValueError, KeyError, TypeError, RuntimeError, OverflowError):
        return None

# Recibir el callback en la RAÍZ, antes del login y de st.navigation.
# st.navigation puede limpiar los query params al cambiar de página.
if "code" in st.query_params or "error" in st.query_params:
    st.session_state["google_oauth_pending"] = {
        "code": str(st.query_params.get("code", "")),
        "state": str(st.query_params.get("state", "")),
        "error": str(st.query_params.get("error", "")),
        "received_at": time.time(),
    }
    for _key in ("code", "state", "scope", "authuser", "prompt", "error"):
        if _key in st.query_params:
            del st.query_params[_key]

# La X solicita autorización; nunca cierra sesión sin contraseña de admin.
solicitar_salida = str(st.query_params.get("salir", "")) == "1"

st.session_state.setdefault("usuario_id", None)
# Impide que una cookie antigua reactive la sesión inmediatamente después de salir.
st.session_state.setdefault("logout_pendiente", False)
st.session_state.setdefault("autorizar_salida_consulta", False)
st.session_state.setdefault("fallos_login", 0)
st.session_state.setdefault("bloqueo_hasta", 0.0)

# Recuperar sesión al refrescar la página o reabrir el navegador.
if not st.session_state.usuario_id and not st.session_state.logout_pendiente:
    token = cookies.get(COOKIE_NAME)
    if token:
        restored_id = _recover(token)
        if restored_id:
            st.session_state.usuario_id = restored_id
        else:
            cookies.remove(COOKIE_NAME)

# CookieController recibe las cookies del navegador de forma asíncrona.
# En una sesión nueva, el primer get() puede devolver None antes de que
# el componente termine de inicializarse. Reintentar sin pedir credenciales.
if not st.session_state.usuario_id and not st.session_state.logout_pendiente:
    @st.fragment(run_every="1s")
    def _esperar_cookie_recordada():
        if st.session_state.get("usuario_id"):
            return
        token_persistente = cookies.get(COOKIE_NAME)
        if token_persistente:
            identificador = _recover(token_persistente)
            if identificador:
                st.session_state.usuario_id = identificador
                st.rerun(scope="app")
            else:
                cookies.remove(COOKIE_NAME)
    _esperar_cookie_recordada()

user = current_user()
# No restaurar automáticamente cuentas con permisos de administración.
# La opción de recordar acceso es exclusiva de cuentas no administradoras.
if user and (str(user["username"]).strip().lower() == "admin" or allowed(user, "usuarios")):
    try:
        cookies.remove(COOKIE_NAME)
    except Exception:
        pass
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
            recordar_acceso = st.checkbox(
                "Recordar mi acceso en este verificador",
                value=False,
                help="Disponible solo para usuarios no administradores. Mantiene la sesión iniciada en este equipo durante 30 días; no guarda la contraseña."
            )
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
                    st.session_state.logout_pendiente = False
                    # Nunca recordar administradores, aunque marquen la casilla.
                    es_administrador = (
                        str(cuenta["username"]).strip().lower() == "admin"
                        or allowed(cuenta, "usuarios")
                    )
                    try:
                        if recordar_acceso and not es_administrador:
                            cookies.set(COOKIE_NAME, _token(cuenta), max_age=COOKIE_SECONDS)
                        else:
                            cookies.remove(COOKIE_NAME)
                    except Exception:
                        pass
                    st.session_state.fallos_login = 0
                    st.session_state.logout_pendiente = False
                    if "salir" in st.query_params:
                        del st.query_params["salir"]
                    # El acceso ya está validado: mostrar Consulta de Precios
                    # inmediatamente. No bloquear la página esperando la cookie.
                    st.rerun()
                else:
                    st.session_state.fallos_login += 1
                    if st.session_state.fallos_login >= 5:
                        st.session_state.bloqueo_hasta = time.monotonic() + 300
                        st.session_state.fallos_login = 0
                    st.error("Usuario o contraseña incorrectos.")
    st.stop()

def _cerrar_sesion():
    # Bloquear recuperación desde la cookie durante el cambio a login.
    st.session_state.logout_pendiente = True
    st.session_state.autorizar_salida_consulta = False
    st.session_state.usuario_id = None
    for permiso_temporal in ("admin_authenticated", "fuentes_admin_ok", "external_admin_ok"):
        st.session_state[permiso_temporal] = False
    try:
        cookies.remove(COOKIE_NAME)
    except Exception:
        pass
    st.rerun()

# La X de consulta exige la contraseña de la cuenta administradora.
# No cerrar ni invalidar la sesión hasta validar la clave en el servidor.
if user["username"].strip().lower() == "consulta" and (solicitar_salida or st.session_state.autorizar_salida_consulta):
    # Temporizador en el servidor: no depende de que el navegador ejecute JavaScript.
    if "inicio_autorizacion_admin" not in st.session_state:
        st.session_state.inicio_autorizacion_admin = time.monotonic()

    @st.fragment(run_every="1s")
    def pantalla_autorizacion_admin():
        st.markdown("""
        <style>
          [data-testid="stSidebar"], [data-testid="collapsedControl"],
          [data-testid="stSidebarCollapsedControl"] {display:none!important;}
          .block-container {max-width:580px!important; padding-top:clamp(50px,12vh,130px)!important;}
        </style>
        """, unsafe_allow_html=True)

        # Campo fuera del formulario para detectar si el usuario comienza a escribir.
        nombre_admin = str(st.session_state.get("salida_usuario_admin", "")).strip()
        transcurridos = time.monotonic() - st.session_state.inicio_autorizacion_admin
        if not nombre_admin and transcurridos >= 10:
            st.session_state.autorizar_salida_consulta = False
            st.session_state.pop("inicio_autorizacion_admin", None)
            if "salir" in st.query_params:
                del st.query_params["salir"]
            st.rerun(scope="app")

        st.title("🔐 Autorizar salida")
        st.info("Para salir, introduce el usuario y la contraseña del administrador.")
        st.text_input("Usuario administrador", key="salida_usuario_admin")
        if not nombre_admin:
            st.caption(f"Regreso automático a Consulta de Precios en {max(0, 10 - int(transcurridos))} segundos si no escribe el usuario.")
        with st.form("formulario_credenciales_admin_para_salir", clear_on_submit=False):
            clave_administrador = st.text_input("Contraseña del administrador", type="password", key="salida_clave_admin")
            confirmar_salida = st.form_submit_button("Confirmar salida", use_container_width=True)
            iniciar_admin = st.form_submit_button("Iniciar sesión como administrador", use_container_width=True)
        if confirmar_salida or iniciar_admin:
            try:
                administrador = get_user(nombre_admin) if nombre_admin.lower() == "admin" else None
                valido_admin = bool(administrador and administrador.get("active")
                                    and verificar(clave_administrador, administrador["password_hash"]))
            except (RuntimeError, ValueError, TypeError, KeyError):
                administrador = None
                valido_admin = False
            if valido_admin:
                st.session_state.pop("inicio_autorizacion_admin", None)
                st.session_state.autorizar_salida_consulta = False
                st.session_state.pop("salida_usuario_admin", None)
                st.session_state.pop("salida_clave_admin", None)
                if "salir" in st.query_params:
                    del st.query_params["salir"]
                if iniciar_admin:
                    # Cambiar la sesión actual por la del administrador, sin recordarla.
                    st.session_state.usuario_id = administrador["id"]
                    st.session_state.logout_pendiente = False
                    try:
                        cookies.remove(COOKIE_NAME)
                    except Exception:
                        pass
                    st.rerun(scope="app")
                else:
                    _cerrar_sesion()
            else:
                st.error("Usuario o contraseña del administrador incorrectos. La sesión no ha cambiado.")
        if st.button("Cancelar y volver a Consulta de Precios", key="cancelar_salida_consulta"):
            st.session_state.autorizar_salida_consulta = False
            st.session_state.pop("inicio_autorizacion_admin", None)
            if "salir" in st.query_params:
                del st.query_params["salir"]
            st.rerun(scope="app")

    pantalla_autorizacion_admin()
    st.stop()

# La autenticación principal del administrador también autoriza los módulos
# antiguos que antes pedían una segunda contraseña por separado.
# Se recalcula en cada ejecución: nunca heredar permisos de otro usuario.
es_administrador_autenticado = str(user["username"]).strip().lower() == "admin"
st.session_state["admin_authenticated"] = es_administrador_autenticado
st.session_state["fuentes_admin_ok"] = es_administrador_autenticado
st.session_state["external_admin_ok"] = es_administrador_autenticado

# La cuenta exclusiva de consulta no necesita navegación lateral.
es_solo_consulta = user["username"].strip().lower() == "consulta"
if not es_solo_consulta:
    with st.sidebar:
        st.caption("Sesión: " + user["username"])
        st.button("🚪 Cerrar sesión", key="sidebar_logout", on_click=_cerrar_sesion)

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
                if not (str(updated["username"]).strip().lower() == "admin" or allowed(updated, "usuarios")):
                    # Solo se renueva una sesión que ya estaba recordada.
                    if cookies.get(COOKIE_NAME):
                        cookies.set(COOKIE_NAME, _token(updated), max_age=COOKIE_SECONDS)
                st.success("Contraseña cambiada.")
                st.rerun()
            except (ValueError, RuntimeError) as exc:
                st.error(str(exc))
    st.stop()

# Completar autorización pendiente después del inicio de sesión administrativo.
_pending = st.session_state.get("google_oauth_pending")
if _pending and es_administrador_autenticado:
    st.session_state.pop("google_oauth_pending", None)
    from google_oauth_source import verify_state, exchange_code, connect
    try:
        if time.time() - _pending["received_at"] > 540:
            raise RuntimeError("La autorización expiró. Conecta Google nuevamente.")
        if _pending["error"]:
            raise RuntimeError("Google rechazó la autorización: " + _pending["error"])
        if not _pending["code"] or not verify_state(_pending["state"]):
            raise RuntimeError("Estado de autorización inválido o vencido.")
        connect(exchange_code(_pending["code"]))
        st.session_state["google_oauth_notice"] = ("success", "Cuenta de Google conectada correctamente.")
    except Exception as exc:
        st.session_state["google_oauth_notice"] = ("error", "No se pudo completar la conexión: " + str(exc))
    st.rerun()

pages = {"Principal": [
    st.Page("consulta_precios.py", title="Consulta de Precios", icon="🏷️", default=True)
]}
config = [
    ("cargar_archivo", "pages/1_Administracion.py", "Cargar Archivo Local", "📁"),
    ("consultar_base", "pages/4_Listado_Productos.py", "Consulta de Base de Datos", "📋"),
    ("fuentes", "pages/2_Fuentes_de_datos.py", "Fuentes de Datos", "🔌"),
    ("configurar", "pages/3_Consulta_Bases_de_Datos.py", "Configurar Consulta", "⚙️"),
    ("configurar", "pages/7_Google_Drive.py", "Google Drive / Sheets", "☁️"),
    ("logo", "pages/3_Logo_del_negocio.py", "Logo del Negocio", "🖼️"),
    ("usuarios", "pages/5_Administrador_Usuarios.py", "Administrador de Usuarios", "👥"),
]
habilitadas = [st.Page(path, title=title, icon=icon)
                for perm, path, title, icon in config if allowed(user, perm)]
if habilitadas:
    pages["Configuración"] = habilitadas
if es_solo_consulta:
    # Ocultar la barra por completo, incluso si el navegador recuerda que estaba abierta.
    # No se modifica el lector ni el script de enfoque de consulta_precios.py.
    st.markdown("""
    <style>
      [data-testid="stSidebar"],
      [data-testid="collapsedControl"],
      [data-testid="stSidebarCollapsedControl"],
      [data-testid="stSidebarCollapseButton"] { display: none !important; }
      [data-testid="stAppViewContainer"] { margin-left: 0 !important; }
    </style>
    """, unsafe_allow_html=True)
    # Botón Streamlit real: el clic establece el estado en el servidor.
    # Evita depender de enlaces URL que algunos navegadores integrados ignoran.
    st.markdown("""
    <style>
      .st-key-boton_salida_x_consulta {
        position: fixed !important;
        top: 10px !important;
        left: 12px !important;
        z-index: 999999 !important;
        width: 40px !important;
      }
      .st-key-boton_salida_x_consulta button {
        width: 38px !important;
        min-height: 36px !important;
        height: 36px !important;
        padding: 0 !important;
        background: rgba(255,255,255,.18) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,.55) !important;
        border-radius: 8px !important;
        font-size: 22px !important;
        font-weight: 800 !important;
      }
      .st-key-boton_salida_x_consulta button:hover {
        background: rgba(255,255,255,.32) !important;
      }
    </style>
    """, unsafe_allow_html=True)
    if st.button("✕", key="boton_salida_x_consulta", help="Salir con contraseña del administrador"):
        st.session_state.autorizar_salida_consulta = True
        st.rerun()
    posicion_navegacion = "hidden"
else:
    posicion_navegacion = "sidebar"

# Ejecutar el navegador exactamente una vez.
st.navigation(pages, position=posicion_navegacion).run()
