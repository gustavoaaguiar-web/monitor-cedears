import streamlit as st
import yfinance as yf

# Fuerza el título y un mensaje simple antes de cargar nada pesado
st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    h1 { color: #111111; }
    </style>
    """, unsafe_allow_html=True)

st.title("🦅 SIMONS GG v12.2")
st.header("SISTEMA REINICIADO")

# Prueba de vida del servidor
st.write("Si puedes leer esto, el servidor está vivo.")

if st.button('DESBLOQUEAR PANTALLA'):
    st.cache_data.clear()
    st.rerun()

# Carga mínima para no saturar
try:
    precio = yf.download("AAPL", period="1d", interval="1m", progress=False)['Close'].iloc[-1]
    st.metric("Apple (Test Connection)", f"USD {precio:.2f}")
except:
    st.warning("Conectando con Yahoo Finance...")
