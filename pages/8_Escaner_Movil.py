"""Consulta móvil con cámara fotográfica y lector Bluetooth HID."""
import hashlib
from io import BytesIO
import streamlit as st
import requests
from datetime import datetime, timedelta, timezone
import time

st.title('📱 Escáner móvil')
st.caption('Cámara o lector Bluetooth · utiliza la fuente de datos activa')
for key, default in {'movil_codigo':'','movil_ultimo':'','movil_producto':None,'movil_job':None,'movil_error':'','movil_foto':''}.items():
    st.session_state.setdefault(key,default)

def api(method,table,params=None,payload=None):
    url=str(st.secrets.get('SUPABASE_URL','')).rstrip('/')
    key=str(st.secrets.get('SUPABASE_SERVICE_ROLE_KEY',''))
    if not url or not key: raise RuntimeError('Faltan credenciales de Supabase.')
    r=requests.request(method,url+'/rest/v1/'+table,params=params,json=payload,
        headers={'apikey':key,'Authorization':'Bearer '+key,'Content-Type':'application/json','Prefer':'return=representation'},timeout=15)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=90,show_spinner=False)
def productos_locales():
    url=str(st.secrets.get('SUPABASE_URL','')).rstrip('/')
    key=str(st.secrets.get('SUPABASE_ANON_KEY',''))
    rows=[]; offset=0
    while True:
        r=requests.get(url+'/rest/v1/products',params={'select':'barcode,name,price','order':'barcode.asc','limit':500,'offset':offset},headers={'apikey':key,'Authorization':'Bearer '+key},timeout=25)
        r.raise_for_status(); batch=r.json(); rows.extend(batch)
        if len(batch)<500: break
        offset+=500
    return rows

def consultar(code):
    code=str(code).strip()
    if not code:return
    st.session_state.movil_ultimo=code
    st.session_state.movil_producto=None
    st.session_state.movil_job=None
    st.session_state.movil_error=''
    try:
        settings=api('GET','price_source_settings',{'id':'eq.1','select':'source_type'})
        if not settings: raise RuntimeError('Configura primero la fuente de datos.')
        mode=settings[0]['source_type']
        if mode=='local':
            rows=productos_locales()
        elif mode=='google':
            from google_oauth_source import config,catalog
            cfg=config()
            if not cfg or not cfg.get('file_id'): raise RuntimeError('Configura Google desde Administración.')
            df=catalog(cfg['kind'],cfg['file_id'],cfg['sheet_name'] or '',cfg['code_column'],cfg['name_column'],cfg['price_column'])
            rows=df.to_dict('records')
        elif mode=='external':
            sources=api('GET','external_price_sources',{'enabled':'eq.true','select':'id','limit':'2'})
            if len(sources)!=1: raise RuntimeError('Debe existir exactamente una fuente externa habilitada.')
            jobs=api('POST','external_price_jobs',payload={'configuration_id':sources[0]['id'],'barcode':code,'status':'pending','expires_at':(datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat()})
            if not jobs or not jobs[0].get('id'): raise RuntimeError('No se pudo registrar la consulta.')
            st.session_state.movil_job={'id':jobs[0]['id'],'started':time.monotonic()}
            return
        else: raise RuntimeError('Fuente desconocida.')
        st.session_state.movil_producto=next((r for r in rows if str(r.get('barcode','')).strip()==code),None)
    except Exception as exc:
        st.session_state.movil_error='No se pudo consultar la fuente seleccionada: '+str(exc)

tab1,tab2=st.tabs(['📷 Cámara','⌨️ Bluetooth / Manual'])
with tab1:
    st.caption('Fotografía el código con buena iluminación. La consulta comienza al reconocerlo.')
    photo=st.camera_input('Tomar foto del código de barras',key='movil_camara')
    if photo:
        data=photo.getvalue(); digest=hashlib.sha256(data).hexdigest()
        if digest!=st.session_state.movil_foto:
            st.session_state.movil_foto=digest
            try:
                import zxingcpp
                from PIL import Image,ImageOps
                img=ImageOps.exif_transpose(Image.open(BytesIO(data))).convert('RGB')
                found=zxingcpp.read_barcodes(img)
                if found:
                    consultar(found[0].text)
                    st.success('Código leído: '+found[0].text)
                else: st.warning('No se reconoció el código. Acerca la cámara y repite la foto.')
            except ImportError: st.error('Falta instalar zxing-cpp (requirements.txt).')
            except Exception: st.error('No se pudo procesar la fotografía.')
with tab2:
    st.caption('Empareja el lector Bluetooth en modo teclado HID y configura sufijo Enter.')
    st.text_input('Código de barras',key='movil_codigo',placeholder='Escanea o escribe el código',on_change=lambda:consultar(st.session_state.movil_codigo))
    if st.button('Consultar',use_container_width=True): consultar(st.session_state.movil_codigo)

@st.fragment(run_every='2s')
def resultado():
    job=st.session_state.movil_job
    if job:
        if time.monotonic()-job['started']>25:
            st.session_state.movil_job=None
            st.session_state.movil_error='La fuente externa no respondió en 25 segundos.'
        else:
            try:
                rows=api('GET','external_price_jobs',{'id':'eq.'+str(job['id']),'select':'status,result,error_message'})
                if not rows: raise RuntimeError('Solicitud no encontrada.')
                item=rows[0]
                if item['status']=='done':
                    st.session_state.movil_producto=item.get('result')
                    st.session_state.movil_job=None
                elif item['status']=='error':
                    st.session_state.movil_error='Error de consulta en la base externa.'
                    st.session_state.movil_job=None
                else:
                    st.info('Consultando base externa…')
                    return
            except Exception:
                st.session_state.movil_error='No se pudo obtener la respuesta del conector.'
                st.session_state.movil_job=None
    if st.session_state.movil_error: st.error(st.session_state.movil_error)
    elif st.session_state.movil_ultimo:
        product=st.session_state.movil_producto
        if product:
            st.success('PRODUCTO ENCONTRADO')
            st.subheader(str(product.get('name') or 'Sin descripción'))
            try: st.metric('PRECIO',f"RD$ {float(product.get('price')):,.2f}")
            except (ValueError,TypeError): st.metric('PRECIO',str(product.get('price') or 'No disponible'))
            st.caption('Código: '+str(product.get('barcode') or st.session_state.movil_ultimo))
        elif not st.session_state.movil_job:
            st.warning('PRODUCTO NO ENCONTRADO')
            st.caption('Código: '+st.session_state.movil_ultimo)
resultado()
