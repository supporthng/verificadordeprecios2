"""Conexión individual de Google Drive y Google Sheets para la instalación."""
import streamlit as st
from auth_usuarios import current_user, allowed
from google_oauth_source import (auth_url, signed_state, verify_state, exchange_code, connect, config, file_id,
                                 read_file, catalog, activate, api, setting)

st.title("☁️ Google Drive y Google Sheets")
user=current_user()
if not allowed(user,"configurar"):
    st.error("Acceso exclusivo para administración.")
    st.stop()
st.caption("Cada instalación puede conectar la cuenta Google de su cliente. No se solicita contraseña de Google.")

try:
    for key in ("GOOGLE_OAUTH_CLIENT_ID","GOOGLE_OAUTH_CLIENT_SECRET",
                "GOOGLE_OAUTH_REDIRECT_URI","GOOGLE_TOKEN_ENCRYPTION_KEY"):
        setting(key)
except Exception as e:
    st.error(str(e));st.stop()

# El retorno de Google se procesa en app.py, después del login.
notice=st.session_state.pop("google_oauth_notice",None)
if notice:
    if notice[0]=="success":st.success(notice[1])
    else:st.error(notice[1])

try:
    cfg=config() or {}
except Exception as e:
    st.error("Ejecuta INSTALAR_GOOGLE_OAUTH.sql en Supabase. Detalle: "+str(e))
    st.stop()

if not cfg.get("refresh_token_encrypted"):
    st.link_button("Conectar con Google",auth_url(signed_state()),type="primary")
    st.info("Autoriza el acceso en Google. Si debes iniciar sesión nuevamente en el verificador al regresar, hazlo como administrador.")
    st.stop()

st.success("Cuenta de Google conectada.")
kind=st.radio("Formato del archivo",["Excel (.xlsx) en Google Drive","Google Sheets"],
              index=1 if cfg.get("kind")=="sheets" else 0)
kind="sheets" if kind=="Google Sheets" else "excel"
link=st.text_input("Enlace del archivo",value=cfg.get("file_id") or "")
sheet=st.text_input("Pestaña u hoja (vacío = primera)",value=cfg.get("sheet_name") or "")
fid=None
if link:
    try:fid=file_id(link)
    except ValueError as e:st.warning(str(e))
if st.button("Leer archivo",disabled=not bool(fid)):
    try:
        df=read_file(kind,fid,sheet)
        st.session_state.google_file_preview=(kind,fid,sheet,list(df.columns),df.head(10))
    except Exception as e:
        st.error("No se pudo leer el archivo: "+str(e))
preview=st.session_state.get("google_file_preview")
if preview and preview[:3]==(kind,fid,sheet):
    cols=preview[3]
    st.dataframe(preview[4],hide_index=True)
    def field(label,stored,hints):
        default=stored if stored in cols else next((c for c in cols if any(h in c.lower() for h in hints)),cols[0])
        return st.selectbox(label,cols,index=cols.index(default))
    code_col=field("Código de barras",cfg.get("code_column"),["codigo","código","barcode","ean"])
    name_col=field("Nombre o descripción",cfg.get("name_column"),["nombre","descrip","name"])
    price_col=field("Precio",cfg.get("price_column"),["precio","price"])
    if st.button("Guardar y activar Google",type="primary"):
        try:
            df=catalog(kind,fid,sheet,code_col,name_col,price_col)
            activate(kind,fid,sheet,code_col,name_col,price_col)
            st.success(f"Google activado. {len(df)} productos válidos.")
        except Exception as e:
            st.error("No se pudo activar: "+str(e))
st.caption("El catálogo se vuelve a consultar al caducar la caché de 5 minutos. No se copian productos a Supabase.")
if st.button("Actualizar ahora"):
    read_file.clear()
    catalog.clear()
    st.success("Caché borrada. La próxima consulta leerá los datos actualizados.")
st.divider()
if st.button("Desconectar cuenta de Google"):
    try:
        api("PATCH","google_price_source",{"id":"eq.1"},
            {"refresh_token_encrypted":None,"file_id":None,"kind":None,
             "sheet_name":"","code_column":None,"name_column":None,"price_column":None})
        api("PATCH","price_source_settings",{"id":"eq.1"},{"source_type":"local"})
        st.cache_data.clear()
        st.success("Cuenta desconectada; origen local restaurado.")
        st.rerun()
    except Exception as e:
        st.error("No se pudo desconectar: "+str(e))
