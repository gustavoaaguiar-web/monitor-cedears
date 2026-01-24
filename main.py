import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# Configuración de la página
st.set_page_config(page_title="Simons-Arg Pro", page_icon="🦅")

st.title("🦅 Monitor Simons-Arg")
st.write("Seguimiento de CEDEARs y ADRs Argentinos")

# DICCIONARIO CALIBRADO
cedears = {
    'AAPL': 20, 'TSLA': 15, 'NVDA': 24, 'MSFT': 30, 'MELI': 120,
    'GGAL': 10, 'YPF': 1,  'PAM': 25, 'BMA': 10, 'CEPU': 10, 'VIST': 0.2
}

def procesar_datos():
    filas = []
    lista_ccl = []
    
    for t, ratio in cedears.items():
        try:
            # Descarga con más margen (5 días) para asegurar que no de None
            u = yf.download(t, period="5d", interval="1m", progress=False, auto_adjust=True)
            a = yf.download(t + ".BA", period="5d", interval="1m", progress=False, auto_adjust=True)
            
            if u.empty or a.empty: continue
            
            val_usa = float(u['Close'].iloc[-1])
            val_arg = float(a['Close'].iloc[-1])
            ccl = (val_arg * ratio) / val_usa
            lista_ccl.append(ccl)

            # Clima (HMM)
            h = yf.download(t, period="3mo", interval="1d", progress=False)
            if not h.empty and len(h) > 10:
                rets = np.diff(np.log(h['Close'].values.flatten().reshape(-1, 1)), axis=0)
                model = GaussianHMM(n_components=3, random_state=42).fit(rets)
                estado = model.predict(rets)[-1]
                clima = "🟢" if estado == 0 else "🟡" if estado == 1 else "🔴"
            else:
                clima = "⚪"
            
            filas.append({
                "Activo": t, 
                "Precio USD": round(val_usa, 2), 
                "CCL": round(ccl, 2), 
                "Clima": clima
            })
        except:
            continue
            
    df = pd.DataFrame(filas)
    
    if not df.empty:
        ccl_ref = np.median(lista_ccl)
        def definir_senal(row):
            # Toro Verde y Oso Rojo con emojis de colores
            if row['CCL'] < ccl_ref * 0.995: return "🟢🐂 COMPRA"
            if row['CCL'] > ccl_ref * 1.005: return "🔴🐻 VENTA"
            return "⚖️ MANTENER"
        df['Señal'] = df.apply(definir_senal, axis=1)
        return df, ccl_ref
    return df, 0

# Interfaz
if st.button('Actualizar Ahora'):
    st.rerun()

with st.spinner('Cargando panel completo...'):
    data, ccl_avg = procesar_datos()

if not data.empty:
    st.metric("CCL Promedio", f"${ccl_avg:,.2f}")
    
    # Altura para ver las 11 filas de una
    altura_total = (len(data) + 1) * 40
    st.dataframe(data, use_container_width=True, hide_index=True, height=altura_total)

st_autorefresh(interval=900000, key="datarefresh")
