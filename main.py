import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os
from datetime import datetime

# --- PERSISTENCIA DE DATOS ---
DB = "estado_simons_solo.json"
def cargar_datos():
    if os.path.exists(DB):
        try:
            with open(DB, "r") as f: return json.load(f)
        except: pass
    return {"s": 10000000.0, "p": {}, "h": [{"fecha": datetime.now().strftime("%Y-%m-%d"), "t": 10000000.0}]}

# --- CONFIGURACIÓN UI ---
st.set_page_config(page_title="Simons-Arg Pro", layout="wide")

if 'init' not in st.session_state:
    d = cargar_datos()
    st.session_state.update({'saldo': d["s"], 'pos': d["p"], 'hist': d["h"], 'init': True})

# --- CÁLCULOS DE PATRIMONIO ---
valor_invertido = sum(float(i['m']) for i in st.session_state.pos.values())
patrimonio_total = st.session_state.saldo + valor_invertido

st.title("🦅 Simons-Arg Pro")
c1, c2, c3 = st.columns(3)
c1.metric("Patrimonio Total", f"AR$ {patrimonio_total:,.2f}")
c2.metric("Efectivo Disponible", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Capital Inicial", "AR$ 10,000,000.00")

st.subheader("📈 Evolución de Cartera")
st.line_chart(pd.DataFrame(st.session_state.hist).set_index("fecha"))

# --- DESCARGA DE MERCADO ---
cfg = {'AAPL':20,'TSLA':15,'NVDA':24,'MSFT':30,'MELI':120,'GGAL':10,'YPF':1,'PAM':25,'BMA':10,'CEPU':10}

@st.cache_data(ttl=600)
def obtener_mercado():
    filas, ccls = [], []
    for t, r in cfg.items():
        try:
            u = yf.download(t, period="1d", interval="5m", progress=False)
            ba = f"{t if t!='YPF' else 'YPFD'}.BA"
            a = yf.download(ba, period="1d", interval="5m", progress=False)
            if u.empty or a.empty: continue
            
            pu, pa = float(u.Close.iloc[-1]), float(a.Close.iloc[-1])
            ccl_i = (pa * r) / pu
            ccls.append(ccl_i)
            
            # Clima: Tendencia de la última hora
            clima = "🟢" if u.Close.iloc[-1] > u.Close.iloc[0] else "🔴"
            filas.append({"Activo": t, "USD": pu, "ARS": pa, "CCL": ccl_i, "Clima": clima})
        except: continue
    return pd.DataFrame(filas), np.median(ccls) if ccls else 0

df, avg_ccl = obtener_mercado()

# --- LÓGICA DE SEÑALES Y TABLA ---
if not df.empty:
    st.metric("📊 CCL Promedio del Mercado", f"AR$ {avg_ccl:,.2f}")
    
    # Definición de Señal
    def generar_senal(row):
        if row['CCL'] < (avg_ccl * 0.995) and row['Clima'] == "🟢": return "🟢 COMPRA"
        if row['CCL'] > (avg_ccl * 1.005): return "🔴 VENTA"
        return "⚖️ MANTENER"

    df['Señal'] = df.apply(generar_senal, axis=1)
    
    # Simulación de Trading Automático
    actualizar_db = False
    for _, r in df.iterrows():
        tk = r['Activo']
        if r['Señal'] == "🟢 COMPRA" and st.session_state.saldo >= 500000 and tk not in st.session_state.pos:
            st.session_state.saldo -= 500000
            st.session_state.pos[tk] = {"m": 500000, "pc": r['ARS']}
            actualizar_db = True
        elif r['Señal'] == "🔴 VENTA" and tk in st.session_state.pos:
            p = st.session_state.pos.pop(tk)
            st.session_state.saldo += p['m'] * (r['ARS'] / p['pc'])
            actualizar_db = True
            
    if actualizar_db:
        with open(DB, "w") as f:
            json.dump({"s": st.session_state.saldo, "p": st.session_state.pos, "h": st.session_state.hist}, f)

    st.subheader("📊 Monitor de Mercado")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("🏢 Posiciones Actuales")
    if st.session_state.pos:
        st.table(pd.DataFrame([{"Activo":k, "Invertido":f"${v['m']:,.0f}"} for k,v in st.session_state.pos.items()]))
else:
    st.warning("⚠️ Conectando con Yahoo Finance... Si no carga, refresca la página.")

st_autorefresh(interval=600000, key="v_estable_final")
