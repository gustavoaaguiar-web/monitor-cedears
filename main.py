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
# Tickers corregidos (PAMP y YPF con sus variantes)
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

st.set_page_config(page_title="Simons GG v01.6", layout="wide")

if 'init' not in st.session_state:
    d = load_db()
    st.session_state.update({'saldo': d["s"], 'pos': d["p"], 'init': True})

# --- BENCHMARKS BLINDADOS (Línea 95 Fix) ---
@st.cache_data(ttl=600)
def get_benchmarks():
    res = {"S&P 500": 0.0, "Merval": 0.0}
    indices = {"S&P 500": "SPY", "Merval": "^MERV"}
    for name, t in indices.items():
        try:
            h = yf.download(t, period="5d", interval="1d", progress=False)
            if not h.empty and len(h) > 1:
                val = ((h.Close.iloc[-1] / h.Close.iloc[0]) - 1) * 100
                res[name] = float(val)
        except: pass
    return res

# --- MERCADO Y CCL (Fix Pampa y Tesla) ---
def fetch_market():
    filas, ccls = [], []
    for t, r in cfg.items():
        try:
            t_usa = 'PAM' if t == 'PAMP' else t
            t_ars = 'YPFD.BA' if t == 'YPF' else f"{t}.BA"
            
            u = yf.download(t_usa, period="2d", progress=False)
            a = yf.download(t_ars, period="2d", progress=False)
            
            if u.empty or a.empty: continue
            
            p_u = float(u.Close.iloc[-1])
            p_a = float(a.Close.iloc[-1])
            
            # Validación de CCL coherente (> 500) para evitar el error de los $21.52
            ccl_i = (p_a * r) / p_u
            if ccl_i > 500:
                ccls.append(ccl_i)
            
            clima = "🟢" if p_u > u.Close.iloc[-2] else "🔴"
            filas.append({"Activo": t, "ARS": p_a, "CCL": ccl_i, "Clima": clima})
        except: continue
    
    df = pd.DataFrame(filas)
    avg = np.median(ccls) if len(ccls) > 0 else 0
    return df, avg

st.title("🦅 Simons GG v01.6")

with st.spinner('Sincronizando...'):
    df_mkt, avg_ccl = fetch_market()
    bench = get_benchmarks()

# --- PATRIMONIO ---
val_cartera = 0
for t, p in st.session_state.pos.items():
    if not df_mkt.empty and t in df_mkt['Activo'].values:
        actual = df_mkt.loc[df_mkt['Activo'] == t, 'ARS'].values[0]
        # Si el precio es ridículo (Tesla fix), usamos el precio de compra
        ratio = actual / p['pc']
        val_cartera += p['m'] * (ratio if 0.5 < ratio < 1.5 else 1.0)
    else: val_cartera += p['m']

patrimonio = st.session_state.saldo + val_cartera
rend_bot = ((patrimonio / CAPITAL_INICIAL) - 1) * 100

# --- UI: MÉTRICAS ---
c1, c2, c3 = st.columns(3)
c1.metric("Patrimonio Total", f"AR$ {patrimonio:,.0f}", f"{rend_bot:+.2f}%")
c2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("CCL Promedio", f"AR$ {avg_ccl:,.2f}")

st.markdown("---")
st.subheader("📊 Comparativa vs Mercado")
b1, b2, b3 = st.columns(3)
b1.metric("Bot", f"{rend_bot:+.2f}%")
# Fix de la línea 95: Aseguramos que siempre haya un número
sp_val = bench.get("S&P 500", 0.0)
mer_val = bench.get("Merval", 0.0)
b2.metric("S&P 500", f"{sp_val:+.2f}%")
b3.metric("Merval Index", f"{mer_val:+.2f}%")

# --- UI: TABLA DE SEÑALES ---
if not df_mkt.empty and avg_ccl > 0:
    def get_sig(row):
        if row['CCL'] < avg_ccl * 0.995: return "🟢 COMPRA"
        if row['CCL'] > avg_ccl * 1.005: return "🔴 VENTA"
        return "⚖️ MANTENER"

    df_mkt['Señal'] = df_mkt.apply(get_sig, axis=1)
    
    st.subheader("🏢 Monitor de Mercado y Pampa")
    st.dataframe(df_mkt[['Activo', 'ARS', 'CCL', 'Clima', 'Señal']], use_container_width=True, hide_index=True)

    if st.session_state.pos:
        st.subheader("💰 Cartera Actual")
        st.write(list(st.session_state.pos.keys()))

st.button('🔄 Actualizar Ahora')
st_autorefresh(interval=600000, key="v6_refresh")
