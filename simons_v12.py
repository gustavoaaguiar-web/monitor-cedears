import streamlit as st
import yfinance as yf
import pandas as pd

# Título único para confirmar que GitHub tomó el cambio
st.set_page_config(page_title="Simons v12 Cloud", layout="wide")
st.title("🦅 Simons Arbitraje v12 (Cloud Edition)")

# Forzar limpieza de memoria
if st.sidebar.button('Limpiar Servidor'):
    st.cache_data.clear()
    st.rerun()

# Configuración de activos
cfg = {'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 'GGAL':10, 'YPF':1}

@st.cache_data(ttl=300) # Caché de 5 minutos para evitar baneos de Yahoo
def get_data():
    try:
        # Descarga simplificada
        tickers = list(cfg.keys())
        data = yf.download(tickers, period="1d", interval="15m", progress=False)['Close']
        if not data.empty:
            return data.iloc[-1]
        return None
    except:
        return None

st.subheader("Estado del Mercado")
precios = get_data()

if precios is not None:
    st.success("Sincronizado con éxito ✅")
    # Mostrar tabla simple
    df_ver = pd.DataFrame(precios).reset_index()
    df_ver.columns = ['Ticker', 'Precio USD']
    st.table(df_ver)
else:
    st.error("Esperando respuesta de Yahoo Finance...")

st.info("Si el título no dice 'v12', ve a Streamlit Cloud y dale a 'Reboot App'")

