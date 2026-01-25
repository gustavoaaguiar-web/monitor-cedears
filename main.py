import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json
import os
from datetime import datetime

# --- 1. PERSISTENCIA DE DATOS ---
DB_FILE = "estado_cartera_vfinal.json"

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

    estado = {
        "saldo": st.session_state['saldo_efectivo'],
        "posiciones": st.session_state['posiciones'],
        "historial": st.session_state['historial']
    }
    with open(DB_FILE, "w") as f:
        json.dump(estado, f)

# --- 2. CONFIGURACIÓN DE INTERFAZ ---
st.set_page_config(page_title="Simons-Arg Pro", page_icon="🦅", layout="wide")

if 'inicializado' not in st.session_state:
    datos = cargar_datos()
    st.session_state['saldo_efectivo'] = datos["saldo"]
    st.session_state['posiciones'] = datos["posiciones"]
    st.session_state['historial'] = datos["historial"]
    st.session_state['inicializado'] = True

valor_acciones = sum(p['monto'] for p in st.session_state['posiciones'].values())
patrimonio_total = st.session_state['saldo_efectivo'] + valor_acciones
rendimiento_pct = ((patrimonio_total / 10000000.0) - 1) * 100

st.title("🦅 Simons-Arg: Gestión de Patrimonio")
m1, m2, m3 = st.columns(3)
m1.metric("Patrimonio Total", f"AR$ {patrimonio_total:,.2f}", f"{rendimiento_pct:+.2f}%")
m2.metric("Efectivo Disponible", f"AR$ {st.session_state['saldo_efectivo']:,.2f}")
m3.metric("Capital Inicial", "AR$ 10.000.000,00")

# Gráfico de Evolución
st.subheader("📈 Evolución de la Cartera")
df_hist = pd.DataFrame(st.session_state['historial'])
st.line_chart(df_hist.set_index("fecha"))

# --- 3. PROCESAMIENTO DE MERCADO ---
activos_config = {
    'AAPL': {'ratio': 20, 'ba': 'AAPL.BA'}, 'TSLA': {'ratio': 15, 'ba': 'TSLA.BA'},
    'NVDA': {'ratio': 24, 'ba': 'NVDA.BA'}, 'MSFT': {'ratio': 30, 'ba': 'MSFT.BA'},
    'MELI': {'ratio': 120, 'ba': 'MELI.BA'}, 'GGAL': {'ratio': 10, 'ba': 'GGAL.BA'},
    'YPF':  {'ratio': 1,  'ba': 'YPFD.BA'}, 'PAM':  {'ratio': 25, 'ba': 'PAMP.BA'},
    'BMA':  {'ratio': 10, 'ba': 'BMA.BA'}, 'CEPU': {'ratio': 10, 'ba': 'CEPU.BA'}
}

def procesar_mercado():
    filas = []
    lista_ccl = []
    for t, cfg in activos_config.items():
        try:
            # Línea 88 corregida y cerrada correctamente
            u = yf.download(t, period="2d", interval="1m", progress=False, auto_adjust=True)
            a = yf.download(cfg['ba'], period="2d", interval="1m", progress=False, auto_adjust=True)
            
            if u.empty or a.empty: continue
            
            p_usa, p_arg = float(u['Close'].iloc[-1]), float(a['Close'].iloc[-1])
            ccl = (p_arg * cfg['ratio']) / p_usa
            lista_ccl.append(ccl)
            
            h = yf.download(t, period="3mo", interval="1d", progress=False)
            clima = "⚪"
            if not h.empty and len(h) > 10:
                rets = np.diff(np.log(h['Close'].values.flatten().reshape(-1, 1)), axis=0)
                estado = GaussianHMM(n_components=3).fit(rets).predict(rets)[-1]
                clima = "🟢" if estado == 0 else "🟡" if estado == 1 else "🔴"
            
            filas.append({"Activo": t, "Precio USD": p_usa, "Precio ARS": p_arg, "CCL": ccl, "Clima": clima})
        except: continue
    return pd.DataFrame(filas), np.median(lista_ccl) if lista_ccl else 0

if st.button('🔄 Actualizar y Ejecutar Bot'):
    st.rerun()

data, ccl_avg = procesar_mercado()

# --- 4. LÓGICA DEL BOT Y TABLAS ---
if not data.empty:
    def definir_senal(row):
        if row['CCL'] < ccl_avg * 0.995 and row['Clima'] != "🔴": return "🟢🐂 COMPRA"
        if row['CCL'] > ccl_avg * 1.005: return "🔴🐻 VENTA"
        return "⚖️ MANTENER"
    
    data['Señal'] = data.apply(definir_senal, axis=1)
    
    hubo_cambio = False
    for _, row in data.iterrows():
        ticker = row['Act
