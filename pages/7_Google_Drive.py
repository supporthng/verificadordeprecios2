import requests
import streamlit as st
from auth_usuarios import current_user, allowed
from google_drive_source import read_source, products, file_id, service_credentials

st.title("☁️ Google Drive y Google Sheets")
user=current_user()
if not user or not allowed(user,"configurar"):
    st.error("No tienes permiso.");st.stop()
try:
    st.info("Comparte el archivo como Lector con: "+service_credentials().service_account_email)
except Exception:
    st.error("Configura GOOGLE_SERVICE_ACCOUNT en Secrets.");st.stop()
url=str(st.secrets.get("SUPABASE_URL","")).rstrip("/")
key=str(st.secrets.get("SUPABASE_SERVICE_ROLE_KEY",""))
headers={"apikey":key,"Authorization":"Bearer "+key,"Content-Type":"application/json","Prefer":"return=representation"}
def api(method,table,params=None,data=None):
    r=requests.request(method,url+"/rest/v1/"+table,params=params,json=data,headers=headers,timeout=20)
    r.raise_for_status()
    return r.json()
try:
    rows=api("GET","cloud_price_sources",{"id":"eq.1","select":"*"})
    saved=rows[0] if rows else {}
except requests.RequestException:
    st.error("Ejecuta INSTALAR_GOOGLE_DRIVE.sql en Supabase.");st.stop()
kind=st.radio("Origen",["Excel en Google Drive","Google Sheets"],index=1 if saved.get("kind")=="sheets" else 0)
kind="sheets" if kind=="Google Sheets" else "excel"
link=st.text_input("Enlace del archivo",value=saved.get("file_id",""))
sheet=st.text_input("Nombre de hoja (vacío = primera)",value=saved.get("sheet_name",""))
fid=None
if link:
    try: fid=file_id(link)
    except ValueError as e: st.warning(str(e))
if st.button("Leer archivo y elegir columnas",disabled=not bool(fid)):
    try:
        data=read_source(kind,fid,sheet)
        st.session_state.drive_preview_key=(kind,fid,sheet)
        st.session_state.drive_columns=list(data.columns)
        st.session_state.drive_preview=data.head(10)
    except Exception as exc: st.error("No se pudo leer: "+str(exc))
if fid and st.session_state.get("drive_preview_key")== (kind,fid,sheet):
    cols=st.session_state.drive_columns
    st.dataframe(st.session_state.drive_preview,hide_index=True)
    def choose(label,old,hints):
        default=old if old in cols else next((c for c in cols if any(h in c.lower() for h in hints)),cols[0])
        return st.selectbox(label,cols,index=cols.index(default))
    code=choose("Código",saved.get("code_column"),["codigo","código","barcode","ean"])
    name=choose("Descripción",saved.get("description_column"),["nombre","descrip","name"])
    price=choose("Precio",saved.get("price_column"),["precio","price"])
    if st.button("Guardar y activar esta fuente",type="primary"):
        try:
            df=products(kind,fid,sheet,code,name,price)
            api("POST","cloud_price_sources",{"on_conflict":"id"},
                {"id":1,"kind":kind,"file_id":fid,"sheet_name":sheet,
                 "code_column":code,"description_column":name,"price_column":price})
            api("PATCH","price_source_settings",{"id":"eq.1"},{"source_type":"cloud"})
            st.success(f"Activado: {len(df)} productos. Caché de 5 minutos.")
        except Exception as exc: st.error("No se pudo activar: "+str(exc))
if saved:
    if st.button("Actualizar ahora"):
        read_source.clear();products.clear()
        st.success("Caché limpiada. Se consultará el archivo en la próxima búsqueda.")
    if st.button("Volver a Supabase"):
        try:
            api("PATCH","price_source_settings",{"id":"eq.1"},{"source_type":"local"})
            st.success("Catálogo Supabase activado.")
        except Exception as exc: st.error(str(exc))
