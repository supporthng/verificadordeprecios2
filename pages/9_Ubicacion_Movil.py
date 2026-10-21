"""Administración: define el punto autorizado para Consulta Móvil."""
import streamlit as st
from mobile_geofence import get_settings, save_settings
from streamlit_geolocation import streamlit_geolocation
import math

if not st.session_state.get('admin_authenticated', False):
    st.error('Esta configuración requiere iniciar sesión como administrador.')
    st.stop()

st.title('📍 Ubicación autorizada · Consulta Móvil')
st.caption('Configura el centro del establecimiento. El radio de consulta es fijo: 100 metros.')
try:
    cfg = get_settings()
except Exception:
    st.error('No se pudo leer la configuración. Ejecuta INSTALAR_GEO_MOVIL.sql en Supabase y revisa la conexión.')
    st.stop()
# Detectar la ubicación del dispositivo del administrador sin introducir coordenadas.
# El componente utiliza la API de geolocalización del navegador (requiere HTTPS).
if st.button('📍 Detectar mi ubicación', use_container_width=True):
    st.session_state['geo_detect_requested'] = True
if st.session_state.get('geo_detect_requested', False):
    st.caption('Autoriza la ubicación en el navegador. Espera unos segundos si es necesario.')
    location = streamlit_geolocation()
    if isinstance(location, dict) and location.get('latitude') is not None and location.get('longitude') is not None:
        try:
            detected_lat = float(location['latitude'])
            detected_lon = float(location['longitude'])
            accuracy = float(location.get('accuracy') or 0)
            if not all(math.isfinite(v) for v in (detected_lat, detected_lon, accuracy)) or not (-90 <= detected_lat <= 90 and -180 <= detected_lon <= 180):
                raise ValueError('Coordenadas inválidas')
            st.session_state['geo_admin_lat'] = detected_lat
            st.session_state['geo_admin_lon'] = detected_lon
            st.success(f'Ubicación detectada (precisión aproximada ±{accuracy:.0f} m). Revisa y pulsa Guardar ubicación.')
            if accuracy > 50:
                st.warning('La ubicación es poco precisa. Activa ubicación precisa antes de guardar el centro del local.')
        except (ValueError, TypeError):
            st.error('No se pudo leer una ubicación válida. Revisa el permiso del navegador.')
    else:
        st.info('Si no aparece la ubicación, habilita el permiso de ubicación y vuelve a intentarlo.')

if 'geo_admin_lat' not in st.session_state:
    st.session_state['geo_admin_lat'] = float(cfg['latitude'])
if 'geo_admin_lon' not in st.session_state:
    st.session_state['geo_admin_lon'] = float(cfg['longitude'])

with st.form('geo_mobile_admin'):
    enabled = st.toggle('Exigir ubicación para utilizar Consulta Móvil', value=bool(cfg['enabled']))
    lat = st.number_input('Latitud', min_value=-90.0, max_value=90.0,
                          value=float(st.session_state['geo_admin_lat']), format='%.7f', step=0.000001)
    lon = st.number_input('Longitud', min_value=-180.0, max_value=180.0,
                          value=float(st.session_state['geo_admin_lon']), format='%.7f', step=0.000001)
    st.info('Radio autorizado: 100 metros. Para obtener coordenadas, mantén pulsado el punto del local en un mapa y copia su latitud y longitud.')
    submitted = st.form_submit_button('Guardar ubicación', type='primary')
if submitted:
    try:
        save_settings(lat, lon, enabled)
        st.session_state['geo_admin_lat'] = lat
        st.session_state['geo_admin_lon'] = lon
        st.success('Ubicación guardada. Se aplicará en la próxima comprobación del móvil.')
    except Exception:
        st.error('No se pudo guardar la ubicación. Revisa Supabase.')
st.map([{'lat': lat, 'lon': lon}], zoom=16)
st.warning('El GPS del navegador puede ser falsificado. Esta restricción es de uso operativo, no una garantía antifraude.')
