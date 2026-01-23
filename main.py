import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
import time

# Configuración de la página para celulares
st.set_page_config(page_title="Simons-Arg Mobile", page_icon="🦅")

st.title("🦅 Monitor Simons-Arg")
st.write("Actualización automática cada 15 min")

# Ratios y configuración
cedears = {'AAPL': 20, 'TSLA': 15, 'NVDA': 24, 'MSFT': 30, 'MELI': 120}

def procesar_datos():
    filas = []
    for t, ratio in cedears.items():
        try:
            # Bajamos data para el CCL y el Clima
            u = yf.download(t, period="2d", interval="1m", progress=False, auto_adjust=True)
            a = yf.download(t + ".BA", period="2d", interval="1m", progress=False, auto_adjust=True)
            
            val_usa = float(u['Close'].values.flatten()[-1])
            val_arg = float(a['Close'].values.flatten()[-1])
            ccl = (val_arg * ratio) / val_usa
            
            # Semáforo simplificado (HMM)
            # Para la app usamos 1 mes de data para que sea rápido
            h = yf.download(t, period="1mo", interval="1d", progress=False)
            rets = np.diff(np.log(h['Close'].values.flatten().reshape(-1, 1)), axis=0)
            model = GaussianHMM(n_components=3).fit(rets)
            estado = model.predict(rets)[-1]
            
            clima = "🟢" if estado == 0 else "🟡" if estado == 1 else "🔴"
            evalu = "💎 OPORTUNIDAD" if ccl < 1515 else "⚖️ JUSTO"
            
            filas.append({"Activo": t, "CCL": round(ccl,2), "Clima": clima, "Señal": evalu})
        except:
            continue
    return pd.DataFrame(filas)

# Botón manual y visualización
if st.button('Actualizar Ahora'):
    st.rerun()

data = procesar_datos()
st.dataframe(data, use_container_width=True)

# Lógica de auto-refresco (900000ms = 15min)
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=900000, key="datarefresh")
