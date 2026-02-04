import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os, smtplib
from datetime import datetime
from email.message import EmailMessage

# --- CONFIGURACIÓN DE CORREO ---
MI_MAIL = "gustavoaaguiar99@gmail.com"
CLAVE_APP = "zmupyxmxwbjsllsu" 

def enviar_alerta_mail(asunto, cuerpo):
    msg = EmailMessage()
    msg.set_content(cuerpo)
    msg['Subject'] = asunto
    msg['From'] = MI_MAIL
    msg['To'] = MI_MAIL
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(MI_MAIL, CLAVE_APP)
        server.send_message(msg)
        server.quit()
    except: pass

# --- DATABASE ---
DB = "bot_v11_final.json"
CAPITAL_INICIAL = 30000000.0 # Ajustado a tus 30M

def load():
    if os.path.exists(DB):
        try:
            with open(DB, "r") as f: return json.load(f)
        except: pass
    return {"s": CAPITAL_INICIAL, "p": {}, "h": []}

def save():
    with open(DB, "w") as f:
        json.dump({"s": st.session_state.saldo, "p": st.session_state.pos}, f)

st.set_page_config(page_title="Simons-Arg v11 Pro", layout="wide")

if 'init' not in st.session_state:
    d = load()
    st.session_state.update({'saldo': d["s"], 'pos': d["p"], 'init': True})

# --- OPTIMIZACIÓN DE TICKERS ---
cfg = {
    'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 
    'GGAL':10, 'YPF':1, 'BMA':10, 'CEPU':10, 'VIST':3,
    'GOOGL':58, 'AMZN':144, 'META':24, 'PAMP':25 
}

# --- DESCARGA MASIVA (Evita que se tilde) ---
@st.cache_data(ttl=60)
def get_market_data():
    filas, ccls = [], []
    # Descargamos todo de una sola vez para evitar bloqueos
    tickers_usa = [t if t != 'PAMP' else 'PAM' for t in cfg.keys()]
    tickers_ars = [(f"{t}.BA" if t != 'YPF' else 'YPFD.BA') for t in cfg.keys()]
    
    try:
        data_usa = yf.download(tickers_usa, period="2d", interval="5m", progress=False)['Close']
        data_ars = yf.download(tickers_ars, period="2d", interval="5m", progress=False)['Close']
        
        for t, r in cfg.items():
            t_u = 'PAM' if t == 'PAMP' else t
            t_a = f"{t}.BA" if t != 'YPF' else 'YPFD.BA'
            
            if t_u in data_usa.columns and t_a in data_ars.columns:
                pu = float(data_usa[t_u].iloc[-1])
                pa = float(data_ars[t_a].iloc[-1])
                
                if pu > 0 and pa > 0:
                    ccl_i = (pa * r) / pu
                    if 1000 < ccl_i < 2000: ccls.append(ccl_i)
                    
                    # Clima simplificado (Precio vs Apertura) para no colapsar con HMM cada minuto
                    clima = "🟢" if pu > data_usa[t_u].iloc[0] else "🔴"
                    filas.append({"Activo": t, "USD": pu, "ARS": pa, "CCL": ccl_i, "Clima": clima})
    except: pass
    
    df = pd.DataFrame(filas)
    avg = np.median(ccls) if ccls else 0
    return df, avg

st.title("🦅 Simons-Arg v11 Pro")

with st.spinner('Actualizando precios...'):
    df, avg_ccl = get_market_data()

# --- PATRIMONIO ---
val_cartera = 0
for t, p in st.session_state.pos.items():
    if not df.empty and t in df.Activo.values:
        actual = df[df.Activo==t].iloc[0]['ARS']
        val_cartera += p['m'] * (actual / p['pc'])
    else: val_cartera += p['m']

pat = st.session_state.saldo + val_cartera
c1, c2, c3 = st.columns(3)
c1.metric("Patrimonio", f"AR$ {pat:,.0f}", f"{((pat/CAPITAL_INICIAL)-1)*100:+.2f}%")
c2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.0f}")
c3.metric("CCL Promedio", f"AR$ {avg_ccl:,.2f}")

if not df.empty and avg_ccl > 0:
    def get_s(r):
        if r['CCL'] < avg_ccl * 0.995: return "🟢 COMPRA"
        if r['CCL'] > avg_ccl * 1.005: return "🔴 VENTA"
        return "⚖️ MANTENER"
    
    df['Señal'] = df.apply(get_s, axis=1)
    
    # Lógica de Trading
    upd = False
    for _, r in df.iterrows():
        tk = r['Activo']
        if r['Señal'] == "🟢 COMPRA" and st.session_state.saldo >= 1500000 and tk not in st.session_state.pos:
            st.session_state.saldo -= 1500000
            st.session_state.pos[tk] = {"m": 1500000, "pc": r['ARS']}
            enviar_alerta_mail(f"🟢 COMPRA: {tk}", f"Entrada en {tk} a AR$ {r['ARS']}")
            upd = True
        elif r['Señal'] == "🔴 VENTA" and tk in st.session_state.pos:
            p = st.session_state.pos.pop(tk)
            st.session_state.saldo += p['m'] * (r['ARS'] / p['pc'])
            enviar_alerta_mail(f"🔴 VENTA: {tk}", f"Salida en {tk} a AR$ {r['ARS']}")
            upd = True
    if upd: save()

    st.subheader("🏢 Monitor de Mercado")
    st.dataframe(df, use_container_width=True, hide_index=True)

st_autorefresh(interval=600000, key="v11_refresh")
