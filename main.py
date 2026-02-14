import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
import json
from datetime import datetime

# URL de tu Google Sheet
URL_DB = "https://docs.google.com/spreadsheets/d/19BvTkyD2ddrMsX1ghYGgnnq-BAfYJ_7qkNGqAsJel-M/edit?usp=drivesdk"

st.set_page_config(page_title="Simons GG v05", layout="wide")

# Conexión automática
conn = st.connection("gsheets", type=GSheetsConnection)

# Función para LEER datos
def cargar_datos():
    try:
        df = conn.read(spreadsheet=URL_DB, worksheet="Hoja1", ttl=0)
        if not df.empty:
            ultimo = df.iloc[-1]
            return float(ultimo['saldo']), json.loads(str(ultimo['posiciones']).replace("'", '"')), json.loads(str(ultimo['historial']).replace("'", '"'))
    except:
        return 33362112.69, {}, [{"fecha": "2026-02-14", "t": 33362112.69}]

if 'saldo' not in st.session_state:
    s, p, h = cargar_datos()
    st.session_state.saldo, st.session_state.pos, st.session_state.hist = s, p, h

st.title("🦅 Simons GG v05 - Full Auto")

# Función para GUARDAR datos automáticamente
def guardar_en_sheet():
    nueva_fila = pd.DataFrame([{
        "saldo": st.session_state.saldo,
        "posiciones": json.dumps(st.session_state.pos),
        "historial": json.dumps(st.session_state.hist),
        "update": datetime.now().strftime("%Y-%m-%d %H:%M")
    }])
    # Esto escribe directamente en la siguiente fila vacía
    conn.create(spreadsheet=URL_DB, worksheet="Hoja1", data=nueva_fila)
    st.toast("✅ Sincronizado con Google Sheets")

# Cálculos de interfaz
patrimonio = st.session_state.saldo + sum(float(v.get('m', 0)) for v in st.session_state.pos.values())
st.metric("Patrimonio Total", f"AR$ {patrimonio:,.2f}")

# Botón para probar el auto-guardado
if st.button("🚀 PROBAR CONEXIÓN (GUARDAR)"):
    guardar_en_sheet()

st.divider()
st.subheader("📊 Monitor de Arbitraje")
# ... (Aquí sigue tu lógica de yfinance y señales)
