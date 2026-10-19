import html
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


CSS = """
<style>
.stApp { background: #f4f7fc; }
.block-container {
    max-width: 950px;
    padding: 1rem 1rem 2rem;
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
    font-size: clamp(18px, 3vw, 28px) !important;
    min-height: 56px;
    border-radius: 14px;
    border: 2px solid #d5e1f1;
    background: white;
}
