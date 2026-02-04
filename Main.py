import streamlit as st
import yfinance as yf
from streamlit_autorefresh import st_autorefresh

# Cambio de título radical para confirmar que refrescó
st.set_page_config(page_title="SIMONS RESET", layout="wide")
st.title("⚡ Simons GG: Modo Recuperación")

# 1. Botón para forzar limpieza manual
if st.button('Limpiar Caché y Reiniciar'):
    st.cache_data.clear()
    st.rerun()

st.info("Si ves este mensaje, la app ya NO está tildada.")

# 2. Prueba de conexión mínima (Solo 1 activo para no saturar)
try:
    with st.spinner('Probando conexión con Yahoo...'):
        data = yf.download("AAPL", period="1d", interval="1m", progress=False)
        if not data.empty:
            st.success("Conexión con Yahoo: FUNCIONANDO ✅")
            st.metric("Apple USD", f"{data['Close'].iloc[-1]:.2f}")
        else:
            st.warning("Yahoo devolvió datos vacíos. Espera 2 minutos.")
except Exception as e:
    st.error(f"Error técnico: {e}")

# 3. Auto-refresh más lento para evitar bloqueos (cada 5 min)
st_autorefresh(interval=300000, key="reset_refresh")
