"""Administración de la zona geográfica autorizada para Consulta Móvil."""
import math
import streamlit as st
from mobile_geofence import get_settings, save_settings
from streamlit_geolocation import streamlit_geolocation

if not st.session_state.get('admin_authenticated', False):
    st.error('Esta configuración requiere iniciar sesión como administrador.')
    st.stop()

st.title('📍 Ubicación autorizada · Consulta Móvil')
st.caption('Configura el centro del establecimiento. Radio autorizado: 100 metros.')
try:
    cfg = get_settings()
except Exception:
    st.error('No se pudo leer la configuración. Comprueba Supabase y el SQL de instalación.')
    st.stop()

# Claves directamente vinculadas a los widgets para que Streamlit actualice los campos.
if 'geo_form_lat' not in st.session_state:
    st.session_state.geo_form_lat = float(cfg['latitude'])
if 'geo_form_lon' not in st.session_state:
    st.session_state.geo_form_lon = float(cfg['longitude'])
if 'geo_form_enabled' not in st.session_state:
    st.session_state.geo_form_enabled = bool(cfg['enabled'])

if st.button('📍 Detectar mi ubicación', use_container_width=True):
    st.session_state.geo_detect_requested = True
    st.session_state.geo_location_applied = False

if st.session_state.get('geo_detect_requested', False):
    st.caption('Acepta el permiso de ubicación del navegador. Si no aparece, pulsa «Reintentar detección».')
    location = streamlit_geolocation()
    if isinstance(location, dict) and location.get('latitude') is not None and location.get('longitude') is not None:
        try:
            lat = float(location['latitude'])
            lon = float(location['longitude'])
            accuracy = float(location.get('accuracy') or 0)
            if not all(map(math.isfinite, (lat, lon, accuracy))) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError('Ubicación inválida')
            if not st.session_state.get('geo_location_applied', False):
                st.session_state.geo_form_lat = lat
                st.session_state.geo_form_lon = lon
                st.session_state.geo_location_applied = True
                st.session_state.geo_detect_requested = False
                st.session_state.geo_accuracy = accuracy
                st.rerun()
        except (TypeError, ValueError):
            st.error('El navegador devolvió coordenadas inválidas.')
    else:
        st.info('Esperando ubicación. Comprueba que Safari o Chrome tenga permiso y ubicación precisa activada.')
        if st.button('Reintentar detección'):
            st.rerun()

if st.session_state.get('geo_location_applied', False):
    st.success('Ubicación detectada. Revisa las coordenadas y pulsa Guardar ubicación.')
    if st.session_state.get('geo_accuracy', 0) > 50:
        st.warning('Precisión superior a 50 metros: intenta detectar desde el exterior del local.')

# Widgets fuera del formulario: se actualizan con las claves de sesión.
st.toggle('Exigir ubicación para utilizar Consulta Móvil', key='geo_form_enabled')
st.number_input('Latitud', min_value=-90.0, max_value=90.0,
                step=0.000001, format='%.7f', key='geo_form_lat')
st.number_input('Longitud', min_value=-180.0, max_value=180.0,
                step=0.000001, format='%.7f', key='geo_form_lon')
if st.button('Guardar ubicación', type='primary', use_container_width=True):
    try:
        save_settings(st.session_state.geo_form_lat,
                      st.session_state.geo_form_lon,
                      st.session_state.geo_form_enabled)
        st.success('Ubicación guardada correctamente.')
    except Exception:
        st.error('No se pudo guardar la ubicación. Revisa la conexión a Supabase.')

st.map([{'lat': st.session_state.geo_form_lat,
         'lon': st.session_state.geo_form_lon}], zoom=16)
st.caption('La geolocalización requiere HTTPS y autorización del navegador. El GPS puede falsificarse.')
