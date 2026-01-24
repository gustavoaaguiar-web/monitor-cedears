import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Simons-Arg Pro", page_icon="🦅")
st.title("🦅 Monitor Simons-Arg")
st.write("Seguimiento de CEDEARs y ADRs Argentinos")

# DICCIONARIO CON RATIOS Y SÍMBOLOS ALTERNATIVOS
activos_config = {
    'AAPL': {'ratio': 20, 'ba': 'AAPL.BA'},
    'TSLA': {'ratio': 15, 'ba': 'TSLA.BA'},
    'NVDA': {'ratio': 24, 'ba': 'NVDA.BA'},
    'MSFT': {'ratio': 30, 'ba': 'MSFT.BA'},
    'MELI': {'ratio': 120, 'ba': 'MELI.BA'},
    'GGAL': {'ratio': 10, 'ba': 'GGAL.BA'},
    'YPF':  {'ratio': 1,  'ba': 'YPFD.BA'}, # Símbolo corregido para YPF
    'PAM':  {'ratio': 25, 'ba': 'PAMP.BA'}, # Símbolo corregido para Pampa
    'BMA':  {'ratio': 10, 'ba': 'BMA.BA'},
    'CEPU': {'ratio': 10, 'ba': 'CEPU.BA'},
    'VIST': {'ratio': 0.2, 'ba': 'VIST.BA'}
}

def procesar_datos():
    filas = []
    lista_ccl = []
    
    for t, config in activos_config.items():
        try:
            # 1. Data USA
            u = yf.download(t, period="5d", interval="1m", progress=False, auto_adjust=True)
            if u.empty: continue
            val_usa = float(u['Close'].iloc[-1])
            
            # 2. Data Argentina (con reintento)
            a = yf.download(config['ba'], period="5d", interval="1m", progress=False, auto_adjust=True)
            
            if a.empty: # Si falla el principal, intentamos con el ticker básico
                a = yf.download(t + ".BA", period="5d", interval="1m", progress=False, auto_adjust=True)
            
            if not a.empty:
                val_arg = float(a['Close'].iloc[-1])
                ccl = (val_arg * config['ratio']) / val_usa
                lista_ccl.append(ccl)
            else:
                ccl = np.nan

            # 3. Clima (HMM)
            h = yf.download(t, period="3mo", interval="1d", progress=False)
            clima = "⚪"
            if not h.empty and len(h) > 10:
                rets = np.diff(np.log(h['Close'].values.flatten().reshape(-1, 1)), axis=0)
                model = GaussianHMM(n_components=3, random_state=42).fit(rets)
                estado = model.predict(rets)[-1]
                clima = "🟢" if estado == 0 else "🟡" if estado == 1 else "🔴"
            
            filas.append({"Activo": t, "Precio USD": round(val_usa, 2), "CCL": round(ccl, 2), "Clima": clima})
        except:
            continue
            
    df = pd.DataFrame(filas)
    if not df.empty:
        ccl_ref = np.median([x for x in lista_ccl if not np.isnan(x)])
        def definir_senal(row):
            if np.isnan(row['CCL']): return "⚖️ MANTENER"
            if row['CCL'] < ccl_ref * 0.995: return "🟢🐂 COMPRA"
            if row['CCL'] > ccl_ref * 1.005: return "🔴🐻 VENTA"
            return "⚖️ MANTENER"
        df['Señal'] = df.apply(definir_senal, axis=1)
        return df, ccl_ref
    return df, 0

if st.button('Actualizar Ahora'):
    st.rerun()

with st.spinner('Buscando a YPF y Pampa...'):
    data, ccl_avg = procesar_datos()

if not data.empty:
    st.metric("CCL Promedio", f"${ccl_avg:,.2f}")
    altura_total = (len(data) + 1) * 39
    st.dataframe(data, use_container_width=True, hide_index=True, height=altura_total)

st_autorefresh(interval=900000, key="datarefresh")
