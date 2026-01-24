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

# DICCIONARIO CORREGIDO (Ratios ADR vs Local)
cedears = {
    'AAPL': 20, 'TSLA': 15, 'NVDA': 24, 'MSFT': 30, 'MELI': 120, # CEDEARs
    'GGAL': 10, 'YPF': 1,  'PAM': 25, 'BMA': 10, 'CEPU': 10, 'VIST': 1  # ADRs Corregidos
}

def procesar_datos():
    filas = []
    lista_ccl = []
    
    for t, ratio in cedears.items():
        try:
            # Datos USA
            u = yf.download(t, period="2d", interval="1m", progress=False, auto_adjust=True)
            if u.empty: continue
            val_usa = float(u['Close'].values.flatten()[-1])
            
            # Datos Argentina
            a = yf.download(t + ".BA", period="2d", interval="1m", progress=False, auto_adjust=True)
            if not a.empty:
                val_arg = float(a['Close'].values.flatten()[-1])
                ccl = (val_arg * ratio) / val_usa
                lista_ccl.append(ccl)
            else:
                ccl = np.nan

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
        ccl_ref = df['CCL'].median()
        def definir_senal(row):
            # Lógica de señales con Toros Verdes y Osos Rojos
            if row['CCL'] < ccl_ref * 0.99: return "🟢🐂 COMPRA"
            if row['CCL'] > ccl_ref * 1.01: return "🔴🐻 VENTA"
            return "⚖️ MANTENER"
        df['Señal'] = df.apply(definir_senal, axis=1)
        return df, ccl_ref
    return df, 0

# Botón y Proceso
if st.button('Actualizar Ahora'):
    st.rerun()

with st.spinner('Analizando Toros y Osos...'):
    data, ccl_avg = procesar_datos()

if not data.empty:
    st.metric("CCL Promedio", f"${ccl_avg:,.2f}")
    
    # Altura dinámica para ver todas las filas
    altura_tabla = (len(data) + 1) * 38 
    st.dataframe(data, use_container_width=True, hide_index=True, height=altura_tabla)

st_autorefresh(interval=900000, key="datarefresh")
