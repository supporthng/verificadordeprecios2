"""Catálogo paginado de Supabase o de una conexión externa configurable."""
from datetime import datetime, timedelta, timezone
import hmac
import math
import requests
import streamlit as st

st.title("📋 Consulta de Base de Datos")
st.caption("Listado de productos de la fuente seleccionada. No modifica precios ni configuraciones.")
password = str(st.secrets.get("ADMIN_PASSWORD", ""))
if not password:
    st.error("Falta ADMIN_PASSWORD en Secrets.")
    st.stop()
if not st.session_state.get("catalog_admin_ok"):
    with st.form("catalog_login"):
        typed = st.text_input("Contraseña de administración", type="password")
        submit = st.form_submit_button("Entrar")
    if submit:
        if hmac.compare_digest(typed, password):
            st.session_state.catalog_admin_ok = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta")
    st.stop()

url = str(st.secrets.get("SUPABASE_URL", "")).strip().rstrip("/")
key = str(st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")).strip()
if not url or not key:
    st.error("Faltan credenciales de Supabase en Secrets.")
    st.stop()
headers = {"apikey": key, "Authorization": "Bearer " + key,
           "Content-Type": "application/json", "Prefer": "return=representation"}

def api(method, table, params=None, data=None, extra_headers=None):
    response = requests.request(method, url + "/rest/v1/" + table,
                                params=params, json=data,
                                headers={**headers, **(extra_headers or {})}, timeout=15)
    response.raise_for_status()
    return response

try:
    sources = api("GET", "external_price_sources", {"select": "id,name,engine,database,schema_name,table_name", "order": "name.asc"}).json()
except requests.RequestException as exc:
    st.error("No se pudieron leer las fuentes externas. " + str(exc))
    st.stop()
choices = {"local": "Archivo local / Supabase"}
choices.update({s["id"]: f"{s['name']} — {s['database']} ({s['schema_name']}.{s['table_name']})" for s in sources})
selected = st.selectbox("Base de datos que deseas consultar", list(choices), format_func=lambda x: choices[x])
search = st.text_input("Buscar por código o descripción", placeholder="Escribe el código o nombre")
page_size = st.selectbox("Productos por página", [25, 50, 100], index=0)
query_key = (selected, search.strip(), page_size)
if st.session_state.get("catalog_query_key") != query_key:
    st.session_state.catalog_query_key = query_key
    st.session_state.catalog_page = 1
    st.session_state.pop("catalog_job", None)
    st.session_state.pop("catalog_result", None)

page = st.session_state.get("catalog_page", 1)
if selected == "local":
    # Para el catálogo local se usa paginación del servidor, no una descarga masiva.
    filt = {}
    if search.strip():
        safe = "".join(c for c in search.strip() if c.isalnum() or c in " -").strip()
        filt["or"] = f"(barcode.ilike.*{safe}*,name.ilike.*{safe}*)"
    try:
        r = api("GET", "products", {**filt, "select": "barcode,name,price", "order": "barcode.asc",
                                   "limit": str(page_size), "offset": str((page - 1) * page_size)},
                extra_headers={"Prefer": "count=exact"})
        products = r.json()
        content_range = r.headers.get("Content-Range", "")
        total = int(content_range.rsplit("/", 1)[1]) if "/" in content_range and content_range.rsplit("/",1)[1].isdigit() else None
        result = {"products": products, "total": total}
    except requests.RequestException as exc:
        st.error("No se pudo consultar el catálogo local: " + str(exc))
        st.stop()
else:
    # El conector Windows debe incluir _execute_catalog y la tabla external_catalog_jobs.
    if st.session_state.get("catalog_job_page") != (selected, page, search, page_size):
        st.session_state.pop("catalog_job", None)
        st.session_state.pop("catalog_result", None)
        st.session_state.catalog_job_page = (selected, page, search, page_size)
    if not st.session_state.get("catalog_job"):
        try:
            created = api("POST", "external_catalog_jobs", data={
                "configuration_id": selected, "page_number": page, "page_size": page_size,
                "search_term": search.strip(), "status": "pending",
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=3)).isoformat(),
            }).json()
            st.session_state.catalog_job = created[0]["id"]
        except requests.RequestException:
            st.error("Falta habilitar el listado externo. Ejecuta supabase_listado_productos.sql y actualiza el conector Windows.")
            st.stop()
    @st.fragment(run_every="2s")
    def show_external_result():
        try:
            jobs = api("GET", "external_catalog_jobs", {"id": "eq." + st.session_state.catalog_job,
                                                          "select": "status,result,error_message"}).json()
        except requests.RequestException:
            st.warning("Esperando conexión con Supabase…")
            return
        if not jobs:
            st.error("No se encontró la solicitud de listado.")
            return
        job = jobs[0]
        if job["status"] == "done":
            show_table(job.get("result") or {"products": [], "total": 0})
        elif job["status"] == "error":
            st.error("Error del conector: " + str(job.get("error_message") or "desconocido"))
        else:
            st.info("Buscando productos…")
    def show_table(data):
        products = data.get("products") or []
        total = data.get("total")
        st.write(f"**{total:,} productos**" if isinstance(total, int) else "**Listado de productos**")
        if products:
            st.dataframe([{"Código": p.get("barcode"), "Descripción": p.get("name"),
                           "Precio": p.get("price")} for p in products],
                         hide_index=True, use_container_width=True)
        else:
            st.info("No se encontraron productos.")
        pager(total, len(products))
    def pager(total, count):
        max_page = max(1, math.ceil(total / page_size)) if isinstance(total, int) else None
        left, middle, right = st.columns([1, 2, 1])
        with left:
            if st.button("← Anterior", disabled=page <= 1, key="prev_external"):
                st.session_state.catalog_page = page - 1
                st.rerun(scope="app")
        with middle:
            st.write(f"Página {page}" + (f" de {max_page}" if max_page else ""))
        with right:
            if st.button("Siguiente →", disabled=(page >= max_page if max_page else count < page_size), key="next_external"):
                st.session_state.catalog_page = page + 1
                st.rerun(scope="app")
    show_external_result()
    st.stop()

products = result["products"]
total = result["total"]
st.write(f"**{total:,} productos**" if isinstance(total, int) else "**Listado de productos**")
if products:
    st.dataframe([{"Código": p.get("barcode"), "Descripción": p.get("name"),
                   "Precio": p.get("price")} for p in products],
                 hide_index=True, use_container_width=True)
else:
    st.info("No se encontraron productos.")
max_page = max(1, math.ceil(total / page_size)) if isinstance(total, int) else None
left, middle, right = st.columns([1, 2, 1])
with left:
    if st.button("← Anterior", disabled=page <= 1, key="prev_local"):
        st.session_state.catalog_page = page - 1
        st.rerun()
with middle:
    st.write(f"Página {page}" + (f" de {max_page}" if max_page else ""))
with right:
    if st.button("Siguiente →", disabled=(page >= max_page if max_page else len(products) < page_size), key="next_local"):
        st.session_state.catalog_page = page + 1
        st.rerun()
