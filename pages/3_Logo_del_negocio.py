import html
from io import BytesIO
from PIL import Image, ImageOps
from datetime import datetime, timedelta, timezone
import time
from pathlib import Path

import pandas as pd
import requests
import streamlit as st



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
