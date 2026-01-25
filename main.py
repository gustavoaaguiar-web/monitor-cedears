import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os, requests
from datetime import datetime

# --- CONFIGURACIÓN DE ALERTAS ---
TELEGRAM_TOKEN = "8519211806:AAFv54n320-ERA2a8eOjqgzQ4IjFnDFpvLY"
TELEGRAM_CHAT_ID = "7338654543"

def enviar_alerta(msj):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': msj}, timeout=10)
    except:
        pass

# --- PERSISTENCIA ---
DB = "estado_final_simons.json"
def cargar():
    if os.path.exists(DB):
        try:
            with open(DB, "r") as f: return json.load(f)
        except: pass
    return {"s": 10000000.0, "p": {}, "h": [{"fecha": datetime.now().strftime("%Y-%m-%d"), "t": 10000000.0}]}

# --- INTERFAZ ---
st.set_page_config(page_title="Simons-Arg Pro", layout="wide")
if 'init' not in st.session_state:
    d = cargar()
    st.session_state.update({'saldo': d["s"], 'pos': d["p"], 'hist': d["h"], 'init': True})

v_i = sum(float(i['m']) for i in st.session_state.pos.values())
pat = st.session_state.saldo + v_i

st.title("🦅 Simons-Arg Pro")
c1, c2, c3 = st.columns(3)
c1.metric("Patrimonio Total", f"AR$ {pat:,.2f}", f"{((pat/10000000.0)-1)*100:+.2f}%")
c2.metric("Efectivo Disponible", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Capital Inicial", "AR$ 10,000,000.00")

st.subheader("📈 Evolución de Cartera")
st.line_chart(pd.DataFrame(st.session_state.hist).set_index("fecha"))

# --- MERCADO ---
cfg = {'AAPL':20,'TSLA':15,'NVDA':24,'MSFT':30,'MELI':120,'GGAL':10,'YPF':1,'PAM':25,'BMA':10,'CEPU':10}

def obtener_datos():
    filas, ccls = [], []
    for t, r in cfg.items():
        try:
            u = yf.download(t, period="2d", interval="1m", progress=False, auto_adjust=True)
            ba = f"{t if t!='YPF' else 'YPFD'}.BA"
            a = yf.download(ba, period="2d", interval="1m", progress=False, auto_adjust=True)
            if u.empty or a.empty: continue
            pu, pa = float(u.Close.iloc[-1]), float(a.Close.iloc[-1])
            ccl = (pa * r) / pu
            ccls.append(ccl)
            
            h = yf.download(t, period="3mo", interval="1d", progress=False)
            cl = "⚪"
            if not h.empty and len(h)>10:
                re = np.diff(np.log(h.Close.values.flatten().reshape(-1, 1)), axis=0)
                cl = "🟢" if GaussianHMM(n_components=3).fit(re).predict(re)[-1]==0 else "🔴"
            filas.append({"Activo": t, "Precio USD": pu, "Precio ARS": pa, "CCL": ccl, "Clima": cl})
        except: continue
    return pd.DataFrame(filas), np.median(ccls) if ccls else 0

if st.button('🔄 Forzar Actualización'): st.rerun()
df, avg_ccl = obtener_datos()

# --- LÓGICA DE TRADING Y COLUMNA SEÑAL ---
if not df.empty:
    st.metric("📊 CCL Promedio del Mercado", f"AR$ {avg_ccl:,.2f}")
    
    # AGREGAMOS LA COLUMNA SEÑAL AL DATAFRAME AQUÍ
    def definir_senal(r):
        if r['CCL'] < (avg_
