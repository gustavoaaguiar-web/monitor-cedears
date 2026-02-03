import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os, smtplib
from datetime import datetime
from email.message import EmailMessage

# --- CREDENCIALES ---
MI_MAIL = "gustavoaaguiar99@gmail.com"
CLAVE_APP = "zmupyxmxwbjsllsu" 

# --- CONFIGURACIÓN DE ACTIVOS Y RATIOS ---
# Ajustado VIST a 3 según tu broker y mercado real
cfg = {
    'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 
    'GGAL':10, 'YPF':1, 'BMA':10, 'CEPU':10,
    'GOOGL':58, 'AMZN':144, 'META':24, 
    'VIST': 3,  # <--- RATIO CORREGIDO
    'PAM':25
}

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
    except Exception: pass

# --- PERSISTENCIA ---
DB = "bot_v11_2.json"
def load():
    if os.path.exists(DB):
        try:
            with open(DB, "r") as f: return json.load(f)
        except: pass
    return {"s": 10000000.0, "p": {}, "h": [{"fecha": datetime.now().strftime("%Y-%m-%d"), "t": 10000000.0}]}

def save():
    v_a = sum(float(i['m']) for i in st.session_state.pos.values())
    tot = st.session_state.saldo + v_a
    with open(DB, "w") as f:
        json.dump({"s": st.session_state.saldo, "p": st.session_state.pos, "h": st.session_state.hist}, f)

st.set_page_config(page_title="Simons-Arg v11.2", layout="wide")

if 'init' not in st.session_state:
    d = load()
    st.session_state.update({'saldo': d["s"], 'pos': d["p"], 'hist': d["h"], 'init': True})

# --- LÓGICA DE DATOS ---
def get_data():
    filas, ccls = [], []
    for t, r in cfg.items():
        try:
            # Traemos data con un periodo un poco más largo para evitar el error de "No hay datos"
            u = yf.download(t, period="5d", interval="15m", progress=False)
            ba = f"{t if t!='YPF' else 'YPFD'}.BA"
            a = yf.download(ba, period="5d", interval="15m", progress=False)
            
            if u.empty or a.empty: continue
            
            pu, pa = float(u.Close.iloc[-1]), float(a.Close.iloc[-1])
            ccl = (pa * r) / pu
            ccls.append(ccl)
            
            # HMM Clima
            h = yf.download(t, period="3mo", interval="1d", progress=False)
            cl = "⚪"
            if len(h) > 15:
                re = np.diff(np.log(h.Close.values.flatten().reshape(-1, 1)), axis=0)
                cl = "🟢" if GaussianHMM(n_components=3).fit(re).predict(re)[-1] == 0 else "🔴"
            
            filas.append({"Activo": t, "USD": pu, "ARS": pa, "CCL": ccl, "Clima": cl})
        except: continue
    return pd.DataFrame(filas), np.median(ccls) if ccls else 0

st.title("🦅 Simons-Arg Pro v11.2")
if st.button('🔄 Sincronizar con Market Data'): st.rerun()

df, avg_ccl = get_data()

if not df.empty:
    st.metric("📊 CCL Promedio Mercado", f"AR$ {avg_ccl:,.2f}")
    
    def get_s(r):
        if r['CCL'] < avg_ccl * 0.992 and r['Clima'] != "🔴": return "🟢 COMPRA"
        if r['CCL'] > avg_ccl * 1.008: return "🔴 VENTA"
        return "⚖️ MANTENER"
    
    df['Señal'] = df.apply(get_s, axis=1)
    
    # Ejecución de señales y mails...
    for _, r in df.iterrows():
        tk = r['Activo']
        if r['Señal'] == "🟢 COMPRA" and st.session_state.saldo >= 500000 and tk not in st.session_state.pos:
            st.session_state.saldo -= 500000
            st.session_state.pos[tk] = {"m": 500000, "pc": r['ARS']}
            enviar_alerta_mail(f"🟢 COMPRA: {tk}", f"Precio ARS: {r['ARS']}\nCCL: {r['CCL']:.2f}")
        elif r['Señal'] == "🔴 VENTA" and tk in st.session_state.pos:
            p = st.session_state.pos.pop(tk)
            st.session_state.saldo += p['m'] * (r['ARS'] / p['pc'])
            enviar_alerta_mail(f"🔴 VENTA: {tk}", f"Salida en {tk} a ARS {r['ARS']}")
    
    save()
    st.dataframe(df, use_container_width=True)
else:
    st.warning("⚠️ No se pudieron obtener datos. Reintentando en la próxima actualización...")

st_autorefresh(interval=600000, key="bot_refresh")
