import html
from io import BytesIO
from PIL import Image, ImageOps
from datetime import datetime, timedelta, timezone
import time
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

# Campo del lector controlado dentro de su propio componente (sin acceder al DOM de Streamlit).
SCANNER_DIR = Path(__file__).resolve().parent / "scanner_component"
SCANNER_DISPONIBLE = SCANNER_DIR.is_dir() and (SCANNER_DIR / "index.html").is_file()
scanner_component = (
    components.declare_component("lector_codigo_autofoco", path=str(SCANNER_DIR))
    if SCANNER_DISPONIBLE else None
)



SUPABASE_URL = str(st.secrets.get("SUPABASE_URL", "")).strip().rstrip("/")
SUPABASE_ANON_KEY = str(st.secrets.get("SUPABASE_ANON_KEY", "")).strip()

SUPABASE_SERVICE_ROLE_KEY = str(st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", "")).strip()

def admin_api(method, table, params=None, payload=None):
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Falta SUPABASE_SERVICE_ROLE_KEY en Secrets.")
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": "Bearer " + SUPABASE_SERVICE_ROLE_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    response = requests.request(
        method, f"{SUPABASE_URL}/rest/v1/{table}",
        params=params, json=payload, headers=headers, timeout=12,
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=4, show_spinner=False)
def active_source():
    settings = admin_api("GET", "price_source_settings",
                         params={"id": "eq.1", "select": "source_type"})
    if not settings:
        raise RuntimeError("Falta configurar el origen de datos.")
    mode = settings[0]["source_type"]
    if mode == "local":
        return mode, None
    if mode != "external":
        raise RuntimeError("Origen de datos desconocido.")
    sources = admin_api("GET", "external_price_sources",
                        params={"enabled": "eq.true", "select": "id,name", "limit": "2"})
    if len(sources) != 1:
        raise RuntimeError(
            "La fuente externa requiere exactamente una configuración habilitada. "
            "Configúrala en Fuentes de datos."
        )
    return mode, sources[0]["id"]


@st.cache_data(ttl=60, show_spinner=False)
def cargar_logo_negocio():
    """Lee el logo persistente desde Supabase Storage, sin hacerlo publico."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return None
    try:
        response = requests.get(
            f"{SUPABASE_URL}/storage/v1/object/logo-negocio/logo.png",
            headers={
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": "Bearer " + SUPABASE_SERVICE_ROLE_KEY,
            },
            timeout=8,
        )
        if response.status_code == 200 and response.headers.get("content-type", "").startswith("image/"):
            return response.content
    except requests.RequestException:
        pass
    return None


CSS = """
<style>
.stApp { background: #f4f7fc; }
.block-container {
    max-width: 100%;
    padding: .5rem .8rem 1rem;
}
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.main-header {
    background: linear-gradient(135deg, #0c2e59, #0759c9);
    border-radius: 20px;
    padding: clamp(12px, 3vw, 28px);
    text-align: center;
    color: white;
    margin-bottom: 12px;
}
.main-header h1 {
    color: white !important;
    font-size: clamp(20px, 4vw, 38px);
    margin: 0;
}
.main-header p {
    color: #dceaff;
    font-size: clamp(12px, 2vw, 17px);
    margin: 6px 0 0;
}
.scan-title {
    color: #102b50;
    text-align: center;
    font-weight: 850;
    font-size: clamp(18px, 3.5vw, 32px);
    margin: 10px 0;
}
div[data-testid="stTextInput"] input {
    text-align: center !important;
    font-size: clamp(16px, 2vw, 21px) !important;
    min-height: 44px;
    height: 44px;
    padding: 4px 12px;
    border-radius: 14px;
    border: 2px solid #d5e1f1;
    background: white;
}
.product-card {
    background: white;
    border: 1px solid #dce5f2;
    border-radius: 20px;
    padding: clamp(16px, 4vw, 36px);
    text-align: center;
    margin: 10px auto;
    box-shadow: 0 7px 25px rgba(20,50,90,.07);
}
/* Resultado ampliado para pantallas de verificadores de precios. */
.product-card.result-card {
    width: 100%;
    min-height: 76dvh;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: clamp(8px, 1.5vh, 18px);
    padding: clamp(16px, 3vw, 40px);
    margin: 0 auto;
}
.result-card .product-name {
    font-size: clamp(28px, 5.5vw, 66px);
    margin: 2px 0;
}
.result-card .product-code {
    font-size: clamp(17px, 2.5vw, 26px);
    margin: 0;
}
.result-card .product-price {
    font-size: clamp(54px, 10vw, 126px);
    margin: 0;
}
.result-card .product-label, .result-card .price-label {
    font-size: clamp(15px, 2vw, 23px);
}
@media (max-width: 600px) {
    .product-card.result-card { min-height: 72dvh; }
    .result-card .product-price { font-size: clamp(42px, 11vw, 78px); }
}
@media (orientation: landscape) and (max-height: 650px) {
    .product-card.result-card { min-height: 79dvh; padding: 10px 22px; gap: 6px; }
    .result-card .product-name { font-size: clamp(28px, 5vw, 58px); }
    .result-card .product-price { font-size: clamp(55px, 9vw, 110px); }
}
.product-label, .price-label {
    color: #64748b;
    font-weight: 800;
    letter-spacing: 1px;
    font-size: clamp(12px, 2vw, 17px);
}
.product-name {
    color: #102b50;
    font-size: clamp(22px, 4.5vw, 40px);
    font-weight: 850;
    overflow-wrap: anywhere;
    line-height: 1.2;
    margin: 12px 0;
}
.product-code {
    color: #64748b;
    font-size: clamp(14px, 2vw, 21px);
    overflow-wrap: anywhere;
    margin-bottom: 22px;
}
.product-price {
    color: #0757c3;
    font-size: clamp(40px, 8vw, 76px);
    font-weight: 900;
    line-height: 1.1;
    overflow-wrap: anywhere;
    margin-top: 8px;
}
@media (max-width: 600px) {
    .block-container { padding: .6rem .6rem 1rem; }
    .main-header { padding: 13px 10px; margin-bottom: 8px; }
    .main-header h1 { font-size: clamp(19px, 5.5vw, 27px); }
    .scan-title { margin: 6px 0; font-size: clamp(17px, 5vw, 24px); }
    div[data-testid="stTextInput"] input { min-height: 48px; }
    .product-card { padding: 18px 12px; }
}
@media (orientation: landscape) and (max-height: 650px) {
    .block-container { padding-top: .25rem; padding-bottom: .4rem; }
    .main-header { padding: 8px 12px; margin-bottom: 5px; }
    .main-header h1 { font-size: clamp(18px, 3vw, 27px); }
    .main-header p { margin-top: 2px; font-size: 12px; }
    .scan-title { margin: 4px 0; font-size: clamp(17px, 3vw, 24px); }
    div[data-testid="stTextInput"] input { min-height: 44px; }
    .product-card { padding: 12px; margin: 4px auto; }
    .product-name { margin: 6px 0; }
    .product-code { margin-bottom: 8px; }
}

.search-card { min-height: 255px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px; }
.search-card .search-label { color: #64748b; font-weight: 800; letter-spacing: 1px; font-size: 14px; }
.search-card .search-text { color: #102b50; font-weight: 750; font-size: clamp(18px, 3vw, 24px); }
.search-visual { width: min(300px, 90%); height: 105px; overflow: hidden; }
.search-lens { animation: scan-barcode 2.1s ease-in-out infinite; transform-origin: center; }
@keyframes scan-barcode { 0%, 100% { transform: translateX(0); } 50% { transform: translateX(180px); } }
@media (prefers-reduced-motion: reduce) { .search-lens { animation: none; } }
.not-found-name { color: #102b50; font-size: clamp(23px, 4.5vw, 40px); font-weight: 850; line-height: 1.2; margin: 16px 0; }
.business-logo-label {
    text-align: center;
    color: #64748b;
    font-weight: 750;
    letter-spacing: 1px;
    margin: 22px 0 8px;
}

/* Codigo de barras decorativo con barrido continuo, sin recursos externos. */
.animated-barcode-card {
    width: min(310px, 75vw); margin: 8px auto 20px; padding: 16px 18px 12px;
    background: #fff; border-radius: 12px; text-align: center;
    box-shadow: 0 2px 10px rgba(20,50,90,.04);
}
.animated-bars {
    position: relative; height: 105px; overflow: hidden;
    background: repeating-linear-gradient(90deg,
        #102b50 0px, #102b50 2px, #fff 2px, #fff 5px,
        #102b50 5px, #102b50 9px, #fff 9px, #fff 12px,
        #102b50 12px, #102b50 13px, #fff 13px, #fff 17px,
        #102b50 17px, #102b50 22px, #fff 22px, #fff 26px);
}
.animated-scan-line {
    position: absolute; top: 0; bottom: 0; left: 0; width: 4px;
    background: #ff9d20; box-shadow: 0 0 9px 3px rgba(255,157,32,.7);
    animation: barcode-sweep 2.4s ease-in-out infinite alternate;
}
@keyframes barcode-sweep { from { left: 0; } to { left: calc(100% - 4px); } }
.animated-barcode-caption { color: #102b50; margin-top: 10px; font-size: 16px; }
@media (prefers-reduced-motion: reduce) { .animated-scan-line { animation: none; left: 50%; } }
@media (max-width: 600px) { .animated-barcode-card { width: min(260px, 76vw); } }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data(ttl=90, show_spinner=False)
def catalog():
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("Falta configurar Supabase en Streamlit Secrets.")

    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    }
    rows = []
    page_size = 500
    offset = 0

    while True:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/products",
            params={
                "select": "barcode,name,price",
                "order": "barcode.asc",
                "limit": page_size,
                "offset": offset,
            },
            headers=headers,
            timeout=25,
        )
        response.raise_for_status()
        batch = response.json()
        if not isinstance(batch, list):
            raise ValueError("Respuesta inesperada de Supabase.")
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    return pd.DataFrame(rows, columns=["barcode", "name", "price"])


for key, default in (
    ("search_input", ""),
    ("last_searched_barcode", ""),
    ("current_product", None),
    ("result_time", None),
    ("not_found", False),
    ("external_job", None),
    ("external_started", None),
    ("consult_error", None),
    ("source_snapshot", None),
):
    if key not in st.session_state:
        st.session_state[key] = default


def buscar_producto():
    query = str(st.session_state.get("search_input", "")).strip()
    if not query:
        return
    st.session_state.last_searched_barcode = query
    st.session_state.current_product = None
    st.session_state.not_found = False
    st.session_state.consult_error = None
    st.session_state.external_job = None
    st.session_state.result_time = None
    try:
        mode, source_id = active_source()
        if mode == "local":
            df = catalog()
            hits = df[df["barcode"].astype(str).str.strip() == query].head(1)
            if hits.empty:
                st.session_state.not_found = True
            else:
                st.session_state.current_product = hits.iloc[0].to_dict()
            st.session_state.result_time = time.monotonic()
        else:
            rows = admin_api("POST", "external_price_jobs", payload={
                "configuration_id": source_id,
                "barcode": query,
                "status": "pending",
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat(),
            })
            if not rows or not rows[0].get("id"):
                raise RuntimeError("No se pudo registrar la consulta externa")
            st.session_state.external_job = rows[0]["id"]
            st.session_state.external_started = time.monotonic()
    except Exception as exc:
        st.session_state.consult_error = (
            "No se pudo consultar la fuente seleccionada. "
            "Revisa la configuración y el conector Windows."
        )
        st.session_state.result_time = time.monotonic()


def check_external_result():
    jid = st.session_state.external_job
    if not jid:
        return
    if time.monotonic() - st.session_state.external_started > 25:
        st.session_state.external_job = None
        st.session_state.consult_error = (
            "La base externa no respondió a tiempo. No se consultó la base local."
        )
        st.session_state.result_time = time.monotonic()
        return
    try:
        rows = admin_api("GET", "external_price_jobs",
                         params={"id": "eq." + jid, "select": "status,result,error_message"})
        if not rows:
            raise RuntimeError("La solicitud externa no existe.")
        job = rows[0]
        if job["status"] == "done":
            result = job.get("result")
            if result:
                st.session_state.current_product = {
                    "barcode": result.get("barcode") or st.session_state.get("last_searched_barcode", ""),
                    "name": result.get("name", ""),
                    "price": result.get("price", 0),
                }
            else:
                st.session_state.not_found = True
            st.session_state.external_job = None
            st.session_state.result_time = time.monotonic()
        elif job["status"] == "error":
            st.session_state.external_job = None
            st.session_state.consult_error = (
                "No se pudo consultar SQL Server. Revisa el conector y la conexión externa."
            )
            st.session_state.result_time = time.monotonic()
    except (requests.RequestException, RuntimeError) as exc:
        st.session_state.external_job = None
        st.session_state.consult_error = "No se pudo obtener la respuesta de la base externa."
        st.session_state.result_time = time.monotonic()


@st.fragment(run_every=0.25)
def verificador():
    # Evitar mostrar resultados de una fuente distinta si el administrador la cambia.
    try:
        mode, source_id = active_source()
        snapshot = (mode, source_id)
        if st.session_state.source_snapshot != snapshot:
            st.session_state.source_snapshot = snapshot
            st.session_state.current_product = None
            st.session_state.not_found = False
            st.session_state.external_job = None
            st.session_state.result_time = None
            st.session_state.consult_error = None
            st.session_state.last_searched_barcode = ""
    except Exception:
        st.error("No se pudo leer la fuente activa. Revisa Configuración.")
        return

    if mode == "external":
        check_external_result()
    started = st.session_state.result_time

    # Los códigos inexistentes vuelven antes al lector; los productos encontrados
    # conservan el tiempo habitual para leer el precio.
    display_seconds = 3 if st.session_state.not_found else 10
    if started is not None and time.monotonic() - started >= display_seconds:
        st.session_state.current_product = None
        st.session_state.not_found = False
        st.session_state.consult_error = None
        st.session_state.result_time = None
        # El widget puede no existir cuando se muestra un resultado.
        # Streamlit limpia automaticamente su estado al ocultarlo.

    product = st.session_state.current_product

    if product is not None:
        name = html.escape(str(product["name"]))
        barcode = html.escape(str(product["barcode"]))
        price = float(product["price"])

        st.markdown(
            '<div class="product-card result-card">'
            '<div class="product-label">PRODUCTO</div>'
            f'<div class="product-name">{name}</div>'
            f'<div class="product-code">Código: {barcode}</div>'
            '<div class="price-label">PRECIO DE VENTA</div>'
            f'<div class="product-price">RD$ {price:,.2f}</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    elif st.session_state.consult_error:
        st.error(st.session_state.consult_error)
    elif st.session_state.external_job:
        # Solo se muestra una animación amigable; no exponer detalles técnicos.
        st.markdown(
            '<div class="product-card search-card">'
            '<div class="search-label">VERIFICANDO PRECIO</div>'
            '<svg class="search-visual" viewBox="0 0 300 105" role="img" '
            'aria-label="Lupa buscando un código de barras">'
            '<g fill="#64748b">'
            + ''.join(
                f'<rect x="{15 + i * 9}" y="22" width="{4 if i % 3 == 0 else 2}" '
                f'height="{55 if i % 4 == 0 else 45}" />' for i in range(27)
            )
            + '</g><g class="search-lens">'
            '<circle cx="36" cy="42" r="23" fill="#e8f1ff" fill-opacity="0.9" '
            'stroke="#0759c9" stroke-width="5"/>'
            '<path d="M53 59 L78 84" stroke="#0759c9" stroke-width="9" '
            'stroke-linecap="round"/></g></svg>'
            '<div class="search-text">Buscando producto...</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    elif st.session_state.not_found:
        barcode = html.escape(str(st.session_state.get("last_searched_barcode", "")))
        st.markdown(
            '<div class="product-card">'
            '<div class="product-label">RESULTADO DE LA CONSULTA</div>'
            '<div class="not-found-name">PRODUCTO NO ENCONTRADO</div>'
            f'<div class="product-code">Código: {barcode}</div>'
            '<div class="price-label">VERIFIQUE EL CÓDIGO DE BARRAS</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    else:
        st.markdown(
            '<div class="main-header">'
            '<h1>🏷️ CONSULTA DE PRECIOS</h1>'
            '<p>Consulta rápida de productos y precios</p>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Codigo de barras animado: solo decorativo, no altera la lectura real.
        st.markdown("""
        <div class="animated-barcode-card" aria-label="Escaner de codigos de barras animado">
          <div class="animated-bars"><div class="animated-scan-line"></div></div>
          <div class="animated-barcode-caption">PRECIO &nbsp;•&nbsp; RD$</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            '<div class="scan-title">ESCANEA TU CÓDIGO AQUÍ</div>',
            unsafe_allow_html=True,
        )

        lado_izquierdo, campo_central, lado_derecho = st.columns([1, 2, 1])
        with campo_central:
            if scanner_component is not None:
                lectura = scanner_component(key="lector_codigo_autofoco", default=None)
                if isinstance(lectura, dict):
                    identificador = str(lectura.get("id", ""))
                    codigo = str(lectura.get("codigo", "")).strip()
                    if codigo and identificador and identificador != st.session_state.get("ultimo_scan_componente"):
                        st.session_state.ultimo_scan_componente = identificador
                        st.session_state.search_input = codigo
                        buscar_producto()
                        st.rerun(scope="fragment")
            else:
                st.text_input(
                    "Código de barras", key="search_input",
                    on_change=buscar_producto,
                    label_visibility="collapsed",
                    placeholder="Escanea o escribe el código",
                )


        logo = cargar_logo_negocio()
        if logo:
            # Logo en la misma columna central y ancho que la imagen del codigo de barras.
            try:
                with Image.open(BytesIO(logo)) as original:
                    imagen = ImageOps.contain(original.convert("RGBA"), (180, 120))
                    lienzo = Image.new("RGBA", (180, 120), (255, 255, 255, 0))
                    lienzo.alpha_composite(
                        imagen,
                        ((180 - imagen.width) // 2, (120 - imagen.height) // 2),
                    )
                    izquierda, centro, derecha = st.columns([2, 1, 2])
                    with centro:
                        st.image(lienzo, use_container_width=True)
            except (OSError, ValueError):
                pass




try:
    verificador()
except Exception:
    st.error("No se pudo iniciar la consulta de precios. Revisa la conexión y la fuente seleccionada.")
