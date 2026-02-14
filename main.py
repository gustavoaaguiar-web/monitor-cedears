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

st.set_page_config(page_title="Simons GG v05", layout="wide")

# --- CARGA SEGURA DE DATOS ---
if 'saldo' not in st.session_state:
    try:
        df_sheet = pd.read_csv(URL_DATA)
        if not df_sheet.empty:
            u = df_sheet.iloc[-1]
            st.session_state.saldo = float(u['saldo'])
            st.session_state.pos = json.loads(str(u['posiciones']).replace("'", '"'))
            st.session_state.hist = json.loads(str(u['historial']).replace("'", '"'))
        else:
            raise ValueError("Excel vacío")
    except:
        # DATOS DE RESPALDO (Si el Excel falla, usa estos)
        st.session_state.saldo = 33362112.69
        st.session_state.pos = {}
        st.session_state.hist = [{"fecha": "2026-02-14", "t": 33362112.69}]

# --- INTERFAZ ---
st.title("🦅 Simons GG v05 🤑")

patrimonio_total = st.session_state.saldo + sum(float(i.get('m', 0)) for i in st.session_state.pos.values())

c1, c2, c3 = st.columns(3)
var = ((patrimonio_total / 30000000.0) - 1) * 100
c1.metric("Patrimonio Total", f"AR$ {patrimonio_total:,.2f}", f"{var:+.4f}%")
c2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Ticket 8%", f"AR$ {(patrimonio_total*0.08):,.2f}")

# --- SECCIÓN DE GUARDADO ---
with st.expander("💾 GENERAR FILA PARA EXCEL"):
    st.write("Copia esta línea y pégala en tu Google Sheet (Columna A):")
    nueva_fila = f"{st.session_state.saldo}, '{json.dumps(st.session_state.pos)}', '{json.dumps(st.session_state.hist)}', {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    st.code(nueva_fila, language="text")

# --- MONITOR DE MERCADO (TODOS LOS ACTIVOS) ---
st.subheader("📊 Monitor de Arbitraje")

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
            u_h = yf.download(t, period="3mo", interval="1d", progress=False)
            a = yf.download(ba, period="1d", interval="1m", progress=False)
            pu, pa = float(u_h.Close.iloc[-1]), float(a.Close.iloc[-1])
            ccl = (pa * r) / pu
            ccls.append(ccl)
            
            re = np.diff(np.log(u_h.Close.values.flatten().reshape(-1, 1)), axis=0)
            cl = "🟢" if GaussianHMM(n_components=3, random_state=42).fit(re).predict(re)[-1] == 0 else "🔴"
            filas.append({"Activo": t, "USD": pu, "ARS": pa, "CCL": ccl, "Clima": cl})
        except: continue
    
    df = pd.DataFrame(filas)
    if not df.empty:
        avg = np.median(ccls)
        df['Señal'] = df.apply(lambda x: "🟢 COMPRA" if x['CCL'] < avg*0.995 and x['Clima']=="🟢" else ("🔴 VENTA" if x['CCL'] > avg*1.005 else "⚖️ MANTENER"), axis=1)
    return df

st.dataframe(get_full_data(), use_container_width=True, hide_index=True)

st_autorefresh(interval=600000, key="v5_ref")
