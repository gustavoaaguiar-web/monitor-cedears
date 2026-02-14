import streamlit as st
from streamlit_gsheets import GSheetsConnection
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, pytz, smtplib
from datetime import datetime

# --- CONFIGURACIÓN INICIAL ---
CAPITAL_ORIGEN = 30000000.0
PATRIMONIO_HOY = 33362112.69 
URL_SHEET = st.secrets["spreadsheet"]

# --- CONEXIÓN GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_memoria():
    try:
        df = conn.read(spreadsheet=URL_SHEET, worksheet="Hoja1", ttl=0)
        if not df.empty:
            u = df.iloc[-1]
            return float(u['saldo']), json.loads(u['posiciones']), json.loads(u['historial'])
    except: pass
    return PATRIMONIO_HOY, {}, [{"fecha": datetime.now().strftime("%Y-%m-%d"), "t": PATRIMONIO_HOY}]

def guardar_memoria(s, p, h):
    try:
        nuevo = pd.DataFrame([{"saldo": s, "posiciones": json.dumps(p), "historial": json.dumps(h), "update": datetime.now().strftime("%Y-%m-%d %H:%M")}])
        conn.create(spreadsheet=URL_SHEET, worksheet="Hoja1", data=nuevo)
        st.success("✅ ¡Sincronizado con Simons_DB!")
    except Exception as e:
        st.error(f"❌ Error al guardar: {e}")

# --- INICIALIZACIÓN APP ---
st.set_page_config(page_title="Simons GG v02", layout="wide")

if 'init' not in st.session_state:
    s, p, h = cargar_memoria()
    st.session_state.update({'saldo': s, 'pos': p, 'hist': h, 'init': True})

# --- DASHBOARD ---
patrimonio_total = st.session_state.saldo + sum(float(i['m']) for i in st.session_state.pos.values())
st.title("🦅 Simons GG v02 🤑")

c1, c2, c3 = st.columns(3)
var = ((patrimonio_total / CAPITAL_ORIGEN) - 1) * 100
c1.metric("Patrimonio Total", f"AR$ {patrimonio_total:,.2f}", f"{var:+.4f}%")
c2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Ticket Operativo", f"AR$ {(patrimonio_total*0.08):,.2f}")

# BOTÓN DE PRUEBA MANUAL
st.divider()
if st.button("💾 PROBAR CONEXIÓN (Guardar Saldo Actual)"):
    guardar_memoria(st.session_state.saldo, st.session_state.pos, st.session_state.hist)

# MOTOR DE DATOS (Mismo que antes)
# ... [Aquí sigue tu lógica de yfinance y señales] ...

st_autorefresh(interval=600000, key="v2_ref")
