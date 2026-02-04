import streamlit as st
import yfinance as yf
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

# --- DATABASE / PERSISTENCIA ---
DB = "bot_v11_final.json"
CAPITAL_INICIAL = 30000000.0

def load():
    if os.path.exists(DB):
        try:
            with open(DB, "r") as f: return json.load(f)
        except: pass
    return {"s": CAPITAL_INICIAL, "p": {}, "h": []}

def save():
    with open(DB, "w") as f:
        json.dump({"s": st.session_state.saldo, "p": st.session_state.pos}, f)

# --- UI CONFIG ---
st.set_page_config(page_title="Simons-Arg v11.2 Pro", layout="wide")

if 'init' not in st.session_state:
    d = load()
    st.session_state.update({'saldo': d["s"], 'pos': d["p"], 'init': True})

# --- TICKERS ---
cfg = {
    'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 
    'GGAL':10, 'YPF':1, 'BMA':10, 'CEPU':10, 'VIST':3,
    'GOOGL':58, 'AMZN':144, 'META':24, 'PAMP':25 
}

# --- DESCARGA OPTIMIZADA (Aquí está el truco para que no se tilde) ---
@st.cache_data(ttl=60)
def get_fast_data():
    # Creamos listas de tickers para descargar todo en 2 bloques
    t_usa = [t if t != 'PAMP' else 'PAM' for t in cfg.keys()]
    t_ars = [(f"{t}.BA" if t != 'YPF' else 'YPFD.BA') for t in cfg.keys()]
    
    try:
        # Descarga masiva (Batch download)
        d_usa = yf.download(t_usa, period="2d", interval="5m", progress=False)['Close']
        d_ars = yf.download(t_ars, period="2d", interval="5m", progress=False)['Close']
        
        res, ccls = [], []
        for t, r in cfg.items():
            u_tk = 'PAM' if t == 'PAMP' else t
            a_tk = f"{t}.BA" if t != 'YPF' else 'YPFD.BA'
            
            if u_tk in d_usa.columns and a_tk in d_ars.columns:
                p_u = d_usa[u_tk].iloc[-1]
                p_a = d_ars[a_tk].iloc[-1]
                
                if not np.isnan(p_u) and not np.isnan(p_a):
                    ccl_val = (p_a * r) / p_u
                    if 1000 < ccl_val < 2000: ccls.append(ccl_val)
                    
                    clima = "🟢" if p_u > d_usa[u_tk].iloc[0] else "🔴"
                    res.append({"Activo": t, "USD": p_u, "ARS": p_a, "CCL": ccl_val, "Clima": clima})
        
        return pd.DataFrame(res), np.median(ccls) if ccls else 0
    except:
        return pd.DataFrame(), 0

# --- LÓGICA PRINCIPAL ---
st.title("🦅 Simons-Arg v11.2 Pro")

with st.spinner('Sincronizando con mercado...'):
    df, avg_ccl = get_fast_data()

# Patrimonio
val_cartera = 0
for t, p in st.session_state.pos.items():
    if not df.empty and t in df.Activo.values:
        actual = df[df.Activo==t].iloc[0]['ARS']
        val_cartera += p['m'] * (actual / p['pc'])
    else: val_cartera += p['m']

pat = st.session_state.saldo + val_cartera

# Métricas
m1, m2, m3 = st.columns(3)
m1.metric("Patrimonio Total", f"AR$ {pat:,.0f}", f"{((pat/CAPITAL_INICIAL)-1)*100:+.2f}%")
m2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.2f}")
m3.metric("CCL Promedio", f"AR$ {avg_ccl:,.2f}")

if not df.empty:
    def get_s(r):
        if r['CCL'] < avg_ccl * 0.995: return "🟢 COMPRA"
        if r['CCL'] > avg_ccl * 1.005: return "🔴 VENTA"
        return "⚖️ MANTENER"
    
    df['Señal'] = df.apply(get_s, axis=1)
    
    # Trading Automático
    upd = False
    for _, r in df.iterrows():
        tk = r['Activo']
        if r['Señal'] == "🟢 COMPRA" and st.session_state.saldo >= 1500000 and tk not in st.session_state.pos:
            st.session_state.saldo -= 1500000
            st.session_state.pos[tk] = {"m": 1500000, "pc": r['ARS']}
            enviar_alerta_mail(f"🟢 COMPRA: {tk}", f"Entrada en {tk} a {r['ARS']}")
            upd = True
        elif r['Señal'] == "🔴 VENTA" and tk in st.session_state.pos:
            p = st.session_state.pos.pop(tk)
            st.session_state.saldo += p['m'] * (r['ARS'] / p['pc'])
            enviar_alerta_mail(f"🔴 VENTA: {tk}", f"Salida en {tk} a {r['ARS']}")
            upd = True
    if upd: save()

    st.subheader("📊 Monitor de Arbitraje")
    st.dataframe(df, use_container_width=True, hide_index=True)

st_autorefresh(interval=600000, key="refresh_v11")
