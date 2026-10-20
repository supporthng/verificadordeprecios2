"""Fuentes de datos: asistente LAN Windows y recuperación automática desde Supabase.
No altera las fuentes activas del verificador de precios.
"""
import ipaddress
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
import streamlit as st

st.title('Fuentes de datos')
st.caption('Configura y detecta servidores sin modificar el verificador de Supabase.')

admin_password = str(st.secrets.get('ADMIN_PASSWORD', ''))
if not admin_password:
    st.error('Falta ADMIN_PASSWORD en Streamlit Secrets.')
    st.stop()
if not st.session_state.get('fuentes_admin_ok', False):
    with st.form('login_fuentes'):
        password = st.text_input('Contraseña de Administración', type='password')
        enter = st.form_submit_button('Entrar')
    if enter:
        if secrets.compare_digest(password, admin_password):
            st.session_state.fuentes_admin_ok = True
            st.rerun()
        else:
            st.error('Contraseña incorrecta')
    st.stop()

URL = str(st.secrets.get('SUPABASE_URL', '')).strip().rstrip('/')
KEY = str(st.secrets.get('SUPABASE_SERVICE_ROLE_KEY', '')).strip()
if not URL or not KEY:
    st.error('Configura SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY en Streamlit Secrets.')
    st.stop()

HEADERS = {
    'apikey': KEY,
    'Authorization': 'Bearer ' + KEY,
    'Content-Type': 'application/json',
    'Prefer': 'return=representation',
}
COLUMNS = 'id,status,selected_host,selected_port,selected_engine,selected_database,expires_at,created_at'


def supabase(method, params=None, payload=None):
    response = requests.request(
        method, URL + '/rest/v1/lan_discovery_requests',
        params=params, json=payload, timeout=15, headers=HEADERS,
    )
    response.raise_for_status()
    return response.json()


def get_request(request_id):
    try:
        uuid.UUID(str(request_id))
    except (ValueError, TypeError, AttributeError):
        return None
    rows = supabase('GET', params={'id': 'eq.' + str(request_id), 'select': COLUMNS})
    return rows[0] if rows else None


def completed(row):
    return bool(row and row.get('status') == 'selected' and row.get('selected_database'))


def store_selection(row):
    st.session_state.lan_selection = row
    st.session_state.pop('lan_seleccion_anterior', None)
    st.session_state.lan_request_id = row['id']
    st.session_state.pop('lan_request_expires', None)


# El conector devuelve ?lan_result=<UUID>. El enlace puede abrir una sesión nueva,
# por eso se recupera directamente de Supabase, sin depender de session_state.
returned_id = st.query_params.get('lan_result')
if returned_id:
    try:
        result = get_request(returned_id)
        if completed(result):
            store_selection(result)
            st.query_params.clear()
        elif result:
            st.warning('La selección todavía no está completa. Se comprobará nuevamente.')
        else:
            st.warning('No se encontró la solicitud devuelta por Windows.')
    except requests.RequestException:
        st.warning('No se pudo recuperar el resultado devuelto por Windows. Inténtalo de nuevo.')

# Recuperar solicitudes terminadas al volver a la página, aunque Streamlit
# haya perdido su estado de sesión. Mostrar una selección previa como recuperación
# y permitir iniciar otra búsqueda cuando se necesite.
if not st.session_state.get('lan_selection'):
    try:
        request_id = st.session_state.get('lan_request_id')
        row = get_request(request_id) if request_id else None
        if completed(row):
            store_selection(row)
        elif not request_id and not st.session_state.get('lan_force_new') and not st.session_state.get('lan_seleccion_anterior'):
            recent = supabase('GET', params={
                'status': 'eq.selected',
                'selected_database': 'not.is.null',
                'order': 'created_at.desc',
                'limit': '1',
                'select': COLUMNS,
            })
            if recent:
                store_selection(recent[0])
    except requests.RequestException:
        st.warning('No se pudo comprobar la última selección en Supabase.')

st.subheader('Buscar servidores desde Windows')
st.info('La búsqueda y las credenciales SQL se gestionan en el conector Windows de tu red.')
bridge_ip = st.text_input('IP del equipo Windows que ejecuta el conector', value='10.0.0.190',
                          help='IP del conector, no del servidor SQL.')
bridge_port = st.number_input('Puerto del conector Windows', min_value=1, max_value=65535, value=8765)


def preparar_busqueda():
    ip = ipaddress.ip_address(bridge_ip.strip())
    if ip.version != 4 or not ip.is_private:
        raise ValueError('Usa una IP privada IPv4 del equipo Windows.')
    now = datetime.now(timezone.utc)
    request_id = str(uuid.uuid4())
    expiry = now + timedelta(minutes=15)
    supabase('POST', payload={'id': request_id, 'expires_at': expiry.isoformat(), 'status': 'pending'})
    st.session_state.lan_request_id = request_id
    st.session_state.lan_request_expires = expiry
    st.session_state.lan_bridge_address = (str(ip), int(bridge_port))
    st.session_state.lan_bridge_url = (
        f'http://{ip}:{int(bridge_port)}/?{urlencode({"request_id": request_id})}'
    )
    st.session_state.pop('lan_selection', None)


selected = st.session_state.get('lan_selection')
if selected:
    st.success('Configuración recibida desde Windows y guardada en Supabase.')
    st.write('**Servidor:**', selected.get('selected_host') or '—')
    st.write('**Puerto:**', selected.get('selected_port') or '—')
    st.write('**Motor:**', selected.get('selected_engine') or '—')
    st.write('**Base de datos:**', selected.get('selected_database') or '—')
    # Reutiliza el canal de catálogo que ya usa Consulta de Base de Datos.
    # No emplear external_metadata_jobs: su restricción kind no acepta 'connection'.
    if st.button('Probar conexión', type='primary', key='test_sql_connection'):
        try:
            response = requests.get(URL + '/rest/v1/external_price_sources',
                params={'select': 'id,name,engine,host,port,database,enabled',
                        'enabled': 'eq.true'}, headers=HEADERS, timeout=15)
            response.raise_for_status()
            matches = [row for row in response.json()
                       if str(row.get('engine', '')).casefold() == str(selected.get('selected_engine', '')).casefold()
                       and str(row.get('host', '')).strip().casefold() == str(selected.get('selected_host', '')).strip().casefold()
                       and str(row.get('port', '')) == str(selected.get('selected_port', ''))
                       and str(row.get('database', '')).strip().casefold() == str(selected.get('selected_database', '')).strip().casefold()]
            if not matches:
                st.warning('La base seleccionada en Windows aún no tiene una fuente de productos configurada y habilitada. '
                           'Configura su tabla y columnas antes de realizar esta prueba.')
            elif len(matches) > 1:
                st.warning('Hay varias fuentes configuradas para esta base de datos. '
                           'Elige cuál deseas probar desde Consulta de Base de Datos.')
            else:
                job = {
                    'configuration_id': matches[0]['id'],
                    'page_number': 1,
                    'page_size': 1,
                    'search_term': '',
                    'status': 'pending',
                    'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=3)).isoformat(),
                }
                response = requests.post(URL + '/rest/v1/external_catalog_jobs',
                    json=job, headers=HEADERS, timeout=15)
                response.raise_for_status()
                st.session_state.lan_test_job_id = response.json()[0]['id']
                st.session_state.lan_test_started = datetime.now(timezone.utc)
                st.info('Prueba enviada al conector Windows. Esperando resultado…')
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else '?'
            st.error(f'No se pudo crear la prueba en Supabase (HTTP {status}).')
            st.caption('Verifica que exista external_catalog_jobs y que el conector Windows esté actualizado.')
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
            st.error('No se pudo iniciar la prueba de conexión: ' + type(exc).__name__)

    @st.fragment(run_every='2s')
    def verificar_conexion_sql():
        job_id = st.session_state.get('lan_test_job_id')
        if not job_id:
            return
        started = st.session_state.get('lan_test_started', datetime.now(timezone.utc))
        if (datetime.now(timezone.utc) - started).total_seconds() > 180:
            st.session_state.pop('lan_test_job_id', None)
            st.error('La prueba venció sin respuesta del conector Windows.')
            return
        try:
            response = requests.get(URL + '/rest/v1/external_catalog_jobs',
                params={'id': 'eq.' + str(job_id), 'select': 'status,result,error_message'},
                headers=HEADERS, timeout=15)
            response.raise_for_status()
            rows = response.json()
            if not rows:
                st.error('No se encontró la solicitud de prueba.')
                st.session_state.pop('lan_test_job_id', None)
            elif rows[0]['status'] == 'done':
                st.success('Conexión comprobada: el conector Windows consultó correctamente la base de datos.')
                st.caption('Prueba de solo lectura, sin modificar productos.')
                st.session_state.pop('lan_test_job_id', None)
            elif rows[0]['status'] == 'error':
                st.error('Error del conector: ' + str(rows[0].get('error_message') or 'No especificado'))
                st.session_state.pop('lan_test_job_id', None)
            else:
                st.info('Comprobando conexión real desde Windows…')
        except requests.RequestException:
            st.warning('Esperando respuesta de Supabase…')

    verificar_conexion_sql()
    # La acción de agregar un servidor requiere confirmación. Nunca elimina
    # registros de Supabase ni modifica la fuente activa del verificador.
    if st.button('Configurar otro servidor', key='lan_abrir_confirmacion'):
        st.session_state['lan_confirmar_nuevo_servidor'] = True

    if st.session_state.get('lan_confirmar_nuevo_servidor', False):
        st.warning(
            '¿Deseas iniciar la configuración de otro servidor? '
            'La conexión actual seguirá guardada en Supabase y la fuente activa '
            'no cambiará. Solo se abrirá un nuevo asistente.'
        )
        col_confirmar, col_cancelar = st.columns(2)
        with col_confirmar:
            confirmar = st.button('Sí, configurar otro servidor',
                                  type='primary', key='lan_confirmar_agregar')
        with col_cancelar:
            cancelar = st.button('Cancelar', key='lan_cancelar_agregar')
        if cancelar:
            st.session_state.pop('lan_confirmar_nuevo_servidor', None)
            st.rerun()
        if confirmar:
            # Copia temporal para poder identificar la conexión anterior durante
            # la configuración. No se borra ni se actualiza la BD existente.
            st.session_state['lan_seleccion_anterior'] = dict(selected)
            st.session_state.pop('lan_confirmar_nuevo_servidor', None)
            for state_key in ('lan_selection', 'lan_request_id',
                              'lan_request_expires', 'lan_bridge_url'):
                st.session_state.pop(state_key, None)
            st.session_state['lan_force_new'] = True
            st.rerun()
else:
    if st.session_state.get('lan_seleccion_anterior'):
        anterior = st.session_state['lan_seleccion_anterior']
        st.info('Conexión anterior conservada: ' + str(anterior.get('selected_host') or '—')
                + ' / ' + str(anterior.get('selected_database') or '—')
                + '. Configurar otra no la elimina ni la desactiva.')
        if st.button('Cancelar nueva configuración y volver a la anterior',
                     key='lan_volver_anterior'):
            st.session_state['lan_selection'] = st.session_state.pop('lan_seleccion_anterior')
            st.session_state['lan_request_id'] = st.session_state['lan_selection']['id']
            for state_key in ('lan_request_expires', 'lan_bridge_url', 'lan_force_new'):
                st.session_state.pop(state_key, None)
            st.rerun()
    if st.session_state.pop('lan_force_new', False):
        st.session_state.lan_request_id = None
    request_id = st.session_state.get('lan_request_id')
    expires = st.session_state.get('lan_request_expires')
    if (not request_id or not expires or not st.session_state.get('lan_bridge_url')
            or datetime.now(timezone.utc) >= expires):
        try:
            preparar_busqueda()
        except (ValueError, requests.RequestException) as exc:
            st.error('No se pudo preparar la búsqueda. Comprueba la IP y Supabase.')
            st.caption(type(exc).__name__)
    if st.session_state.get('lan_bridge_url'):
        st.link_button('Iniciar búsqueda en Windows', st.session_state.lan_bridge_url, type='primary')
        st.caption('El conector Windows abre el asistente completo: servidor, credenciales y base de datos.')

    @st.fragment(run_every='3s')
    def recibir_seleccion_automatica():
        rid = st.session_state.get('lan_request_id')
        if not rid or st.session_state.get('lan_selection'):
            return
        try:
            row = get_request(rid)
            if completed(row):
                store_selection(row)
                st.rerun(scope='app')
            elif row and row.get('status') == 'selected':
                st.warning('El servidor fue seleccionado, pero todavía no hay una base de datos confirmada.')
            elif row:
                st.info('Esperando que termines el asistente en Windows…')
            else:
                st.warning('La solicitud ya no existe. Recarga la página para iniciar otra.')
        except requests.RequestException:
            st.warning('No se pudo comprobar la selección. Se reintentará automáticamente.')

    recibir_seleccion_automatica()

st.divider()
st.subheader('Estado de la configuración')
if selected:
    st.info('La fuente fue identificada y guardada. Esto no cambia automáticamente la conexión '
            'que utiliza el verificador de precios ni activa consultas de facturación.')
else:
    st.caption('Completa el asistente Windows para mostrar aquí la base de datos seleccionada.')
