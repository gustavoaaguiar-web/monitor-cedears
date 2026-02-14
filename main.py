import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import yfinance as yf
import numpy as np
from hmmlearn.hmm import GaussianHMM
import json
from datetime import datetime

# --- CONFIGURACIÓN INICIAL ---
URL_DB = "https://docs.google.com/spreadsheets/d/19BvTkyD2ddrMsX1ghYGgnnq-BAfYJ_7qkNGqAsJel-M/edit?usp=drivesdk"
CAPITAL_INICIAL = 30000000.0

st.set_page_config(page_title="Simons GG v08.1", page_icon="🦅", layout="wide")

# Conexión con Google Sheets (usa los Secrets ya validados)
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos():
    try:
        df = conn.read(spreadsheet=URL_DB, worksheet="Hoja1", ttl=0)
        if not df.empty:
            u = df.iloc[-1]
            return (
                float(u['saldo']), 
                json.loads(str(u['posiciones']).replace("'", '"')), 
                json.loads(str(u['historial']).replace("'", '"'))
            )
    except:
        # Valores por defecto si la base está vacía
        return 33362112.69, {}, [{"fecha": "2026-02-14", "t": 33362112.69}]

if 'saldo' not in st.session_state:
    s, p, h = cargar_datos()
    st.session_state.update({'saldo': s, 'pos': p, 'hist': h})

# --- INTERFAZ DE PATRIMONIO ---
st.title("🦅 Simons GG v3.0 🤑")

patrimonio_total = st.session_state.saldo + sum(float(i.get('m', 0)) for i in st.session_state.pos.values())
rendimiento_h = ((patrimonio_total / CAPITAL_INICIAL) - 1) * 100

c1, c2, c3 = st.columns(3)
c1.metric(
    label="Patrimonio Total", 
    value=f"AR$ {patrimonio_total:,.2f}", 
    delta=f"{rendimiento_h:+.2f}% vs Inicial",
    delta_color="normal"
)
c2.metric("Efectivo disponible", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Ticket sugerido (8%)", f"AR$ {(patrimonio_total * 0.08):,.2f}")

# --- MONITOR DE MERCADO (14 ACTIVOS) ---
st.subheader("📊 Monitor de Arbitraje y Clima HMM")

activos = {
    'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 
    'GGAL':10, 'YPF':1, 'BMA':10, 'CEPU':10, 'GOOGL':58, 
    'AMZN':144, 'META':24, 'VIST':3, 'PAM':25
}

@st.cache_data(ttl=300)
def fetch_market():
    datos, ccls = [], []
    for t, r in activos.items():
        try:
            # Selección de Tickers (ARS vs USD)
            tk_ars = "YPFD.BA" if t=='YPF' else ("PAMP.BA" if t=='PAM' else f"{t}.BA")
            h_usd = yf.download(t, period="3mo", interval="1d", progress=False)
            h_ars = yf.download(tk_ars, period="1d", interval="1m", progress=False)
            
            p_usd = float(h_usd.Close.iloc[-1])
            p_ars = float(h_ars.Close.iloc[-1])
            ccl_spot = (p_ars * r) / p_usd
            ccls.append(ccl_spot)
            
            # Modelo HMM para Clima de Mercado
            ret = np.diff(np.log(h_usd.Close.values.flatten().reshape(-1, 1)), axis=0)
            model = GaussianHMM(n_components=3, random_state=42).fit(ret)
            clima = "🟢" if model.predict(ret)[-1] == 0 else "🔴"
            
            datos.append({"Activo": t, "USD": p_usd, "ARS": p_ars, "CCL": ccl_spot, "Clima": clima})
        except: continue
    
    df = pd.DataFrame(datos)
    if not df.empty:
        ccl_mediano = np.median(ccls)
        def set_label(row):
            if row['CCL'] < ccl_mediano * 0.994 and row['Clima'] == "🟢": return "🟢 COMPRA"
            if row['CCL'] > ccl_mediano * 1.006: return "🔴 VENTA"
            return "⚖️ MANTENER"
        df['Señal'] = df.apply(set_label, axis=1)
    return df, np.median(ccls) if ccls else 0

df_m, ccl_m = fetch_market()
st.caption(f"CCL Mediano del mercado: ${ccl_m:.2f}")
st.dataframe(df_m, use_container_width=True, hide_index=True)

# --- PANEL DE CONTROL ---
st.divider()
col_btn1, col_btn2 = st.columns([1, 4])

with col_btn1:
    if st.button("💾 GUARDAR EN EXCEL"):
        nueva_fila = pd.DataFrame([{
            "saldo": st.session_state.saldo,
            "posiciones": json.dumps(st.session_state.pos),
            "historial": json.dumps(st.session_state.hist),
            "update": datetime.now().strftime("%Y-%m-%d %H:%M")
        }])
        try:
            # Método validado vía Update
            conn.update(spreadsheet=URL_DB, data=nueva_fila)
            st.success("Sincronizado!")
            st.balloons()
        except:
            st.error("Error de conexión.")

with col_btn2:
    st.info("Sistema listo. Las señales se actualizan cada 5 minutos.")
