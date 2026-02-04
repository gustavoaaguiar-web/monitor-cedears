import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURACIÓN PRO ---
st.set_page_config(page_title="Simons GG v12.5", layout="wide")
st.title("🦅 Simons GG - Arbitraje Pro")

# --- PERSISTENCIA DE SALDO ---
if 'saldo' not in st.session_state:
    st.session_state.saldo = 30000000.0  # Tus 30 Millones
if 'posiciones' not in st.session_state:
    st.session_state.posiciones = {}

# --- DICCIONARIO DE RATIOS ---
cfg = {
    'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 
    'GGAL':10, 'YPF':1, 'BMA':10, 'CEPU':10, 'VIST':3,
    'GOOGL':58, 'AMZN':144, 'META':24, 'PAMP':25 
}

# --- FUNCIÓN DE CARGA ULTRA-RÁPIDA ---
@st.cache_data(ttl=60)
def fetch_data():
    try:
        t_usa = list(cfg.keys())
        t_ars = [f"{t}.BA" if t != 'YPF' else 'YPFD.BA' for t in t_usa]
        
        # Descarga masiva (evita tildado)
        df_all = yf.download(t_usa + t_ars, period="2d", interval="5m", progress=False)['Close']
        
        res = []
        ccls = []
        for t in t_usa:
            t_ba = f"{t}.BA" if t != 'YPF' else 'YPFD.BA'
            if t in df_all.columns and t_ba in df_all.columns:
                p_u = df_all[t].iloc[-1]
                p_a = df_all[t_ba].iloc[-1]
                if not np.isnan(p_u) and not np.isnan(p_a):
                    ccl_i = (p_a * cfg[t]) / p_u
                    ccls.append(ccl_i)
                    res.append({"Activo": t, "USD": p_u, "ARS": p_a, "CCL": ccl_i})
        
        return pd.DataFrame(res), np.median(ccls) if ccls else 0
    except:
        return pd.DataFrame(), 0

# --- LÓGICA DE INTERFAZ ---
df, ccl_mediano = fetch_data()

if not df.empty:
    # Métricas
    c1, c2, c3 = st.columns(3)
    c1.metric("Patrimonio Liq.", f"${st.session_state.saldo:,.0f}")
    c2.metric("CCL Promedio", f"${ccl_mediano:,.2f}")
    c3.metric("Status", "EN VIVO ✅")

    # Señales
    def get_signal(row):
        if row['CCL'] < ccl_mediano * 0.995: return "🟢 COMPRA"
        if row['CCL'] > ccl_mediano * 1.005: return "🔴 VENTA"
        return "⚖️ MANTENER"

    df['Acción'] = df.apply(get_signal, axis=1)

    # Mostrar Monitor
    st.subheader("📊 Monitor de Arbitraje")
    st.dataframe(df.style.format({"USD": "{:.2f}", "ARS": "{:.2f}", "CCL": "{:.2f}"}), 
                 use_container_width=True, hide_index=True)
else:
    st.warning("Sincronizando con Yahoo Finance... Espera 10 segundos.")

# --- AUTO-REFRESH (Cada 2 minutos para no banear la IP) ---
st_autorefresh(interval=120000, key="refresh_cel")

if st.sidebar.button('Limpiar Todo'):
    st.cache_data.clear()
    st.rerun()
