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
    except Exception as e:
        st.error(f"Error enviando mail: {e}")

# --- DATABASE / PERSISTENCIA ---
DB = "simons_gg_v01.json"
CAPITAL_INICIAL = 30000000.0
GANANCIA_PREVIA = 0.05 
SALDO_ACTUAL = CAPITAL_INICIAL * (1 + GANANCIA_PREVIA)

def load():
    if os.path.exists(DB):
        try:
            with open(DB, "r") as f: return json.load(f)
        except: pass
    return {"s": SALDO_ACTUAL, "p": {}, "h": [{"fecha": datetime.now().strftime("%Y-%m-%d"), "t": SALDO_ACTUAL}]}

def save():
    v_a = sum(float(i['m']) for i in st.session_state.pos.values())
    tot = st.session_state.saldo + v_a
    hoy = datetime.now().strftime("%Y-%m-%d")
    if not st.session_state.hist or st.session_state.hist[-1]['fecha'] != hoy:
        st.session_state.hist.append({"fecha": hoy, "t": tot})
    else: 
        st.session_state.hist[-1]['t'] = tot
    with open(DB, "w") as f:
        json.dump({"s": st.session_state.saldo, "p": st.session_state.pos, "h": st.session_state.hist}, f)

# --- UI CONFIG ---
st.set_page_config(page_title="Simons GG v01 - 30M", layout="wide")

if 'init' not in st.session_state:
    d = load()
    st.session_state.update({'saldo': d["s"], 'pos': d["p"], 'hist': d["h"], 'init': True})

v_i = sum(float(i['m']) for i in st.session_state.pos.values())
pat = st.session_state.saldo + v_i

st.title("🦅 Simons GG v01: Gestión de Capital")
c1, c2, c3 = st.columns(3)
# Delta respecto a los 30M
c1.metric("Patrimonio Total", f"AR$ {pat:,.2f}", f"{((pat/CAPITAL_INICIAL)-1)*100:+.2f}%")
c2.metric("Efectivo en Cuenta", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Capital Inicial", f"AR$ {CAPITAL_INICIAL:,.2f}")

# --- MARKET DATA & RATIOS ---
# Incluye PAMP, VIST y los demás activos sumados hoy
cfg = {
    'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 
    'GGAL':10, 'YPF':1, 'BMA':10, 'CEPU':10,
    'GOOGL':58, 'AMZN':144, 'META':24, 'VIST':3, 'PAMP':25
}

def get_data():
    filas, ccls = [], []
    for t, r in cfg.items():
        try:
            # Manejo de tickers para Pampa y YPF
            t_usa = 'PAM' if t == 'PAMP' else t
            ba_ticker = f"{t if t!='YPF' else 'YPFD'}.BA"
            
            u = yf.download(t_usa, period="2d", interval="1m", progress=False, auto_adjust=True)
            a = yf.download(ba_ticker, period="2d", interval="1m", progress=False, auto_adjust=True)
            
            if u.empty or a.empty: continue
            
            pu, pa = float(u.Close.iloc[-1]), float(a.Close.iloc[-1])
            ccl = (pa * r) / pu
            
            # Filtro para evitar el CCL de $21 (solo valores realistas)
            if ccl > 500:
                ccls.append(ccl)
            
            h = yf.download(t_usa, period="3mo", interval="1d", progress=False)
            cl = "⚪"
            if not h.empty and len(h)>10:
                re = np.diff(np.log(h.Close.values.flatten().reshape(-1, 1)), axis=0)
                cl = "🟢" if GaussianHMM(n_components=3).fit(re).predict(re)[-1]==0 else "🔴"
            filas.append({"Activo": t, "USD": pu, "ARS": pa, "CCL": ccl, "Clima": cl})
        except: continue
    return pd.DataFrame(filas), np.median(ccls) if ccls else 0

if st.button('🔄 Sincronizar Mercado'): st.rerun()
df, avg_ccl = get_data()

# --- LÓGICA DE SEÑALES ---
if not df.empty:
    st.markdown(f"**CCL Promedio Detectado:** AR$ {avg_ccl:,.2f}")
    
    def get_s(r):
        if r['CCL'] < avg_ccl * 0.995 and r['Clima'] != "🔴": return "🟢 COMPRA"
        if r['CCL'] > avg_ccl * 1.005: return "🔴 VENTA"
        return "⚖️ MANTENER"
    
    df['Señal'] = df.apply(get_s, axis=1)
    
    upd = False
    MONTO_OPERACION = 1500000 
    
    for _, r in df.iterrows():
        tk = r['Activo']
        if r['Señal'] == "🟢 COMPRA" and st.session_state.saldo >= MONTO_OPERACION and tk not in st.session_state.pos:
            st.session_state.saldo -= MONTO_OPERACION
            st.session_state.pos[tk] = {"m": MONTO_OPERACION, "pc": r['ARS']}
            upd = True
            enviar_alerta_mail(f"🟢 COMPRA: {tk}", f"Simons GG inició {tk} a AR$ {r['ARS']:,.2f}")
            
        elif r['Señal'] == "🔴 VENTA" and tk in st.session_state.pos:
            p = st.session_state.pos.pop(tk)
            st.session_state.saldo += p['m'] * (r['ARS'] / p['pc'])
            upd = True
            enviar_alerta_mail(f"🔴 VENTA: {tk}", f"Simons GG cerró {tk} a AR$ {r['ARS']:,.2f}")
    
    if upd: save()

    # --- TABLA DE CARTERA ---
    st.subheader("💰 Cartera Activa")
    if st.session_state.pos:
        pos_list = []
        for t, p in st.session_state.pos.items():
            if t in df.Activo.values:
                act = df[df.Activo==t].iloc[0]['ARS']
                rend = ((act/p['pc'])-1)*100
                if rend > 100: rend = 0.0 # Fix para errores de carga
                pos_list.append({"Activo":t, "Inversión":f"${p['m']:,.0f}", "Rendimiento":f"{rend:+.2f}%"})
        if pos_list: st.table(pd.DataFrame(pos_list))

    # --- TABLA DE MONITOREO ---
    st.subheader("📊 Monitor de Arbitraje")
    st.dataframe(df[['Activo', 'USD', 'ARS', 'CCL', 'Clima', 'Señal']], use_container_width=True, hide_index=True)

st_autorefresh(interval=600000, key="simons_v1_stable")
