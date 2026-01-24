import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# Configuración Inicial
st.set_page_config(page_title="Simons-Arg Bot", page_icon="🦅", layout="wide")

# Inicialización de Saldo (AR$ 10.000.000)
if 'saldo_efectivo' not in st.session_state:
    st.session_state['saldo_efectivo'] = 10000000.0
if 'posiciones' not in st.session_state:
    st.session_state['posiciones'] = {}

st.title("🦅 Monitor & Bot Simons-Arg")
st.write("Panel optimizado para operaciones en Pesos (Bull Market)")

# Métricas de Cartera Virtual
col_m1, col_m2 = st.columns(2)
col_m1.metric("Saldo Disponible", f"AR$ {st.session_state['saldo_efectivo']:,.2f}")
total_invertido = sum(st.session_state['posiciones'].values())
col_m2.metric("Total Invertido (Simulado)", f"AR$ {total_invertido:,.2f}")

# DICCIONARIO SIN VIST
activos_config = {
    'AAPL': {'ratio': 20, 'ba': 'AAPL.BA'}, 'TSLA': {'ratio': 15, 'ba': 'TSLA.BA'},
    'NVDA': {'ratio': 24, 'ba': 'NVDA.BA'}, 'MSFT': {'ratio': 30, 'ba': 'MSFT.BA'},
    'MELI': {'ratio': 120, 'ba': 'MELI.BA'}, 'GGAL': {'ratio': 10, 'ba': 'GGAL.BA'},
    'YPF':  {'ratio': 1,  'ba': 'YPFD.BA'}, 'PAM':  {'ratio': 25, 'ba': 'PAMP.BA'},
    'BMA':  {'ratio': 10, 'ba': 'BMA.BA'}, 'CEPU': {'ratio': 10, 'ba': 'CEPU.BA'}
}

def procesar_datos():
    filas = []
    lista_ccl = []
    for t, config in activos_config.items():
        try:
            u = yf.download(t, period="5d", interval="1m", progress=False, auto_adjust=True)
            a = yf.download(config['ba'], period="5d", interval="1m", progress=False, auto_adjust=True)
            
            if u.empty or a.empty: continue
            
            val_usa = float(u['Close'].iloc[-1])
            val_arg = float(a['Close'].iloc[-1])
            ccl = (val_arg * config['ratio']) / val_usa
            lista_ccl.append(ccl)
            
            h = yf.download(t, period="3mo", interval="1d", progress=False)
            clima = "⚪"
            if not h.empty and len(h) > 10:
                rets = np.diff(np.log(h['Close'].values.flatten().reshape(-1, 1)), axis=0)
                model = GaussianHMM(n_components=3, random_state=42).fit(rets)
                estado = model.predict(rets)[-1]
                clima = "🟢" if estado == 0 else "🟡" if estado == 1 else "🔴"
            
            filas.append({
                "Activo": t, 
                "Precio USD": round(val_usa, 2), 
                "Precio ARS": round(val_arg, 2), 
                "CCL": round(ccl, 2), 
                "Clima": clima
            })
        except: continue
    return pd.DataFrame(filas), np.median(lista_ccl) if lista_ccl else 0

if st.button('🔄 Actualizar y Operar'):
    st.rerun()

with st.spinner('Analizando oportunidades en Pesos...'):
    data, ccl_avg = procesar_datos()

if not data.empty:
    st.metric("CCL Promedio del Mercado", f"${ccl_avg:,.2f}")
    
    def definir_senal(row):
        if row['CCL'] < ccl_avg * 0.995 and row['Clima'] != "🔴": return "🟢🐂 COMPRA"
        if row['CCL'] > ccl_avg * 1.005: return "🔴🐻 VENTA"
        return "⚖️ MANTENER"
    
    data['Señal'] = data.apply(definir_senal, axis=1)

    # Lógica de Ejecución Virtual
    for _, row in data.iterrows():
        activo = row['Activo']
        # Comprar si hay señal y saldo (Monto fijo de AR$ 500k por vez)
        if row['Señal'] == "🟢🐂 COMPRA" and st.session_state['saldo_efectivo'] >= 500000:
            if activo not in st.session_state['posiciones']:
                st.session_state['saldo_efectivo'] -= 500000
                st.session_state['posiciones'][activo] = 500000
                st.toast(f"Bot: Comprado {activo} por AR$ 500.000")
        
        # Vender si hay señal de oso y tenemos posición
        elif row['Señal'] == "🔴🐻 VENTA" and activo in st.session_state['posiciones']:
            monto_recuperado = st.session_state['posiciones'].pop(activo)
            st.session_state['saldo_efectivo'] += monto_recuperado
            st.toast(f"Bot: Vendido {activo}. Saldo recuperado.")

    altura_tabla = (len(data) + 1) * 39
    st.dataframe(data, use_container_width=True, hide_index=True, height=altura_tabla)

st_autorefresh(interval=900000, key="bot_refresh")
