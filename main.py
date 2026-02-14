import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime

# URL ABSOLUTA
URL_DB = "https://docs.google.com/spreadsheets/d/19BvTkyD2ddrMsX1ghYGgnnq-BAfYJ_7qkNGqAsJel-M/edit?usp=drivesdk"

st.set_page_config(page_title="Simons GG v07", layout="wide")

# Forzamos la conexión pasando la URL desde el primer segundo
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        # En algunas versiones el parámetro es 'spreadsheet' y en otras no lleva nombre
        df = conn.read(spreadsheet=URL_DB, worksheet="Hoja1", ttl=0)
        if not df.empty:
            u = df.iloc[-1]
            return float(u['saldo']), json.loads(str(u['posiciones']).replace("'", '"')), json.loads(str(u['historial']).replace("'", '"'))
    except:
        return 33362112.69, {}, [{"fecha": "2026-02-14", "t": 33362112.69}]

if 'saldo' not in st.session_state:
    s, p, h = cargar_datos()
    st.session_state.saldo, st.session_state.pos, st.session_state.hist = s, p, h

st.title("🦅 Simons GG v07")

patrimonio = st.session_state.saldo + sum(float(v.get('m', 0)) for v in st.session_state.pos.values())
st.metric("Patrimonio Total", f"AR$ {patrimonio:,.2f}")

# --- BOTÓN DE ESCRITURA FORZADA ---
if st.button("🚀 SINCRONIZAR AHORA"):
    nueva_fila = pd.DataFrame([{
        "saldo": st.session_state.saldo,
        "posiciones": json.dumps(st.session_state.pos),
        "historial": json.dumps(st.session_state.hist),
        "update": datetime.now().strftime("%Y-%m-%d %H:%M")
    }])
    try:
        # Probamos el método de escritura directa
        conn.create(spreadsheet=URL_DB, data=nueva_fila)
        st.success("✅ ¡CONECTADO! La fila se grabó en el Excel.")
    except Exception as e:
        # Si falla el método anterior, probamos la alternativa de actualización
        try:
            conn.update(spreadsheet=URL_DB, data=nueva_fila)
            st.success("✅ ¡CONECTADO via Update!")
        except:
            st.error(f"Error de conexión: {e}")

st.divider()
st.info("Si el botón superior da error, revisaremos los permisos de 'Editor' del mail en el Excel.")
        
