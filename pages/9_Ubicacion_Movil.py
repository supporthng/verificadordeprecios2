"""Administración: define el punto autorizado para Consulta Móvil."""
import streamlit as st
from mobile_geofence import get_settings, save_settings

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
with st.form('geo_mobile_admin'):
    enabled = st.toggle('Exigir ubicación para utilizar Consulta Móvil', value=bool(cfg['enabled']))
    lat = st.number_input('Latitud', min_value=-90.0, max_value=90.0,
                          value=float(cfg['latitude']), format='%.7f', step=0.000001)
    lon = st.number_input('Longitud', min_value=-180.0, max_value=180.0,
                          value=float(cfg['longitude']), format='%.7f', step=0.000001)
    st.info('Radio autorizado: 100 metros. Para obtener coordenadas, mantén pulsado el punto del local en un mapa y copia su latitud y longitud.')
    submitted = st.form_submit_button('Guardar ubicación', type='primary')
if submitted:
    try:
        save_settings(lat, lon, enabled)
        st.success('Ubicación guardada. Se aplicará en la próxima comprobación del móvil.')
    except Exception:
        st.error('No se pudo guardar la ubicación. Revisa Supabase.')
st.map([{'lat': lat, 'lon': lon}], zoom=16)
st.warning('El GPS del navegador puede ser falsificado. Esta restricción es de uso operativo, no una garantía antifraude.')
