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


st.divider()
st.subheader("Fotografías de productos")
st.caption("Sube una imagen para un código de barras. Tendrá prioridad sobre las imágenes encontradas automáticamente.")
codigo_imagen = st.text_input("Código de barras del producto", key="codigo_imagen_producto").strip()
archivo_imagen = st.file_uploader("Fotografía JPG o PNG", type=["jpg", "jpeg", "png"], key="foto_producto_manual")
if archivo_imagen is not None and codigo_imagen.isdigit() and 8 <= len(codigo_imagen) <= 14:
    try:
        with Image.open(archivo_imagen) as original:
            imagen_producto_manual = original.convert("RGB")
            imagen_producto_manual.thumbnail((800, 800))
            buffer_producto = BytesIO()
            imagen_producto_manual.save(buffer_producto, format="PNG", optimize=True)
        datos_imagen = buffer_producto.getvalue()
        st.image(datos_imagen, caption=f"Imagen para {codigo_imagen}", width=200)
        if st.button("Guardar fotografía del producto", type="primary"):
            cabeceras = {"apikey": key, "Authorization": "Bearer " + key}
            try:
                bucket_check = requests.get(f"{url}/storage/v1/bucket/imagenes-productos", headers=cabeceras, timeout=12)
                if bucket_check.status_code == 404:
                    created = requests.post(f"{url}/storage/v1/bucket", headers={**cabeceras,"Content-Type":"application/json"}, json={"id":"imagenes-productos","name":"imagenes-productos","public":False}, timeout=12)
                    if not created.ok:
                        st.error(f"No se pudo crear el almacenamiento (HTTP {created.status_code}).")
                        st.stop()
                elif not bucket_check.ok:
                    st.error(f"No se pudo comprobar el almacenamiento (HTTP {bucket_check.status_code}).")
                    st.stop()
                response = requests.post(f"{url}/storage/v1/object/imagenes-productos/{codigo_imagen}.png", headers={**cabeceras,"Content-Type":"image/png","x-upsert":"true"}, data=datos_imagen, timeout=20)
                if response.ok:
                    st.success("Fotografía guardada. La imagen aparecerá en las próximas consultas (la caché puede tardar hasta 24 horas en renovarse).")
                else:
                    st.error(f"No se pudo guardar la imagen (HTTP {response.status_code}).")
            except requests.RequestException:
                st.error("No se pudo conectar con Supabase Storage.")
    except (OSError, ValueError):
        st.error("El archivo de imagen no es válido.")
elif archivo_imagen is not None:
    st.warning("Introduce un código de barras numérico de 8 a 14 dígitos.")
