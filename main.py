import streamlit as st
from streamlit_gsheets import GSheetsConnection
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, pytz, smtplib
from datetime import datetime

# --- CONFIGURACIÓN ---
CAPITAL_ORIGEN = 30000000.0
PATRIMONIO_HOY = 33362112.69 

# Intentamos sacar la URL de los secrets de forma segura
try:
    URL_SHEET = st.secrets["spreadsheet"]
except:
    st.error("⚠️ No se encontró la URL en los Secrets. Revisa el paso 1.")
    st.stop()

# --- CONEXIÓN GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_memoria():
    try:
        df = conn.read(spreadsheet=URL_SHEET, worksheet="Hoja1", ttl=0)
        if not df.empty:
            u = df.iloc[-1]
            return float(u['saldo']), json.loads(u['posiciones']), json.loads(u['historial'])
    except: pass
    return PATRIMONIO_HOY, {}, [{"fecha": datetime.now().strftime("%Y-%m-%d"), "t": PATRIMONIO_HOY}]

def guardar_memoria(s, p, h):
    try:
        nuevo = pd.DataFrame([{"saldo": s, "posiciones": json.dumps(p), "historial": json.dumps(h), "update": datetime.now().strftime("%Y-%m-%d %H:%M")}])
        conn.create(spreadsheet=URL_SHEET, worksheet="Hoja1", data=nuevo)
        st.success("✅ ¡Guardado en Google Sheets!")
    except Exception as e:
        st.error(f"❌ Error al guardar: {e}")

# --- INICIALIZACIÓN ---
st.set_page_config(page_title="Simons GG v02", layout="wide")
if 'init' not in st.session_state:
    s, p, h = cargar_memoria()
    st.session_state.update({'saldo': s, 'pos': p, 'hist': h, 'init': True})

# --- DASHBOARD ---
patrimonio_total = st.session_state.saldo + sum(float(i['m']) for i in st.session_state.pos.values())
st.title("🦅 Simons GG v02 🤑")

c1, c2, c3 = st.columns(3)
var = ((patrimonio_total / CAPITAL_ORIGEN) - 1) * 100
c1.metric("Patrimonio Total", f"AR$ {patrimonio_total:,.2f}", f"{var:+.4f}%")
c2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Ticket Operativo", f"AR$ {(patrimonio_total*0.08):,.2f}")

if st.button("💾 GUARDAR BACKUP"):
    guardar_memoria(st.session_state.saldo, st.session_state.pos, st.session_state.hist)

# --- MONITOR DE MERCADO ---
st.subheader("📊 Monitor de Arbitraje")

cfg = {'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 'GGAL':10, 'YPF':1, 'BMA':10, 'CEPU':10, 'GOOGL':58, 'AMZN':144, 'META':24, 'VIST':3, 'PAM':25}

@st.cache_data(ttl=300)
def get_data():
    filas, ccls = [], []
    for t, r in cfg.items():
        try:
            ba = "YPFD.BA" if t=='YPF' else ("PAMP.BA" if t=='PAM' else f"{t}.BA")
            u = yf.download(t, period="2d", interval="1m", progress=False)
            a = yf.download(ba, period="2d", interval="1m", progress=False)
            pu, pa = float(u.Close.iloc[-1]), float(a.Close.iloc[-1])
            ccl = (pa * r) / pu
            ccls.append(ccl)
            filas.append({"Activo": t, "USD": pu, "ARS": pa, "CCL": ccl})
        except: continue
    df = pd.DataFrame(filas)
    if not df.empty:
        avg = np.median(ccls)
        df['Señal'] = df.apply(lambda x: "🟢 COMPRA" if x['CCL'] < avg*0.995 else ("🔴 VENTA" if x['CCL'] > avg*1.005 else "⚖️ MANTENER"), axis=1)
    return df

data_df = get_data()
st.dataframe(data_df, use_container_width=True, hide_index=True)

st_autorefresh(interval=600000, key="v2_ref")
