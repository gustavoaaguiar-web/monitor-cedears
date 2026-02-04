import streamlit as st
import yfinance as yf
import pandas as pd

# CONFIGURACIÓN INICIAL
st.set_page_config(page_title="Simons v12", layout="wide")

# TÍTULO BIEN GRANDE PARA CONFIRMAR
st.title("🦅 SIMONS GG v12.1")
st.write("---")
st.success("¡Si ves esto, el sistema se actualizó correctamente!")

# BOTÓN DE EMERGENCIA
if st.sidebar.button('REINICIAR MEMORIA'):
    st.cache_data.clear()
    st.rerun()

# CARGA DE DATOS SIMPLE (Muestra si hay conexión)
try:
    with st.spinner('Conectando con el mercado...'):
        # Solo bajamos 3 tickers para que sea instantáneo
        data = yf.download(['AAPL', 'GGAL', 'YPF'], period="1d", interval="15m", progress=False)['Close']
        if not data.empty:
            st.write("### Precios en Vivo (USD)")
            st.table(data.iloc[-1])
except Exception as e:
    st.error(f"Error de conexión: {e}")

st.info("Paso siguiente: Una vez que veas esto, agregaremos el motor de arbitraje.")

