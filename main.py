import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import json, os
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURACIÓN ---
TOKEN = "8519211806:AAFv54n320-ERA2a8eOjqgzQ4IjFnDFpvLY"
CHAT_ID = "7338654543"

def enviar_telegram(msj):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': CHAT_ID, 'text': msj}, timeout=8)
    except:
        pass

st.set_page_config(page_title="Simons-Arg Pro", layout="wide")

# --- TEST DE TELEGRAM EN PANTALLA ---
if st.sidebar.button("📩 Forzar Alerta"):
    enviar_telegram("Prueba manual desde el panel.")
    st.sidebar.success("Enviado. Revisa Telegram.")

# --- DATOS ---
DB = "estado_v15.json"
if 'init' not in st.session_state:
    st.session_state.update({'saldo': 10000000.0, 'pos': {}, 'init': True})

st.title("🦅 Simons-Arg Pro")

# --- DESCARGA DE DATOS SIN AUTO-ADJUST (Más estable) ---
cfg = {'AAPL':20,'TSLA':15,'NVDA':24,'MSFT':30,'GGAL':10,'YPF':1}

def obtener_datos():
    filas = []
    ccls = []
    for t, r in cfg.items():
        try:
            # Descargamos sin parámetros complejos para evitar errores
            u = yf.Ticker(t).history(period="1d", interval="1m")
            ba_ticker = f"{t if t!='YPF' else 'YPFD'}.BA"
            a = yf.Ticker(ba_ticker).history(period="1d", interval="1m")
            
            if not u.empty and not a.empty:
                pu = float(u.Close.iloc[-1])
                pa = float(a.Close.iloc[-1])
                ccl = (pa * r) / pu
                ccls.append(ccl)
                filas.append({"Activo": t, "USD": round(pu,2), "ARS": round(pa,2), "CCL": round(ccl,2)})
        except Exception as e:
            st.error(f"Error en {t}: {e}")
            continue
    return pd.DataFrame(filas), np.median(ccls) if ccls else 0

with st.spinner('Actualizando precios de mercado...'):
    df, avg_ccl = obtener_datos()

# --- MOSTRAR RESULTADOS SIEMPRE ---
if not df.empty:
    st.metric("📊 CCL Promedio", f"AR$ {avg_ccl:,.2f}")
    
    # Lógica de señales simplificada
    df['Señal'] = df['CCL'].apply(lambda x: "🟢 COMPRA" if x < avg_ccl*0.99 else ("🔴 VENTA" if x > avg_ccl*1.01 else "⚖️ ESPERA"))
    
    st.subheader("📋 Monitor de Mercado")
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.error("⚠️ No se pudieron obtener datos de Yahoo Finance. Intenta refrescar la página.")
    st.info("Nota: Revisa si el mercado está abierto o si hay conexión a internet en el servidor.")

st_autorefresh(interval=300000, key="v15")
