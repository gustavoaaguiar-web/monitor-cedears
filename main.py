import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os, requests
from datetime import datetime

# --- CREDENCIALES ---
TOKEN = "8519211806:AAFv54n320-ERA2a8eOjqgzQ4IjFnDFpvLY"
CHAT_ID = "7338654543"

def enviar_telegram(msj):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, data={'chat_id': CHAT_ID, 'text': msj}, timeout=10)
        return res.status_code == 200
    except Exception as e:
        st.error(f"Error de Telegram: {e}")
        return False

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Simons-Arg Pro", layout="wide")

# Botón de prueba manual
if st.sidebar.button("🧪 Probar Conexión Telegram"):
    if enviar_telegram("✅ Prueba de conexión exitosa para Gustavo."):
        st.sidebar.success("¡Mensaje enviado!")
    else:
        st.sidebar.error("Falló el envío. Verificá el bot en Telegram.")

# --- PERSISTENCIA ---
DB = "estado_simons_v13.json"
if 'init' not in st.session_state:
    if os.path.exists(DB):
        with open(DB, "r") as f: d = json.load(f)
    else:
        d = {"s": 10000000.0, "p": {}, "h": [{"fecha": datetime.now().strftime("%Y-%m-%d"), "t": 10000000.0}]}
    st.session_state.update({'saldo': d["s"], 'pos': d["p"], 'hist': d["h"], 'init': True})

v_i = sum(i['m'] for i in st.session_state.pos.values())
pat = st.session_state.saldo + v_i

# --- UI PRINCIPAL ---
st.title("🦅 Simons-Arg Pro")
c1, c2, c3 = st.columns(3)
c1.metric("Patrimonio Total", f"AR$ {pat:,.2f}")
c2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.2f}")
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
            # Clima simple
            h = yf.download(t, period="3mo", interval="1d", progress=False)
            cl = "🟢" if len(h)>5 and h.Close.iloc[-1] > h.Close.iloc[-5] else "🔴"
            filas.append({"Activo": t, "USD": pu, "ARS": pa, "CCL": ccl, "Clima": cl})
        except: continue
    return pd.DataFrame(filas), np.median(ccls) if ccls else 0

df, avg_ccl = obtener_datos()

# --- LÓGICA Y SEÑALES ---
if not df.empty:
    st.metric("📊 CCL Promedio", f"AR$ {avg_ccl:,.2f}")
    
    # Generar columna de Señal explícita
    def procesar_senal(row):
        if row['CCL'] < avg_ccl * 0.995 and row['Clima'] == "🟢": return "🟢 COMPRA"
        if row['CCL'] > avg_ccl * 1.005: return "🔴 VENTA"
        return "⚖️ MANTENER"
    
    df['Señal'] = df.apply(procesar_senal, axis=1)
    
    # Ejecutar operaciones
    upd = False
    for _, r in df.iterrows():
        tk = r['Activo']
        if r['Señal'] == "🟢 COMPRA" and st.session_state.saldo >= 500000 and tk not in st.session_state.pos:
            st.session_state.saldo -= 500000
            st.session_state.pos[tk] = {"m": 500000, "pc": r['ARS']}
            enviar_telegram(f"🟢 COMPRA: {tk} a ${r['ARS']:,.2f}")
            upd = True
        elif r['Señal'] == "🔴 VENTA" and tk in st.session_state.pos:
            p = st.session_state.pos.pop(tk)
            st.session_state.saldo += p['m'] * (r['ARS'] / p['pc'])
            enviar_telegram(f"🔴 VENTA: {tk} a ${r['ARS']:,.2f}")
            upd = True
            
    if upd:
        with open(DB, "w") as f:
            json.dump({"s": st.session_state.saldo, "p": st.session_state.pos, "h": st.session_state.hist}, f)

    st.subheader("🏢 Posiciones")
    st.table(pd.DataFrame([{"Activo":t, "Monto":f"${p['m']:,.0f}"} for t,p in st.session_state.pos.items()]))
    
    st.subheader("📊 Monitor de Mercado")
    st.dataframe(df, use_container_width=True, hide_index=True)

st_autorefresh(interval=600000, key="bot_v13")
