import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Simons-Arg ADRs", page_icon="🦅")

st.title("🦅 Monitor Simons-Arg")
st.write("Seguimiento de CEDEARs y ADRs Argentinos")

# Diccionario con Ratios Actualizados
cedears = {
    'AAPL': 20, 'TSLA': 15, 'NVDA': 24, 'MSFT': 30, 'MELI': 120,
    'GGAL': 10, 'YPF': 2, 'PAM': 25, 'BMA': 10, 'CEPU': 10, 'VIST': 1
}

def procesar_datos():
    filas = []
    lista_ccl = []
    
    for t, ratio in cedears.items():
        try:
            # Descarga de datos
            u = yf.download(t, period="2d", interval="1m", progress=False, auto_adjust=True)
            a = yf.download(t + ".BA", period="2d", interval="1m", progress=False, auto_adjust=True)
            
            if u.empty or a.empty: continue
            
            val_usa = float(u['Close'].values.flatten()[-1])
            val_arg = float(a['Close'].values.flatten()[-1])
            ccl = (val_arg * ratio) / val_usa
            lista_ccl.append(ccl)
            
            # Modelo de Clima (HMM)
            h = yf.download(t, period="2mo", interval="1d", progress=False)
            rets = np.diff(np.log(h['Close'].values.flatten().reshape(-1, 1)), axis=0)
            model = GaussianHMM(n_components=3, random_state=42).fit(rets)
            estado = model.predict(rets)[-1]
            
            # 0: Calmo, 1: Incierto, 2: Tenso
            clima = "🟢" if estado == 0 else "🟡" if estado == 1 else "🔴"
            
            filas.append({"Activo": t, "CCL": round(ccl, 2), "Clima": clima})
        except:
            continue
            
    df = pd.DataFrame(filas)
    
    # Cálculo de señales basado en el promedio del mercado
    if not df.empty:
        ccl_mediana = df['CCL'].median()
        df['Señal'] = df['CCL'].apply(lambda x: "💎 OPORTUNIDAD" if x < (ccl_mediana * 0.995) else "⚖️ JUSTO")
        
    return df, ccl_mediana if not df.empty else 0

# Botón de actualización
if st.button('Actualizar Ahora'):
    st.rerun()

# Procesamiento y visualización
with st.spinner('Analizando mercado...'):
    data, ccl_avg = procesar_datos()

if not data.empty:
    # Mostrar CCL Promedio en un recuadro destacado
    st.metric("CCL Promedio del Panel", f"${ccl_avg:,.2f}")
    
    # Tabla principal
    st.dataframe(data, use_container_width=True, hide_index=True)
else:
    st.error("No se pudieron obtener datos. Verificá la conexión.")

# Auto-refresco cada 15 min
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=900000, key="datarefresh")
