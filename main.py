import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json
import os
from datetime import datetime

# --- PERSISTENCIA ---
DB_FILE = "estado_v4.json"

def cargar():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: pass
    return {"saldo": 10000000.0, "posiciones": {}, "hist": [{"fecha": datetime.now().strftime("%Y-%m-%d"), "total": 10000000.0}]}

def guardar():
    v_act = sum(p['monto'] for p in st.session_state.pos.values())
    total = st.session_state.saldo + v_act
    hoy = datetime.now().strftime("%Y-%m-%d")
    if not st.session_state.hist or st.session_state.hist[-1]['fecha'] != hoy:
        st.session_state.hist.append({"fecha": hoy, "total": total})
    else:
        st.session_state.hist[-1]['total'] = total
    with open(DB_FILE, "w") as f:
        json.dump({"saldo": st.session_state.saldo, "posiciones": st.session_state.pos, "historial": st.session_state.hist}, f)

# --- INTERFAZ ---
st.set_page_config(page_title="Simons-Arg Pro", layout="wide")
if 'init' not in st.session_state:
    d = cargar()
    st.session_state.update({'saldo': d["saldo"], 'pos': d["posiciones"], 'hist': d.get("historial", d.get("hist")), 'init': True})

v_p = sum(p['monto'] for p in st.session_state.pos.values())
patrimonio = st.session_state.saldo + v_p

st.title("🦅 Simons-Arg Pro")
c1, c2, c3 = st.columns(3)
c1.metric("Patrimonio Total", f"AR$ {patrimonio:,.2f}", f"{((patrimonio/10000000.0)-1)*100:+.2f}%")
c2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Invertido", f"AR$ {v_p:,.2f}")

st.subheader("📈 Evolución")
st.line_chart(pd.DataFrame(st.session_state.hist).set_index("fecha"))

# --- MERCADO ---
cfg_act = {
    'AAPL': 20, 'TSLA': 15, 'NVDA': 24, 'MSFT': 30, 
    'MELI': 120, 'GGAL': 10, 'YPF': 1, 'PAM': 25, 
    'BMA': 10, 'CEPU': 10
}

def obtener():
    filas, ccls = [], []
    for t, r in cfg_act.items():
        try:
            u = yf.download(t, period="2d", interval="1m", progress=False, auto_adjust=True)
            a = yf.download(f"{t if t != 'YPF' else 'YPFD'}.BA", period="2d", interval="1m", progress=False, auto_adjust=True)
            if u.empty or a.empty: continue
            pu, pa = float(u.Close.iloc[-1]), float(a.Close.iloc[-1])
            ccl = (pa * r) / pu
            ccls.append(ccl)
            h = yf.download(t, period="3mo", interval="1d", progress=False)
            clm = "⚪"
            if not h.empty and len(h) > 10:
                re = np.diff(np.log(h.Close.values.flatten().reshape(-1, 1)), axis=0)
                clm = "🟢" if GaussianHMM(n_components=3).fit(re).predict(re)[-1] == 0 else "🔴"
            filas.append({"Activo": t, "Precio USD": pu, "Precio ARS": pa, "CCL": ccl, "Clima": clm})
        except: continue
    return pd.DataFrame(filas), np.median(ccls) if ccls else 0

if st.button('🔄 Actualizar'): st.rerun()
df, avg_ccl = obtener()

# --- BOT ---
if not df.empty:
    cambio = False
    for _, row in df.iterrows():
        tk = row['Activo']
        is_low = row['CCL'] < avg_ccl * 0.995
        is_high = row['CCL'] > avg_ccl * 1.005
        
        # Compra
        if is_low and row['Clima'] != "🔴" and st.session_state.saldo >= 500000 and tk not in st.session_state.pos:
            st.session_state.saldo -= 500000
            st.session_state.pos[tk] = {"monto": 500000, "pc": row['Precio ARS']}
            st.toast(f"Comprado {tk}")
            cambio = True
        # Venta
        elif is_high and tk in st.session_state.pos:
            p = st.session_state.pos.pop(tk)
            st.session_state.saldo += p['monto'] * (row['Precio ARS'] / p['pc'])
            st.toast(f"Vendido {tk}")
            cambio = True
            
    if cambio: guardar()
    
    st.subheader("🏢 Posiciones")
    if st.session_state.pos:
        det = []
        for t, p in st.session_state.pos.items():
            act = df[df.Activo == t].iloc[0]['Precio ARS'] if t in df.Activo.values else p['pc']
            det.append({"Activo": t, "Invertido": f"${p['monto']:,.0f}", "Resultado": f"{((act/p['pc'])-1)*100:+.2f}%"})
        st.table(pd.DataFrame(det))
    
    st.subheader("📊 Monitor")
    st.dataframe(df, use_container_width=True, hide_index=True)

st_autorefresh(interval=900000, key="bot")
