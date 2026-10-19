"""Pagina administrativa para cargar el logo del verificador."""
from io import BytesIO
import hmac

import requests
import streamlit as st
from PIL import Image, UnidentifiedImageError

st.set_page_config(page_title="Logo del negocio", page_icon="🖼️", layout="centered")
st.title("🖼️ Logo del negocio")
st.write("Sube el logo que aparecera debajo del lector de codigo en Consulta de precios.")

url = str(st.secrets.get("SUPABASE_URL", "")).strip().rstrip("/")
key = str(st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")).strip()
admin_password = str(st.secrets.get("LOGO_ADMIN_PASSWORD", ""))

if not admin_password:
    st.error("Configura LOGO_ADMIN_PASSWORD en los Secrets de Streamlit para proteger esta pagina.")
    st.stop()

password = st.text_input("Contraseña de administrador", type="password")
if not hmac.compare_digest(password, admin_password):
    if password:
        st.error("Contraseña incorrecta.")
    st.stop()

if not url or not key:
    st.error("Falta configurar SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY.")
    st.stop()

headers = {"apikey": key, "Authorization": "Bearer " + key}
archivo = st.file_uploader("Selecciona un logo JPG o PNG", type=["jpg", "jpeg", "png"])
if archivo is not None:
    try:
        imagen = Image.open(archivo)
        imagen.verify()
        archivo.seek(0)
        imagen = Image.open(archivo)
        imagen.thumbnail((1400, 900))
        if imagen.mode not in ("RGB", "RGBA"):
            imagen = imagen.convert("RGBA")
        buffer = BytesIO()
        imagen.save(buffer, format="PNG", optimize=True)
        logo_png = buffer.getvalue()
        st.image(logo_png, caption="Vista previa", use_container_width=True)
    except (UnidentifiedImageError, OSError, ValueError):
        st.error("La imagen no es valida.")
        st.stop()

    if st.button("Guardar logo", type="primary", use_container_width=True):
        try:
            # Crear el bucket privado si aun no existe.
            bucket = requests.post(
                f"{url}/storage/v1/bucket",
                headers={**headers, "Content-Type": "application/json"},
                json={"id": "logo-negocio", "name": "logo-negocio", "public": False},
                timeout=15,
            )
            if bucket.status_code not in (200, 201, 409):
                bucket.raise_for_status()
            respuesta = requests.post(
                f"{url}/storage/v1/object/logo-negocio/logo.png",
                headers={**headers, "Content-Type": "image/png", "x-upsert": "true"},
                data=logo_png,
                timeout=25,
            )
            respuesta.raise_for_status()
            st.success("Logo guardado. Aparecera en Consulta de precios (puede tardar hasta un minuto).")
        except requests.RequestException as exc:
            st.error(f"No se pudo guardar el logo en Supabase: {exc}")
