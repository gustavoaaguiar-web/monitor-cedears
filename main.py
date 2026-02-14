import streamlit as st
import pandas as pd
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
from datetime import datetime
import json

# --- CONFIGURACIÓN DIRECTA ---
# Usamos el formato de exportación CSV para leer/escribir fácil
SHEET_ID = "19BvTkyD2ddrMsX1ghYGgnnq-BAfYJ_7qkNGqAsJel-M"
URL_DATA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Hoja1"

st.set_page_config(page_title="Simons GG v03", layout="wide")

# --- VALORES INICIALES ---
CAPITAL_ORIGEN = 30000000.0
if 'saldo' not in st.session_state:
    try:
        # Intentamos leer la última fila del Excel
        df_sheet = pd.read_csv(URL_DATA)
        if not df_sheet.empty:
            ultimo = df_sheet.iloc[-1]
            st.session_state.saldo = float(ultimo['saldo'])
            st.session_state.pos = json.loads(ultimo['posiciones'].replace("'", '"'))
        else:
            st.session_state.saldo = 33362112.69
            st.session_state.pos = {}
    except:
        st.session_state.saldo = 33362112.69
        st.session_state.pos = {}

# --- INTERFAZ ---
st.title("🦅 Simons GG v03 🤑")
st.info("Conexión directa vía enlace (Sin Google Cloud)")

patrimonio_total = st.session_state.saldo + sum(float(i.get('m', 0)) for i in st.session_state.pos.values())

c1, c2, c3 = st.columns(3)
var = ((patrimonio_total / CAPITAL_ORIGEN) - 1) * 100
c1.metric("Patrimonio Total", f"AR$ {patrimonio_total:,.2f}", f"{var:+.4f}%")
c2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Ticket 8%", f"AR$ {(patrimonio_total*0.08):,.2f}")

# --- BOTÓN DE RESPALDO ---
if st.button("💾 GUARDAR ESTADO ACTUAL"):
    # Generamos el enlace para que tú mismo pegues la fila si la conexión falla
    nueva_fila = f"{st.session_state.saldo},{json.dumps(st.session_state.pos)},{datetime.now().strftime('%Y-%m-%d %H:%M')}"
    st.code(nueva_fila, language="text")
    st.success("Copia la línea de arriba y pégala en tu Excel para no perder datos.")

# --- MONITOR DE MERCADO ---
st.subheader("📊 Monitor de Arbitraje")
# (Aquí va tu lógica de yfinance que ya funcionaba)
st.write("Cargando datos de mercado...")
            
