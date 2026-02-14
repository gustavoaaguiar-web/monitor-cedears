import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime

# URL DIRECTA (Sin intermediarios para evitar el error de 'not specified')
URL_PLANILLA = "https://docs.google.com/spreadsheets/d/19BvTkyD2ddrMsX1ghYGgnnq-BAfYJ_7qkNGqAsJel-M/edit?usp=drivesdk"

st.set_page_config(page_title="Simons GG v06", layout="wide")

# Forzamos la conexión con los secrets que ya tenés guardados
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        # Le pasamos la URL directamente aquí
        df = conn.read(spreadsheet=URL_PLANILLA, worksheet="Hoja1", ttl=0)
        if not df.empty:
            u = df.iloc[-1]
            return float(u['saldo']), json.loads(str(u['posiciones']).replace("'", '"')), json.loads(str(u['historial']).replace("'", '"'))
    except Exception as e:
        return 33362112.69, {}, [{"fecha": "2026-02-14", "t": 33362112.69}]

if 'saldo' not in st.session_state:
    s, p, h = cargar_datos()
    st.session_state.saldo, st.session_state.pos, st.session_state.hist = s, p, h

st.title("🦅 Simons GG v06 - Conexión Forzada")

# --- MÉTRICAS ---
patrimonio = st.session_state.saldo + sum(float(v.get('m', 0)) for v in st.session_state.pos.values())
st.metric("Patrimonio Total", f"AR$ {patrimonio:,.2f}")

# --- FUNCIÓN DE GUARDADO REFORZADA ---
def guardar_en_sheet():
    nueva_fila = pd.DataFrame([{
        "saldo": st.session_state.saldo,
        "posiciones": json.dumps(st.session_state.pos),
        "historial": json.dumps(st.session_state.hist),
        "update": datetime.now().strftime("%Y-%m-%d %H:%M")
    }])
    try:
        # AQUÍ ESTÁ LA CLAVE: Pasar la URL literal en el create
        conn.create(spreadsheet=URL_PLANILLA, worksheet="Hoja1", data=nueva_fila)
        st.success("✅ ¡CONEXIÓN EXITOSA! Fila guardada en el Excel.")
    except Exception as e:
        st.error(f"Error crítico: {e}")

if st.button("🚀 PROBAR CONEXIÓN FINAL"):
    guardar_en_sheet()

st.divider()
st.subheader("📊 Monitor de Mercado")
st.info("Si el botón de arriba da verde, el bot ya puede operar solo.")
