import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
import json
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Simons GG v05.2", layout="wide")

# Conexión directa usando los Secrets que ya guardaste
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        # Usamos st.secrets para que no haya error de "Spreadsheet not specified"
        df = conn.read(spreadsheet=st.secrets["spreadsheet"], worksheet="Hoja1", ttl=0)
        if not df.empty:
            u = df.iloc[-1]
            return float(u['saldo']), json.loads(str(u['posiciones']).replace("'", '"')), json.loads(str(u['historial']).replace("'", '"'))
    except:
        return 33362112.69, {}, [{"fecha": "2026-02-14", "t": 33362112.69}]

if 'saldo' not in st.session_state:
    s, p, h = cargar_datos()
    st.session_state.saldo, st.session_state.pos, st.session_state.hist = s, p, h

# --- INTERFAZ ---
st.title("🦅 Simons GG v05.2 - Corrección de Conexión")

patrimonio = st.session_state.saldo + sum(float(v.get('m', 0)) for v in st.session_state.pos.values())
st.metric("Patrimonio Total", f"AR$ {patrimonio:,.2f}")

# --- FUNCIÓN DE GUARDADO CORREGIDA ---
def guardar_en_sheet():
    nueva_fila = pd.DataFrame([{
        "saldo": st.session_state.saldo,
        "posiciones": json.dumps(st.session_state.pos),
        "historial": json.dumps(st.session_state.hist),
        "update": datetime.now().strftime("%Y-%m-%d %H:%M")
    }])
    try:
        # Aquí estaba el error, ahora usamos st.secrets["spreadsheet"]
        conn.create(spreadsheet=st.secrets["spreadsheet"], worksheet="Hoja1", data=nueva_fila)
        st.success("✅ ¡Guardado en Google Sheets con éxito!")
    except Exception as e:
        st.error(f"Fallo al escribir: {e}")

if st.button("🚀 PROBAR CONEXIÓN (GUARDAR)"):
    guardar_en_sheet()

st.divider()
st.subheader("📊 Monitor de Mercado")
# Aquí puedes re-pegar tu lógica de yfinance si la necesitas ver
