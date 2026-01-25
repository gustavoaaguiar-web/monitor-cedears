import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json
import os
from datetime import datetime

# --- 1. PERSISTENCIA ---
DB_FILE = "estado_cartera_v_finalisima.json"

def cargar_datos():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {
        "saldo": 10000000.0, 
        "posiciones": {}, 
        "historial": [{"fecha": datetime.now().strftime("%Y-%m-%d"), "valor_total": 10000000.0}]
    }

def guardar_datos():
    valor_acciones = sum(p['monto'] for p in st.session_state['posiciones'].values())
    total = st.session_state['saldo_efectivo'] + valor_acciones
    hoy = datetime.now().strftime("%Y-%m-%d")
    if not st.session_state['historial'] or st.session_state['historial'][-1]['fecha'] != hoy:
        st.session_state['historial'].append({"fecha": hoy, "valor_total": total})
    else:
        st.session_state['historial'][-1]['valor_total'] = total
    estado = {"saldo": st.session_state['saldo_efectivo'], "posiciones": st.session_state['posiciones'], "historial": st.session_state['historial']}
    with open(DB_FILE, "w") as f:
        json.dump(estado, f)

# --- 2. INTERFAZ ---
st.set_page_config(page_title="Simons-Arg Pro", page_icon="🦅", layout="wide")

if 'inicializado' not in st.session_state:
    datos = cargar_datos()
    st.session_state.update({'saldo_efectivo': datos["saldo"], 'posiciones': datos["posiciones"], 'historial': datos["historial"], 'inicializado': True})

v_acciones = sum(p['monto'] for p in st.session_state['posiciones'].values())
total_patrimonio = st.session_state['saldo_efectivo'] + v_acciones
rendimiento = ((total_patrimonio / 10000000.0) - 1) * 100

st.title("🦅 Simons-Arg Pro")
c1, c2, c3 = st.columns(3)
c1.metric("Patrimonio Total", f"AR$ {total_patrimonio:,.2f}", f"{rendimiento:+.2f}%")
c2.metric("Saldo Efectivo", f"AR$ {st.session_state['saldo_efectivo']:,.2f}")
c3.metric("Capital Inicial", "AR$ 10.000.000")

st.subheader("📈 Evolución")
st.line_chart(pd.DataFrame(st.session_state['historial']).set_index("fecha"))

# --- 3. MERCADO ---
activos_config = {
    'AAPL': {'ratio': 20, 'ba': 'AAPL.BA'}, 'TSLA': {'ratio': 15, 'ba': 'TSLA.BA'},
    'NVDA': {'ratio': 24, 'ba': 'NVDA.BA'}, 'MSFT': {'ratio': 30, 'ba': 'MSFT.BA'},
    'MELI': {'ratio': 120, 'ba': 'MELI.BA'}, 'GGAL': {'ratio': 10, 'ba': 'GGAL.BA'},
    'YPF':  {'ratio': 1,  'ba': 'YPFD.BA'}, 'PAM':  {'ratio': 25, 'ba': 'PAMP.BA'},
    'BMA':  {'ratio': 10, 'ba': 'BMA.BA'}, 'CEPU': {'ratio': 10, 'ba': 'CEPU.BA'}
}

def obtener_datos():
    filas, lista_ccl = [], []
    for t, cfg in activos_config.items():
        try:
            u = yf.download(t, period="2d", interval="1m", progress=False, auto_adjust=True)
            a = yf.download(cfg['ba'], period="2d", interval="1m", progress=False, auto_adjust=True)
            if u.empty or a.empty: continue
            p_u, p_a = float(u['Close'].iloc[-1]), float(a['Close'].iloc[-1])
            ccl = (p_a * cfg['ratio']) / p_u
            lista_ccl.append(ccl)
            h = yf.download(t, period="3mo", interval="1d", progress=False)
            clima = "⚪"
            if not h.empty and len(h) > 10:
                rets = np.diff(np.log(h['Close'].values.flatten().reshape(-1, 1)), axis=0)
                est = GaussianHMM(n_components=3).fit(rets).predict(rets)[-1]
                clima = "🟢" if est == 0 else "🟡" if est == 1 else "🔴"
            filas.append({"Activo": t, "Precio USD": p_u, "Precio ARS": p_a, "CCL": ccl, "Clima": clima})
        except: continue
    return pd.DataFrame(filas), np.median(lista_ccl) if lista_ccl else 0

if st.button('🔄 Actualizar'): st.rerun()
df, ccl_avg = obtener_datos()

# --- 4. BOT ---
if not df.empty:
    df['Señal'] = df.apply(lambda r: "🟢🐂 COMPRA" if r['CCL'] < ccl_avg * 0.995 and r['Clima'] != "🔴" else ("🔴🐻 VENTA" if r['CCL'] > ccl_avg * 1.005 else "⚖️ MANTENER"), axis=1)
    cambio = False
    for _, row in df.iterrows():
        tk = row['Activo']
        if row['Señal'] == "🟢🐂 COMPRA" and st.session_state['saldo_efectivo'] >= 500000 and tk not in st.session_state['posiciones']:
            st.session_state['saldo_efectivo'] -= 500000
            st.session_state['posiciones'][tk] = {"monto": 500000, "p_compra": row['Precio ARS']}
            st.toast(f"Comprado {tk}")
            cambio = True
        elif row['Señal'] == "🔴🐻 VENTA" and tk in st.session_state['posiciones']:
            p = st.session_state['posiciones'].pop(tk)
            st.session_state['saldo_efectivo'] += p['monto'] * (row['Precio ARS'] / p['p_compra'])
            st.toast(f"Vendido {tk}")
            cambio = True
    if cambio: guardar_datos()
    
    st.subheader("🏢 Posiciones")
    if st.session_state['posiciones']:
