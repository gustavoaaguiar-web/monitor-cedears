import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Conexión ultra simple
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🦅 Simons GG v02 - Test")

# Intentamos escribir una fila de prueba
if st.button("🚀 PROBAR CONEXIÓN"):
    try:
        url = st.secrets["spreadsheet"]
        # Creamos una fila de prueba
        df_test = pd.DataFrame([{"saldo": 33362112.69, "posiciones": "{}", "historial": "[]", "update": "TEST"}])
        conn.create(spreadsheet=url, worksheet="Hoja1", data=df_test)
        st.success("¡FUNCIONA! Se escribió en el Excel.")
    except Exception as e:
        st.error(f"Error: {e}")
        
