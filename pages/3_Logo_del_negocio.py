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
# La sesión principal controla el acceso; no pedir otra contraseña.
from auth_usuarios import current_user, allowed
_usuario_modulo = current_user()
if not _usuario_modulo or not allowed(_usuario_modulo, "logo"):
    st.error("No tienes permiso para acceder a esta sección.")
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
            # Consultar primero: Supabase puede devolver 400 si el bucket ya existe.
            consulta = requests.get(
                f"{url}/storage/v1/bucket/logo-negocio",
                headers=headers,
                timeout=15,
            )
            if consulta.status_code == 404:
                bucket = requests.post(
                    f"{url}/storage/v1/bucket",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"id": "logo-negocio", "name": "logo-negocio", "public": False},
                    timeout=15,
                )
                if not bucket.ok:
                    # Un conflicto de creacion concurrente solo es aceptable
                    # si luego se puede verificar que el bucket existe.
                    verificacion = requests.get(
                        f"{url}/storage/v1/bucket/logo-negocio",
                        headers=headers,
                        timeout=15,
                    )
                    if not verificacion.ok:
                        st.error(
                            f"Supabase no pudo crear el almacenamiento del logo "
                            f"(HTTP {bucket.status_code}): {bucket.text[:600]}"
                        )
                        st.stop()
            elif not consulta.ok:
                st.error(
                    f"Supabase no pudo comprobar el almacenamiento del logo "
                    f"(HTTP {consulta.status_code}): {consulta.text[:600]}"
                )
                st.stop()
            respuesta = requests.post(
                f"{url}/storage/v1/object/logo-negocio/logo.png",
                headers={**headers, "Content-Type": "image/png", "x-upsert": "true"},
                data=logo_png,
                timeout=25,
            )
            if not respuesta.ok:
                st.error(
                    f"Supabase no pudo subir el logo "
                    f"(HTTP {respuesta.status_code}): {respuesta.text[:600]}"
                )
                st.stop()
            st.success("Logo guardado. Aparecera en Consulta de precios (puede tardar hasta un minuto).")
        except requests.RequestException as exc:
            st.error(f"No se pudo guardar el logo en Supabase: {exc}")
