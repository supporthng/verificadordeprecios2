"""Configuración de ubicación del establecimiento mediante GPS del navegador."""
import math
import streamlit as st
from mobile_geofence import get_settings, save_settings
from streamlit_geolocation import streamlit_geolocation
import pandas as pd
import requests

if not st.session_state.get('admin_authenticated', False):
    st.error('Esta configuración requiere iniciar sesión como administrador.')
    st.stop()

st.title('📍 Ubicación autorizada · Consulta Móvil')
st.caption('Centro del establecimiento · radio permitido: 100 metros.')
try:
    cfg = get_settings()
except Exception:
    st.error('No se pudo leer la configuración geográfica de Supabase.')
    st.stop()

for key, value in [('geo_form_lat',float(cfg['latitude'])),
                   ('geo_form_lon',float(cfg['longitude'])),
                   ('geo_form_enabled',bool(cfg['enabled'])),
                   ('geo_attempt',0),('geo_detecting',False)]:
    st.session_state.setdefault(key,value)

st.info('Pulsa Detectar mi ubicación desde el dispositivo que está en el establecimiento. El navegador debe solicitar permiso para compartir tu ubicación.')
if st.button('📍 Detectar mi ubicación', use_container_width=True):
    st.session_state.geo_attempt += 1
    st.session_state.geo_detecting = True
    st.session_state.geo_detect_error = None

# El componente debe permanecer montado después del clic. La clave cambia en
# cada intento para forzar un montaje nuevo y una nueva solicitud al navegador.
if st.session_state.geo_detecting:
    st.caption('Solicitando ubicación al navegador… Acepta el permiso cuando aparezca.')
    try:
        location = streamlit_geolocation(key=f'geo_permission_{st.session_state.geo_attempt}')
    except Exception as exc:
        st.session_state.geo_detecting = False
        st.error('No se pudo iniciar la solicitud de ubicación del navegador.')
        location = None
    if isinstance(location,dict) and location.get('latitude') is not None and location.get('longitude') is not None:
        try:
            lat, lon = float(location['latitude']),float(location['longitude'])
            accuracy = float(location.get('accuracy') or 0)
            if not all(map(math.isfinite,(lat,lon,accuracy))) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError('Coordenadas inválidas')
            st.session_state.geo_form_lat = lat
            st.session_state.geo_form_lon = lon
            st.session_state.geo_accuracy = accuracy
            st.session_state.geo_detecting = False
            st.session_state.geo_location_applied = True
            st.rerun()
        except (ValueError,TypeError):
            st.error('El navegador devolvió coordenadas inválidas.')
    elif isinstance(location,dict) and location.get('error'):
        st.error('El navegador no pudo obtener la ubicación: '+str(location['error']))
        st.session_state.geo_detecting = False
    else:
        st.warning('Si no aparece el permiso, revisa los ajustes de ubicación del navegador y vuelve a pulsar Detectar mi ubicación.')
        st.caption('En iPhone: Ajustes → Privacidad y seguridad → Localización → Safari (o Chrome), permitir ubicación precisa. En Safari también revisa aA → Configuración del sitio web → Ubicación → Preguntar. Abre el enlace directamente en Safari/Chrome, no en el navegador interno de otra aplicación.')

if st.session_state.get('geo_location_applied'):
    st.success('Coordenadas detectadas. Pulsa Guardar ubicación para aplicarlas.')
    if st.session_state.get('geo_accuracy',0)>50:
        st.warning('Precisión GPS baja. Intenta nuevamente cerca de una ventana o al aire libre.')

st.toggle('Exigir ubicación para Consulta Móvil',key='geo_form_enabled')
st.number_input('Latitud',min_value=-90.0,max_value=90.0,step=0.000001,format='%.7f',key='geo_form_lat')
st.number_input('Longitud',min_value=-180.0,max_value=180.0,step=0.000001,format='%.7f',key='geo_form_lon')

st.divider()
st.subheader('Buscar y seleccionar establecimiento')
st.caption('Busca una dirección o establecimiento. También puedes introducir las coordenadas manualmente.')
address = st.text_input('Dirección o nombre del establecimiento', placeholder='Ej.: calle, sector, ciudad, República Dominicana')
if st.button('🔎 Buscar en el mapa', use_container_width=True):
    if not address.strip():
        st.warning('Escribe una dirección o nombre para buscar.')
    else:
        try:
            response = requests.get('https://nominatim.openstreetmap.org/search',
                params={'q':address.strip(),'format':'json','limit':5,'countrycodes':'do'},
                headers={'User-Agent':'VerificadorDePrecios/1.0 (business-location-picker)'}, timeout=12)
            response.raise_for_status()
            matches = response.json()
            st.session_state.geo_matches = matches
            if not matches:
                st.warning('No encontramos resultados. Prueba con una dirección más específica o introduce las coordenadas.')
        except requests.RequestException:
            st.error('No se pudo consultar el buscador de direcciones. Puedes escribir las coordenadas manualmente.')
matches = st.session_state.get('geo_matches',[])
if matches:
    choices = {str(i):r.get('display_name', 'Resultado '+str(i)) for i,r in enumerate(matches)}
    choice = st.selectbox('Selecciona la ubicación encontrada', options=list(choices),format_func=lambda i:choices[i])
    if st.button('📍 Usar esta ubicación',use_container_width=True):
        r=matches[int(choice)]
        st.session_state.geo_form_lat=float(r['lat'])
        st.session_state.geo_form_lon=float(r['lon'])
        st.session_state.geo_location_applied=False
        st.success('Coordenadas cargadas. Revisa el mapa y pulsa Guardar ubicación.')
        st.rerun()

lat, lon = float(st.session_state.geo_form_lat),float(st.session_state.geo_form_lon)
if lat == 0 and lon == 0:
    st.info('Busca el establecimiento o introduce latitud y longitud para visualizar el mapa.')
else:
    # Mapa nativo de Streamlit, sin iframe de Folium que puede quedar en blanco.
    st.map(pd.DataFrame([{'lat':lat,'lon':lon}]),zoom=16,size=140)
    st.caption('Marcador: centro seleccionado. Radio autorizado: 100 metros alrededor del punto. '
               'Puedes afinar las coordenadas en los campos superiores.')
    st.link_button('Abrir ubicación en Google Maps',
                   f'https://www.google.com/maps?q={lat:.7f},{lon:.7f}',use_container_width=True)

if st.button('Guardar ubicación',type='primary',use_container_width=True):
    try:
        save_settings(st.session_state.geo_form_lat,st.session_state.geo_form_lon,st.session_state.geo_form_enabled)
        st.success('Ubicación guardada correctamente.')
    except Exception:
        st.error('No se pudo guardar en Supabase.')
