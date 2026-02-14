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
# Usamos tu URL directamente aquí para evitar errores de Secrets
URL_FINAL = "https://docs.google.com/spreadsheets/d/19BvTkyD2ddrMsX1ghYGgnnq-BAfYJ_7qkNGqAsJel-M/edit?usp=drivesdk"

# --- CONEXIÓN GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_memoria():
    try:
        df = conn.read(spreadsheet=URL_FINAL, worksheet="Hoja1", ttl=0)
        if not df.empty:
            u = df.iloc[-1]
            return float(u['saldo']), json.loads(u['posiciones']), json.loads(u['historial'])
    except: pass
    return PATRIMONIO_HOY, {}, [{"fecha": datetime.now().strftime("%Y-%m-%d"), "t": PATRIMONIO_HOY}]

def guardar_memoria(s, p, h):
    try:
        nuevo = pd.DataFrame([{
            "saldo": s, 
            "posiciones": json.dumps(p), 
            "historial": json.dumps(h), 
            "update": datetime.now().strftime("%Y-%m-%d %H:%M")
        }])
        conn.create(spreadsheet=URL_FINAL, worksheet="Hoja1", data=nuevo)
        st.success("✅ ¡Backup sincronizado con éxito!")
    except Exception as e:
        st.error(f"❌ Error técnico: {e}")

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
c3.metric("Ticket 8%", f"AR$ {(patrimonio_total*0.08):,.2f}")

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
            u = yf.download(t, period="3mo", interval="1d", progress=False)
            a = yf.download(ba, period="1d", interval="1m", progress=False)
            pu, pa = float(u.Close.iloc[-1]), float(a.Close.iloc[-1])
            ccl = (pa * r) / pu
            ccls.append(ccl)
            
            re = np.diff(np.log(u.Close.values.flatten().reshape(-1, 1)), axis=0)
            cl = "🟢" if GaussianHMM(n_components=3, random_state=42).fit(re).predict(re)[-1] == 0 else "🔴"
            filas.append({"Activo": t, "USD": pu, "ARS": pa, "CCL": ccl, "Clima": cl})
        except: continue
    
    df = pd.DataFrame(filas)
    if not df.empty:
        avg = np.median(ccls)
        df['Señal'] = df.apply(lambda x: "🟢 COMPRA" if x['CCL'] < avg*0.995 and x['Clima']=="🟢" else ("🔴 VENTA" if x['CCL'] > avg*1.005 else "⚖️ MANTENER"), axis=1)
    return df

st.dataframe(get_data(), use_container_width=True, hide_index=True)

st_autorefresh(interval=3600000, key="v2_ref")
