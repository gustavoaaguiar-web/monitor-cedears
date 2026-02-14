import streamlit as st
import pandas as pd
import json
from datetime import datetime

# --- CONFIGURACIÓN ---
SHEET_ID = "19BvTkyD2ddrMsX1ghYGgnnq-BAfYJ_7qkNGqAsJel-M"
URL_DATA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=Hoja1"

if 'saldo' not in st.session_state:
    try:
        df_sheet = pd.read_csv(URL_DATA)
        if not df_sheet.empty:
            u = df_sheet.iloc[-1]
            st.session_state.saldo = float(u['saldo'])
            st.session_state.pos = json.loads(str(u['posiciones']).replace("'", '"'))
            # Intentamos cargar el historial si existe la columna
            if 'historial' in u:
                st.session_state.hist = json.loads(str(u['historial']).replace("'", '"'))
            else:
                st.session_state.hist = [{"fecha": "2026-01-01", "t": 30000000.0}]
    except:
        st.session_state.saldo = 33362112.69
        st.session_state.pos = {}
        st.session_state.hist = [{"fecha": "2026-02-14", "t": 33362112.69}]

# --- INTERFAZ ---
st.title("🦅 Simons GG v04.1")

# --- BOTÓN DE RESPALDO CON HISTORIAL ---
with st.expander("💾 GENERAR FILA PARA EXCEL"):
    st.write("Copia esto y pegalo en la siguiente fila vacía de tu Sheets:")
    
    # Agregamos el historial a la fila
    fila_completa = {
        "saldo": st.session_state.saldo,
        "posiciones": json.dumps(st.session_state.pos),
        "historial": json.dumps(st.session_state.hist),
        "update": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    texto_para_copy = f"{fila_completa['saldo']}, '{fila_completa['posiciones']}', '{fila_completa['historial']}', {fila_completa['update']}"
    st.code(texto_para_copy, language="text")

# (Aquí sigue el resto de tu monitor de acciones...)
