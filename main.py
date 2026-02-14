import streamlit as st
import pandas as pd
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
from datetime import datetime
import json
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURACIÓN ---
SHEET_ID = "19BvTkyD2ddrMsX1ghYGgnnq-BAfYJ_7qkNGqAsJel-M"
URL_DATA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Hoja1"

st.set_page_config(page_title="Simons GG v04", layout="wide")

# --- RECUPERACIÓN DE DATOS ---
if 'saldo' not in st.session_state:
    st.session_state.saldo = 33362112.69
    st.session_state.pos = {}

# --- DASHBOARD ---
st.title("🦅 Simons GG v04 🤑")
valor_cartera = sum(float(i.get('m', 0)) for i in st.session_state.pos.values())
patrimonio_total = st.session_state.saldo + valor_cartera

c1, c2, c3 = st.columns(3)
var = ((patrimonio_total / 30000000.0) - 1) * 100
c1.metric("Patrimonio Total", f"AR$ {patrimonio_total:,.2f}", f"{var:+.4f}%")
c2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Ticket 8%", f"AR$ {(patrimonio_total*0.08):,.2f}")

# --- BOTÓN DE BACKUP (Indispensable ahora que Google borró el proyecto) ---
with st.expander("💾 Guardar Cambios en Excel"):
    st.write("Copia esta línea y pégala al final de tu Google Sheet:")
    linea_excel = f"{st.session_state.saldo}, '{json.dumps(st.session_state.pos)}', {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    st.code(linea_excel, language="text")

# --- MONITOR DE MERCADO COMPLETO ---
st.subheader("📊 Monitor de Arbitraje y Clima HMM")

cfg = {
    'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 
    'GGAL':10, 'YPF':1, 'BMA':10, 'CEPU':10, 'GOOGL':58, 
    'AMZN':144, 'META':24, 'VIST':3, 'PAM':25
}

@st.cache_data(ttl=600)
def get_full_data():
    filas, ccls = [], []
    for t, r in cfg.items():
        try:
            ba = "YPFD.BA" if t=='YPF' else ("PAMP.BA" if t=='PAM' else f"{t}.BA")
            # Datos históricos para Clima
            u_hist = yf.download(t, period="3mo", interval="1d", progress=False)
            # Datos actuales
            a = yf.download(ba, period="1d", interval="1m", progress=False)
            
            pu = float(u_hist.Close.iloc[-1])
            pa = float(a.Close.iloc[-1])
            ccl = (pa * r) / pu
            ccls.append(ccl)
            
            # Modelo HMM para Clima
            returns = np.diff(np.log(u_hist.Close.values.flatten().reshape(-1, 1)), axis=0)
            model = GaussianHMM(n_components=3, random_state=42).fit(returns)
            clima = "🟢" if model.predict(returns)[-1] == 0 else "🔴"
            
            filas.append({"Activo": t, "USD": round(pu,2), "ARS": round(pa,2), "CCL": round(ccl,2), "Clima": clima})
        except: continue
    
    df = pd.DataFrame(filas)
    if not df.empty:
        avg_ccl = np.median(ccls)
        def set_signal(row):
            if row['CCL'] < avg_ccl * 0.995 and row['Clima'] == "🟢": return "🟢 COMPRA"
            if row['CCL'] > avg_ccl * 1.005: return "🔴 VENTA"
            return "⚖️ MANTENER"
        df['Señal'] = df.apply(set_signal, axis=1)
    return df

df_final = get_full_data()
st.dataframe(df_final, use_container_width=True, hide_index=True)

st_autorefresh(interval=600000, key="v4_ref")
