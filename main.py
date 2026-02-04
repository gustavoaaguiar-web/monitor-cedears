import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os

# --- CONFIGURACIÓN ---
DB = "simons_gg_v01.json"
CAPITAL_INICIAL = 30000000.0
cfg = {
    'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 
    'GGAL':10, 'YPF':1, 'BMA':10, 'CEPU':10, 'VIST':3,
    'GOOGL':58, 'AMZN':144, 'META':24, 'PAMP':25 
}

def load_db():
    if os.path.exists(DB):
        try:
            with open(DB, "r") as f: return json.load(f)
        except: pass
    return {"s": CAPITAL_INICIAL * 1.05, "p": {}, "h": []}

st.set_page_config(page_title="Simons GG v01.5", layout="wide")

if 'init' not in st.session_state:
    d = load_db()
    st.session_state.update({'saldo': d["s"], 'pos': d["p"], 'init': True})

# --- BENCHMARKS (S&P y MERVAL) ---
@st.cache_data(ttl=600)
def get_benchmarks():
    res = {}
    for name, t in {"S&P 500": "SPY", "Merval": "^MERV"}.items():
        try:
            h = yf.download(t, period="5d", interval="1d", progress=False)
            if not h.empty:
                res[name] = ((h.Close.iloc[-1] / h.Close.iloc[0]) - 1) * 100
        except: res[name] = 0.0
    return res

# --- OBTENCIÓN DE DATOS DE MERCADO ---
def fetch_market():
    filas, ccls = [], []
    for t, r in cfg.items():
        try:
            t_usa = 'PAM' if t == 'PAMP' else t
            t_ars = 'YPFD.BA' if t == 'YPF' else f"{t}.BA"
            
            u = yf.download(t_usa, period="1d", progress=False)
            a = yf.download(t_ars, period="1d", progress=False)
            
            if u.empty or a.empty: continue
            
            p_u, p_a = float(u.Close.iloc[-1]), float(a.Close.iloc[-1])
            ccl_i = (p_a * r) / p_u
            ccls.append(ccl_i)
            
            # Lógica Clima (HMM simplificado para velocidad)
            clima = "🟢" if (p_u > u.Open.iloc[0]) else "🔴"
            filas.append({"Activo": t, "Precio ARS": p_a, "CCL": ccl_i, "Clima": clima})
        except: continue
    return pd.DataFrame(filas), np.median(ccls) if ccls else 0

st.title("🦅 Simons GG v01.5")

# Ejecutar descarga
with st.spinner('Actualizando mercado...'):
    df_mkt, avg_ccl = fetch_market()
    bench = get_benchmarks()

# --- CÁLCULO DE PATRIMONIO ---
val_cartera = 0
for t, p in st.session_state.pos.items():
    if not df_mkt.empty and t in df_mkt['Activo'].values:
        actual = df_mkt.loc[df_mkt['Activo'] == t, 'Precio ARS'].values[0]
        # Protección Tesla: si el salto es >100%, mantenemos precio de compra
        val_cartera += p['m'] * (actual/p['pc'] if actual/p['pc'] < 2.0 else 1.0)
    else: val_cartera += p['m']

patrimonio = st.session_state.saldo + val_cartera
rend_total = ((patrimonio / CAPITAL_INICIAL) - 1) * 100

# --- UI: MÉTRICAS PRINCIPALES ---
c1, c2, c3 = st.columns(3)
c1.metric("Patrimonio Total", f"AR$ {patrimonio:,.0f}", f"{rend_total:+.2f}%")
c2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.0f}")
c3.metric("CCL Promedio", f"AR$ {avg_ccl:,.2f}")

# --- UI: COMPARATIVA ---
st.write("### 📊 Rendimiento vs Mercado")
b1, b2, b3 = st.columns(3)
b1.metric("Bot", f"{rend_total:+.2f}%")
b2.metric("S&P 500", f"{bench.get('S&P 500', 0):+.2f}%")
b3.metric("Merval", f"{bench.get('Merval', 0):+.2f}%")

# --- UI: SEÑALES Y TABLA ---
if not df_mkt.empty:
    def get_sig(row):
        if row['CCL'] < avg_ccl * 0.993: return "🟢 COMPRA (Barato)"
        if row['CCL'] > avg_ccl * 1.007: return "🔴 VENTA (Caro)"
        return "⚖️ MANTENER"

    df_mkt['Sugerencia'] = df_mkt.apply(get_sig, axis=1)
    
    st.write("### 🏢 Monitor de Arbitraje y Señales")
    # Forzamos que la tabla se muestre explícitamente
    st.dataframe(
        df_mkt[['Activo', 'Precio ARS', 'CCL', 'Clima', 'Sugerencia']], 
        use_container_width=True, 
        hide_index=True
    )

    if st.session_state.pos:
        st.write("### 💰 Mi Cartera")
        # Mostrar solo los activos que posees
        st.json(st.session_state.pos)

if st.button('🔄 Forzar Actualización'):
    st.rerun()

st_autorefresh(interval=600000, key="v5refresh")
