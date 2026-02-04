import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os, smtplib
from datetime import datetime
from email.message import EmailMessage

# --- CONFIGURACIÓN ---
DB = "simons_gg_v01.json"
CAPITAL_INICIAL = 30000000.0
GANANCIA_PREVIA = 0.05 
SALDO_ACTUAL = CAPITAL_INICIAL * (1 + GANANCIA_PREVIA)

# Configuración de Ratios y Tickers Corregidos
cfg = {
    'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 
    'GGAL':10, 'YPF':1, 'BMA':10, 'CEPU':10, 'VIST':3,
    'GOOGL':58, 'AMZN':144, 'META':24, 'PAMP':25 
}

def load():
    if os.path.exists(DB):
        try:
            with open(DB, "r") as f: return json.load(f)
        except: pass
    return {"s": SALDO_ACTUAL, "p": {}, "h": []}

st.set_page_config(page_title="Simons GG v01.4", layout="wide")

if 'init' not in st.session_state:
    d = load()
    st.session_state.update({'saldo': d["s"], 'pos': d["p"], 'init': True})

# --- BENCHMARKS ---
@st.cache_data(ttl=3600)
def get_benchmarks():
    indices = {"S&P 500": "SPY", "Merval": "^MERV"}
    res = {}
    for name, ticker in indices.items():
        try:
            h = yf.download(ticker, period="10d", interval="1d", progress=False)
            if not h.empty:
                v = ((h.Close.iloc[-1] / h.Close.iloc[0]) - 1) * 100
                res[name] = float(v)
        except: continue
    return res

bench = get_benchmarks()

# --- DATA FETCHING ---
def get_market_data():
    filas, ccls = [], []
    for t, r in cfg.items():
        try:
            t_usa = t if t != 'PAMP' else 'PAM'
            t_ars = f"{t}.BA" if t != 'YPF' else 'YPFD.BA'
            u = yf.download(t_usa, period="2d", interval="1m", progress=False)
            a = yf.download(t_ars, period="2d", interval="1m", progress=False)
            if u.empty or a.empty: continue
            pu, pa = float(u.Close.iloc[-1]), float(a.Close.iloc[-1])
            ccl = (pa * r) / pu
            ccls.append(ccl)
            
            h = yf.download(t_usa, period="4mo", interval="1d", progress=False)
            cl = "⚪"
            if len(h) > 20:
                re = np.diff(np.log(h.Close.values.flatten().reshape(-1, 1)), axis=0)
                cl = "🟢" if GaussianHMM(n_components=3).fit(re).predict(re)[-1] == 0 else "🔴"
            filas.append({"Activo": t, "USD": pu, "ARS": pa, "CCL": ccl, "Clima": cl})
        except: continue
    return pd.DataFrame(filas), np.median(ccls) if ccls else 0

st.title("🦅 Simons GG v01.4")
df, avg_ccl = get_market_data()

# --- LÓGICA DE PATRIMONIO ---
val_cartera = 0
if not df.empty:
    for t, p in st.session_state.pos.items():
        if t in df['Activo'].values:
            actual = df.loc[df['Activo'] == t, 'ARS'].values[0]
            # Filtro de cordura para Tesla/Errores de Data
            ratio = actual / p['pc']
            val_cartera += p['m'] * (ratio if ratio < 2.0 else 1.0)
        else: val_cartera += p['m']

patrimonio = st.session_state.saldo + val_cartera
rend_bot = ((patrimonio / CAPITAL_INICIAL) - 1) * 100

# --- DASHBOARD SUPERIOR ---
c1, c2, c3 = st.columns(3)
c1.metric("Patrimonio Total", f"AR$ {patrimonio:,.2f}", f"{rend_bot:+.2f}%")
c2.metric("Efectivo en Cuenta", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("CCL Promedio", f"AR$ {avg_ccl:,.2f}")

st.markdown("---")
st.subheader("📊 Comparativa vs Mercado (7 Días)")
b1, b2, b3 = st.columns(3)
b1.metric("Simons GG (Bot)", f"{rend_bot:+.2f}%")
if "S&P 500" in bench:
    b2.metric("S&P 500 (SPY)", f"{bench['S&P 500']:+.2f}%", f"{rend_bot - bench['S&P 500']:+.2f}% vs Bot")
if "Merval" in bench:
    b3.metric("Merval Index", f"{bench['Merval']:+.2f}%", f"{rend_bot - bench['Merval']:+.2f}% vs Bot")

# --- SEÑALES COMPRA/VENTA ---
if not df.empty:
    def calc_signal(r):
        if r['CCL'] < avg_ccl * 0.995 and r['Clima'] != "🔴": return "🟢 COMPRA"
        if r['CCL'] > avg_ccl * 1.005: return "🔴 VENTA"
        return "⚖️ MANTENER"
    
    df['Señal'] = df.apply(calc_signal, axis=1)

    st.subheader("🏢 Cartera Activa")
    if st.session_state.pos:
        p_data = []
        for t, p in st.session_state.pos.items():
            if t in df['Activo'].values:
                pre = df.loc[df['Activo'] == t, 'ARS'].values[0]
                r_ind = ((pre / p['pc']) - 1) * 10
