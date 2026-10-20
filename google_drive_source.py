"""Lectura segura de Excel de Drive y Google Sheets mediante cuenta de servicio."""
import io
import json
import math
import re
from urllib.parse import urlparse, parse_qs
import pandas as pd
import requests
import streamlit as st

SCOPES = ["https://www.googleapis.com/auth/drive.readonly",
          "https://www.googleapis.com/auth/spreadsheets.readonly"]

def service_credentials():
    from google.oauth2 import service_account
    raw = st.secrets.get("GOOGLE_SERVICE_ACCOUNT", None)
    if raw is None:
        raise ValueError("Configura GOOGLE_SERVICE_ACCOUNT en Secrets.")
    info = json.loads(raw) if isinstance(raw, str) else dict(raw)
    return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

def token():
    from google.auth.transport.requests import Request
    cred = service_credentials()
    cred.refresh(Request())
    return cred.token

def file_id(value):
    value = str(value).strip()
    match = re.search(r"/(?:file/d|spreadsheets/d)/([a-zA-Z0-9_-]+)", value)
    if match: return match.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{20,}", value): return value
    parsed = urlparse(value)
    if parsed.hostname in ("drive.google.com", "docs.google.com"):
        ident = parse_qs(parsed.query).get("id", [""])[0]
        if re.fullmatch(r"[a-zA-Z0-9_-]{20,}", ident): return ident
    raise ValueError("Introduce un enlace válido de Google Drive/Sheets o el ID del archivo.")

def _get(url, params=None):
    response = requests.get(url, params=params,
                            headers={"Authorization": "Bearer " + token()}, timeout=45)
    response.raise_for_status()
    return response

@st.cache_data(ttl=300, show_spinner=False)
def read_source(kind, identifier, sheet_name):
    fid = file_id(identifier)
    if kind == "sheets":
        from urllib.parse import quote
        meta = _get(f"https://sheets.googleapis.com/v4/spreadsheets/{fid}",
                    {"fields":"sheets(properties(title))"}).json()
        titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
        name = sheet_name.strip() or (titles[0] if titles else "")
        if not name or name not in titles:
            raise ValueError("La pestaña indicada no existe en Google Sheets.")
        result = _get(f"https://sheets.googleapis.com/v4/spreadsheets/{fid}/values/"
                      + quote("'" + name.replace("'", "''") + "'!A1:ZZ", safe=""),
                      {"valueRenderOption":"FORMATTED_VALUE"}).json()
        values = result.get("values", [])
        if not values: raise ValueError("La hoja está vacía.")
        headers = [str(x).strip() for x in values[0]]
        if len(headers) != len(set(headers)) or not all(headers):
            raise ValueError("Los encabezados deben ser únicos y no estar vacíos.")
        return pd.DataFrame([list(r[:len(headers)])+[""]*max(0,len(headers)-len(r))
                             for r in values[1:]], columns=headers)
    if kind == "excel":
        response = _get(f"https://www.googleapis.com/drive/v3/files/{fid}",
                        {"alt":"media"})
        return pd.read_excel(io.BytesIO(response.content), sheet_name=sheet_name.strip() or 0,
                             dtype=str, engine="openpyxl").fillna("")
    raise ValueError("Tipo de archivo no reconocido.")

def normalize(df, code, description, price):
    if len({code, description, price}) != 3 or any(c not in df.columns for c in (code, description, price)):
        raise ValueError("Selecciona tres columnas diferentes.")
    result = []
    for _, row in df.iterrows():
        barcode = str(row[code]).strip()
        name = str(row[description]).strip()
        raw = str(row[price]).strip()
        if barcode.endswith(".0"): barcode = barcode[:-2]
        if not barcode or not name: continue
        try:
            # 1,250.50 y 1250,50
            number = raw.replace(" ", "")
            if "," in number and "." not in number:
                number = number.replace(",", ".")
            else:
                number = number.replace(",", "")
            amount = float(number)
        except (ValueError, TypeError):
            continue
        if not math.isfinite(amount) or amount < 0: continue
        result.append({"barcode":barcode, "name":name, "price":round(amount,2)})
    if not result: raise ValueError("No hay productos válidos en el archivo.")
    return pd.DataFrame(result).drop_duplicates("barcode",keep="last").reset_index(drop=True)

@st.cache_data(ttl=300, show_spinner=False)
def products(kind, identifier, sheet_name, code, description, price):
    return normalize(read_source(kind,identifier,sheet_name),code,description,price)

def cloud_config():
    url = str(st.secrets.get("SUPABASE_URL","")).rstrip("/")
    key = str(st.secrets.get("SUPABASE_SERVICE_ROLE_KEY",""))
    if not url or not key: raise ValueError("Faltan los Secrets de Supabase.")
    res = requests.get(url+"/rest/v1/cloud_price_sources",
                       params={"select":"*","id":"eq.1"},
                       headers={"apikey":key,"Authorization":"Bearer "+key},timeout=15)
    res.raise_for_status()
    rows = res.json()
    if not rows: raise ValueError("Configura primero la fuente de Google Drive.")
    return rows[0]
