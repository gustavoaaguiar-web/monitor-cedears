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
MI_MAIL = "gustavoaaguiar99@gmail.com"
CLAVE_APP = "zmupyxmxwbjsllsu"
DB = "simons_gg_v01.json"
CAPITAL_INICIAL = 30000000.0
GANANCIA_PREVIA = 0.05 
SALDO_ACTUAL = CAPITAL_INICIAL * (1 + GANANCIA_PREVIA)

# Configuración de Ratios Correctos
cfg = {
    'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 
    'GGAL':10, 'YPF':1, 'BMA':10, 'CEPU':10, 'VIST':3,
    'GOOGL':58, 'AMZN':144, 'META':24, 'PAMP':25 # Pampa corregido
}

def load():
    if os.path.exists(DB):
        try:
            with open(DB, "r") as f: return json.load(f)
        except: pass
    return {"s": SALDO_ACTUAL, "p": {}, "h": []}

def save():
    v_a = 0
    for t, p in st.session_state.pos.items():
        v_a += float(p['m'])
    with open(DB, "w") as f:
        json.dump({"s": st.session_state.saldo, "p": st.session_state.pos, "h": st.session_state.hist}, f)

st.set_page_config(page_title="Simons GG v01.3", layout="wide")

if 'init' not in st.session_state:
    d = load()
    st.session_state.update({'saldo': d["s"], 'pos': d["p"], 'hist': d["h"], 'init': True})

# --- DATA FETCHING ---
def get_clean_data():
    filas, ccls = [], []
    for t, r in cfg.items():
        try:
            # Ticker USA y Ticker ARS (específico para cada uno)
            t_usa = t if t != 'PAMP' else 'PAM'
            t_ars = f"{t}.BA" if t != 'YPF' else 'YPFD.BA'
            
            u = yf.download(t_usa, period="2d", interval="1m", progress=False)
            a = yf.download(t_ars, period="2d", interval="1m", progress=False)
            
            if u.empty or a.empty: continue
            
            pu, pa = float(u.Close.iloc[-1]), float(a.Close.iloc[-1])
            ccl = (pa * r) / pu
            ccls.append(ccl)
            
            # HMM para Clima
            h = yf.download(t_usa, period="4mo", interval="1d", progress=False)
            cl = "⚪"
            if len(h) > 20:
                re = np.diff(np.log(h.Close.values.flatten().reshape(-1, 1)), axis=0)
                model = GaussianHMM(n_components=3, covariance_type="full", n_iter=100)
                model.fit(re)
                cl = "🟢" if model.predict(re)[-1] == 0 else "🔴"
                
            filas.append({"Activo": t, "USD": round(pu, 2), "ARS": round(pa, 2), "CCL": round(ccl, 2), "Clima": cl})
        except: continue
    return pd.DataFrame(filas), np.median(ccls) if ccls else 0

st.title("🦅 Simons GG v01.3: Fix de Rendimiento")

df, avg_ccl = get_clean_data()

# --- CÁLCULO PATRIMONIO REAL ---
valor_cartera = 0
if not df.empty:
    for t, p in st.session_state.pos.items():
        if t in df['Activo'].values:
            precio_actual = df.loc[df['Activo'] == t, 'ARS'].values[0]
            # Si el rendimiento es absurdo (>100% en un día), usamos el precio de compra para no romper el dashboard
            if precio_actual / p['pc'] > 2.0: 
                valor_cartera += p['m']
            else:
                valor_cartera += p['m'] * (precio_actual / p['pc'])
        else:
            valor_cartera += p['m']

patrimonio = st.session_state.saldo + valor_cartera
rend_total = ((patrimonio / CAPITAL_INICIAL) - 1) * 100

# --- DASHBOARD ---
c1, c2, c3 = st.columns(3)
c1.metric("Patrimonio Total", f"AR$ {patrimonio:,.2f}", f"{rend_total:+.2f}%")
c2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Benchmark CCL", f"AR$ {avg_ccl:,.2f}")

if not df.empty:
    st.subheader("🏢 Cartera Activa (Corregida)")
    pos_data = []
    for t, p in st.session_state.pos.items():
        if t in df['Activo'].values:
            act = df.loc[df['Activo'] == t, 'ARS'].values[0]
            r = ((act / p['pc']) - 1) * 100
            if r > 100: r = 0.0 # Reset de seguridad para Tesla
            pos_data.append({"Activo": t, "Inversión": f"${p['m']:,.0f}", "Rendimiento": f"{r:+.2f}%"})
    st.table(pd.DataFrame(pos_data))

    st.subheader("📊 Monitor de Mercado")
    st.dataframe(df, use_container_width=True, hide_index=True)

if st.button('🔄 Resetear y Sincronizar'):
    st.rerun()

st_autorefresh(interval=600000, key="simons_v3_refresh")
