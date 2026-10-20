"""Fuentes de Datos: Conexión y Selección de la fuente activa."""
import runpy
import streamlit as st
from auth_usuarios import current_user, allowed

st.title("Fuentes de Datos")
user = current_user()
if not allowed(user, "configurar"):
    st.error("No tienes permiso para configurar fuentes de datos.")
    st.stop()

tab_connection, tab_selection = st.tabs(["🔌 Conexión", "🎯 Selección"])

with tab_connection:
    st.caption("Conecta y configura los orígenes. Guardar una conexión no cambia la fuente activa.")
    if allowed(user, "cargar_archivo"):
        with st.expander("📁 Cargar archivo Excel local", expanded=False):
            st.caption("Carga, revisa y publica el archivo Excel usando el módulo actual, sin cambiar su funcionamiento.")
            runpy.run_path("pages/_fuentes_carga_excel.py", run_name="__main__")
    with st.expander("☁️ Google Drive / Sheets", expanded=True):
        runpy.run_path("pages/_fuentes_google_conexion.py", run_name="__main__")
    with st.expander("🖥️ Base de datos externa / Conector Windows", expanded=False):
        runpy.run_path("pages/_fuentes_conexion_existente.py", run_name="__main__")
    st.info("Supabase utiliza la conexión configurada en Streamlit Secrets.")

with tab_selection:
    st.subheader("Fuente activa de consulta de precios")
    st.caption("Solo una fuente se utiliza a la vez. Cambiarla no borra productos ni conexiones.")
    try:
        from google_oauth_source import api, config, catalog
        settings = api("GET", "price_source_settings", {"id": "eq.1", "select": "source_type"})
        if not settings:
            st.error("Falta el registro id=1 en price_source_settings.")
            st.stop()
        current = settings[0].get("source_type") or "local"
        gcfg = config() or {}
        google_ready = all(gcfg.get(k) for k in
                           ("refresh_token_encrypted", "kind", "file_id",
                            "code_column", "name_column", "price_column"))
        external = api("GET", "external_price_sources",
                       {"enabled": "eq.true", "select": "id,name", "limit": "2"})
        external_ready = len(external) == 1
        options = {
            "local": "Supabase (productos del sistema)",
            "external": "Base de datos externa",
            "google": "Google Drive / Sheets",
        }
        st.info("Fuente activa: " + options.get(current, current))
        choice = st.radio("Selecciona de dónde se consultarán los códigos",
                          options=list(options.keys()),
                          format_func=lambda x: options[x],
                          index=list(options).index(current) if current in options else 0)
        if choice == "google" and not google_ready:
            st.warning("Primero conecta Google y guarda un archivo con sus columnas en Conexión.")
        if choice == "external" and not external_ready:
            st.warning("Configura exactamente una fuente externa habilitada antes de seleccionarla.")
        if choice == "local":
            st.caption("Esta opción consulta los productos almacenados en Supabase. "
                       "No es una consulta directa a un archivo Excel local.")
        valid = (choice == "local" or
                 (choice == "google" and google_ready) or
                 (choice == "external" and external_ready))
        if st.button("Guardar fuente activa", type="primary", disabled=not valid):
            if choice == "google":
                # Confirmar que el archivo y la asignación siguen siendo legibles.
                catalog(gcfg["kind"], gcfg["file_id"], gcfg.get("sheet_name") or "",
                        gcfg["code_column"], gcfg["name_column"], gcfg["price_column"])
            api("PATCH", "price_source_settings", {"id": "eq.1"}, {"source_type": choice})
            st.cache_data.clear()
            st.success("Fuente activa guardada: " + options[choice])
            st.rerun()
    except Exception as exc:
        st.error("No se pudo consultar o guardar la fuente: " + str(exc))
