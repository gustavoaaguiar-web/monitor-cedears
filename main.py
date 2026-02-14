import streamlit as st
import pandas as pd
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
from datetime import datetime
import json

# --- CONFIGURACIÓN DIRECTA (SIN GOOGLE CLOUD) ---
SHEET_ID = "19BvTkyD2ddrMsX1ghYGgnnq-BAfYJ_7qkNGqAsJel-M"
# URL para leer el Excel como si fuera una web
URL_DATA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Hoja1"

st.set_page_config(page_title="Simons GG v03", layout="wide")

# --- INICIALIZACIÓN DE SALDO ---
if 'saldo' not in st.session_state:
    try:
        # Intentamos leer la última fila del Excel directamente
        df_sheet = pd.read_csv(URL_DATA)
        if not df_sheet.empty:
            u = df_sheet.iloc[-1]
            st.session_state.saldo = float(u['saldo'])
            # Limpiamos el texto de posiciones para que Python lo entienda
            pos_text = str(u['posiciones']).replace("'", '"')
            st.session_state.pos = json.loads(pos_text)
        else:
            st.session_state.saldo = 33362112.69
            st.session_state.pos = {}
    except:
        # Si falla la conexión, cargamos tus datos reales por defecto
        st.session_state.saldo = 33362112.69
        st.session_state.pos = {}

# --- INTERFAZ ---
st.title("🦅 Simons GG v03 🤑")
st.caption("Conexión Directa (Independiente de Google Cloud)")

valor_cartera = sum(float(i.get('m', 0)) for i in st.session_state.pos.values())
patrimonio_total = st.session_state.saldo + valor_cartera

c1, c2, c3 = st.columns(3)
var = ((patrimonio_total / 30000000.0) - 1) * 100
c1.metric("Patrimonio Total", f"AR$ {patrimonio_total:,.2f}", f"{var:+.4f}%")
c2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Ticket 8%", f"AR$ {(patrimonio_total*0.08):,.2f}")

# --- MONITOR DE MERCADO (SIMPLIFICADO PARA PROBAR) ---
st.subheader("📊 Monitor de Arbitraje")

cfg = {'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 'GGAL':10, 'YPF':1}

@st.cache_data(ttl=300)
def get_data():
    filas = []
    for t, r in cfg.items():
        try:
            ba = "YPFD.BA" if t=='YPF' else f"{t}.BA"
            u = yf.download(t, period="1d", interval="1m", progress=False)
            a = yf.download(ba, period="1d", interval="1m", progress=False)
            pu, pa = float(u.Close.iloc[-1]), float(a.Close.iloc[-1])
            ccl = (pa * r) / pu
            filas.append({"Activo": t, "USD": pu, "ARS": pa, "CCL": ccl})
        except: continue
    return pd.DataFrame(filas)

df_mercado = get_data()
if not df_mercado.empty:
    st.dataframe(df_mercado, use_container_width=True, hide_index=True)
else:
    st.warning("Esperando datos de Yahoo Finance...")

st.info("💡 El lunes a las 11:00 AM el bot retomará la operatoria automática.")
            
