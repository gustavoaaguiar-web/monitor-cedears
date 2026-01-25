import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json
import os
from datetime import datetime

# --- 1. PERSISTENCIA DE DATOS (EL "DISCO DURO" DEL BOT) ---
DB_FILE = "estado_cartera_v3.json"

def cargar_datos():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    # Si el archivo no existe, creamos el capital inicial de AR$ 10M
    return {
        "saldo": 10000000.0, 
        "posiciones": {}, 
        "historial": [{"fecha": datetime.now().strftime("%Y-%m-%d"), "valor_total": 10000000.0}]
    }

def guardar_datos():
    # Calculamos el valor actual (Efectivo + Valor de mercado de acciones)
    valor_activos = sum(p['monto'] for p in st.session_state['posiciones'].values())
    total = st.session_state['saldo_efectivo'] + valor_activos
    
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

# Cargar estado persistente
if 'inicializado' not in st.session_state:
    datos = cargar_datos()
    st.session_state['saldo_efectivo'] = datos["saldo"]
    st.session_state['posiciones'] = datos["posiciones"]
    st.session_state['historial'] = datos["historial"]
    st.session_state['inicializado'] = True

# Cálculos de Cartera
valor_acciones = sum(p['monto'] for p in st.session_state['posiciones'].values())
patrimonio_total = st.session_state['saldo_efectivo'] + valor_acciones
rendimiento_pct = ((patrimonio_total / 10000000.0) - 1) * 100

st.title("🦅 Simons-Arg: Gestión de Patrimonio")
st.write("Estrategia automatizada con AR$ 10.000.000 iniciales")

# Métricas Principales
m1, m2, m3 = st.columns(3)
m1.metric("Patrimonio Total", f"AR$ {patrimonio_total:,.2f}", f"{rendimiento_pct:+.2f}%")
m2.metric("Efectivo Disponible", f"AR$ {st.session_state['saldo_efectivo']:,.2f}")
m3.metric("Capital Inicial", "AR$ 10.000.000,00")

# Gráfico de Evolución
st.subheader("📈 Evolución de la Cartera")
df_hist = pd.DataFrame(st.session_state['historial'])
st.line_chart(df_hist.set_index("fecha"))

# --- 3. PROCESAMIENTO DE MERCADO (SIN VIST) ---
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
            u = yf.download(t, period="2d", interval
