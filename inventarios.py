import requests
import pandas as pd
import streamlit as st

def api(method, table, params=None, data=None, admin=True, prefer=None):
    url=str(st.secrets['SUPABASE_URL']).rstrip('/')
    key=str(st.secrets['SUPABASE_SERVICE_ROLE_KEY' if admin else 'SUPABASE_ANON_KEY'])
    headers={'apikey':key,'Authorization':'Bearer '+key,'Content-Type':'application/json'}
    if prefer: headers['Prefer']=prefer
    r=requests.request(method,f'{url}/rest/v1/{table}',params=params,json=data,headers=headers,timeout=50)
    if not r.ok: raise RuntimeError(f'Supabase {r.status_code}: {r.text[:500]}')
    return r.json() if r.content else []

def all_inventories():
    return api('GET','price_inventories',{'select':'id,name,is_active','order':'name.asc'})

def active_catalog():
    active=api('GET','price_inventories',{'select':'id','is_active':'eq.true','limit':1},admin=False)
    if not active:return pd.DataFrame(columns=['barcode','name','price'])
    rows=[];offset=0
    while True:
        batch=api('GET','price_inventory_items',{'select':'barcode,name,price','inventory_id':f"eq.{active[0]['id']}",'limit':500,'offset':offset},admin=False)
        rows+=batch
        if len(batch)<500:break
        offset+=500
    return pd.DataFrame(rows,columns=['barcode','name','price'])
