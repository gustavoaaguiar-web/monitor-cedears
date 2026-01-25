import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os, requests
from datetime import datetime

# --- CONFIGURACIÓN ---
TOKEN = "8519211806:AAFv54n320-ERA2a8eOjqgzQ4IjFnDFpvLY"
CHAT_ID = "7338654543"

def enviar_alerta(msj):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': CHAT_ID, 'text': msj}, timeout=10)
    except:
        pass

# --- PERSISTENCIA ---
DB = "estado_simons_v20.json"
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
c1.metric("Patrimonio Total", f"AR$ {pat:,.2f}")
c2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Capital Inicial", "AR$ 10,000,000.00")

# --- MERCADO ---
cfg = {'AAPL':20,'TSLA':15,'NVDA':24,'MSFT':30,'MELI':120,'GGAL':10,'YPF':1,'PAM':25,'BMA':10,'CEPU':10}

def obtener_datos():
    filas, ccls = [], []
    for t, r in cfg.items():
        try:
            # Descarga simplificada para evitar bloqueos
            u = yf.download(t, period="1d", interval="5m", progress=False)
            ba = f"{t if t!='YPF' else 'YPFD'}.BA"
            a = yf.download(ba, period="1d", interval="5m", progress=False)
            
            if u.empty or a.empty: continue
            
            pu, pa = float(u.Close.iloc[-1]), float(a.Close.iloc[-1])
            ccl_i = (pa * r) / pu
            ccls.append(ccl_i)
            
            # Clima basado en los últimos 30 min (Simple y rápido)
            clima_v = "🟢" if u.Close.iloc[-1] > u.Open.iloc[0] else "🔴"
            
            filas.append({
                "Activo": t, 
                "Precio USD": round(pu, 2), 
                "Precio ARS": round(pa, 2), 
                "CCL": round(ccl_i, 2), 
                "Clima": clima_v
            })
        except:
            continue
    return pd.DataFrame(filas), np.median(ccls) if ccls else 0

with st.spinner('Actualizando Monitor de Mercado...'):
    df, avg_ccl = obtener_datos()

# --- SEÑALES Y TRADING ---
if not df.empty:
    st.metric("📊 CCL Promedio", f"AR$ {avg_ccl:,.2f}")
    
    # Columna Señal integrada directamente
    df['Señal'] = df.apply(lambda r: "🟢 COMPRA" if r['CCL'] < (avg_ccl * 0.995) and r['Clima'] == "🟢" else ("🔴 VENTA" if r['CCL'] > (avg_ccl * 1.005) else "⚖️ MANTENER"), axis=1)
    
    upd = False
    for _, r in df.iterrows():
        tk = r['Activo']
        if r['Señal'] == "🟢 COMPRA" and st.session_state.saldo >= 500000 and tk not in st.session_state.pos:
            st.session_state.saldo -= 500000
            st.session_state.pos[tk] = {"m": 500000, "pc": r['Precio ARS']}
            enviar_alerta(f"🟢 COMPRA: {tk} a ${r['Precio ARS']:,.2f}")
            upd = True
        elif r['Señal'] == "🔴 VENTA" and tk in st.session_state.pos:
            p = st.session_state.pos.pop(tk)
            st.session_state.saldo += p['m'] * (r['Precio ARS'] / p['pc'])
            enviar_alerta(f"🔴 VENTA: {tk} a ${r['Precio ARS']:,.2f}")
            upd = True
            
    if upd:
        with open(DB, "w") as f:
            json.dump({"s": st.session_state.saldo, "p": st.session_state.pos, "h": st.session_state.hist}, f)

    st.subheader("📊 Monitor de Mercado")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("🏢 Posiciones")
    if st.session_state.pos:
        st.table(pd.DataFrame([{"Activo":k, "Monto":f"${v['m']:,.0f}"} for k,v in st.session_state.pos.items()]))
else:
    st.warning("⚠️ No hay datos disponibles en este momento. Verificá la conexión con Yahoo Finance.")

st_autorefresh(interval=600000, key="v20_definitiva")
