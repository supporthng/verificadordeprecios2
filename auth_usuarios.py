"""Autenticación administrativa y permisos en Supabase."""
import base64
import hashlib
import hmac
import os
import secrets
import time
import requests
import streamlit as st

URL = str(st.secrets.get("SUPABASE_URL", "")).rstrip("/")
KEY = str(st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", ""))
PERMISOS = {
    "cargar_archivo": "Cargar Archivo Local",
    "consultar_base": "Consulta de Base de Datos",
    "fuentes": "Fuentes de Datos",
    "configurar": "Configurar Consulta",
    "logo": "Logo del Negocio",
    "usuarios": "Administrador de Usuarios",
}
MAX_FALLOS = 5

def api(method, params=None, data=None):
    if not URL or not KEY:
        raise RuntimeError("Faltan las credenciales técnicas de Supabase en Secrets.")
    r = requests.request(method, URL + "/rest/v1/verificador_usuarios",
        headers={"apikey": KEY, "Authorization": "Bearer " + KEY,
                 "Content-Type": "application/json", "Prefer": "return=representation"},
        params=params, json=data, timeout=15)
    if not r.ok:
        raise RuntimeError("Supabase HTTP %s: %s" % (r.status_code, r.text[:350]))
    return r.json() if r.content else []

def hash_password(password):
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600000)
    return "pbkdf2_sha256$600000$%s$%s" % (
        base64.b64encode(salt).decode(), base64.b64encode(dk).decode())

def verificar(password, stored):
    try:
        kind, rounds, salt, expected = stored.split("$")
        if kind != "pbkdf2_sha256" or int(rounds) < 200000:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
            base64.b64decode(salt), int(rounds))
        return hmac.compare_digest(actual, base64.b64decode(expected))
    except (ValueError, TypeError):
        return False

def get_user(username):
    rows = api("GET", {"username": "eq." + username.lower().strip(),
                       "select": "*", "limit": 1})
    return rows[0] if rows else None

def bootstrap():
    # Crear admin únicamente cuando la tabla está vacía.
    rows = api("GET", {"select": "id", "limit": 1})
    if not rows:
        try:
            api("POST", data={"username": "admin", "password_hash": hash_password("admin"),
                              "role": "admin", "permissions": list(PERMISOS),
                              "must_change_password": True, "active": True})
        except RuntimeError:
            # Puede haber sido creado en otra sesión concurrente.
            if not get_user("admin"):
                raise

def login():
    st.session_state.setdefault("usuario_id", None)
    st.session_state.setdefault("fallos_login", 0)
    st.session_state.setdefault("bloqueo_hasta", 0.0)
    with st.sidebar:
        if st.session_state.usuario_id:
            try:
                u = current_user()
            except RuntimeError as exc:
                st.error(str(exc))
                return
            if u:
                st.caption("Sesión: " + u["username"])
                if st.button("Cerrar sesión", key="logout"):
                    st.session_state.usuario_id = None
                    st.rerun()
            return
        with st.expander("🔐 Acceso administrativo"):
            with st.form("login_form"):
                name = st.text_input("Usuario")
                password = st.text_input("Contraseña", type="password")
                submit = st.form_submit_button("Entrar")
            if submit:
                if time.monotonic() < st.session_state.bloqueo_hasta:
                    st.error("Demasiados intentos. Espera 5 minutos.")
                    return
                try:
                    u = get_user(name)
                    valid = bool(u and u["active"] and verificar(password, u["password_hash"]))
                except RuntimeError as exc:
                    st.error(str(exc))
                    return
                if valid:
                    st.session_state.usuario_id = u["id"]
                    st.session_state.fallos_login = 0
                    st.rerun()
                else:
                    st.session_state.fallos_login += 1
                    if st.session_state.fallos_login >= MAX_FALLOS:
                        st.session_state.bloqueo_hasta = time.monotonic() + 300
                        st.session_state.fallos_login = 0
                    st.error("Usuario o contraseña incorrectos.")

def current_user():
    uid = st.session_state.get("usuario_id")
    if not uid:
        return None
    rows = api("GET", {"id": "eq." + str(uid), "select": "*", "limit": 1})
    if not rows or not rows[0]["active"]:
        st.session_state.usuario_id = None
        return None
    return rows[0]

def allowed(user, permission):
    return bool(user and not user["must_change_password"] and
                (user["role"] == "admin" or permission in (user.get("permissions") or [])))

def require(permission):
    u = current_user()
    if not allowed(u, permission):
        st.error("Acceso restringido. Inicia sesión con un usuario autorizado.")
        st.stop()
    return u

def cambiar_password(user, nueva):
    if len(nueva) < 8:
        raise ValueError("La nueva contraseña debe tener al menos 8 caracteres.")
    api("PATCH", {"id": "eq." + str(user["id"])},
        {"password_hash": hash_password(nueva), "must_change_password": False})
