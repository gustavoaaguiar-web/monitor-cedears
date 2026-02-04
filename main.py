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

# --- COMPARATIVA MERCADO (BENCHMARKS) ---
@st.cache_data(ttl=3600)
def get_benchmarks():
    res = {"S&P 500": 0.0, "Merval": 0.0}
    indices = {"S&P 500": "SPY", "Merval": "^MERV"}
    for name, t in indices.items():
        try:
            h = yf.download(t, period="5d", progress=False)
            if not h.empty:
                res[name] = ((h.Close.iloc[-1] / h.Close.iloc[0]) - 1) * 100
        except: pass
    return res

bench = get_benchmarks()

st.title("🦅 Simons GG v01: Gestión de Capital")
c1, c2, c3 = st.columns(3)
c1.metric("Patrimonio Total", f"AR$ {pat:,.2f}", f"{((pat/CAPITAL_INICIAL)-1)*100:+.2f}%")
c2.metric("Efectivo en Cuenta", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Capital de Origen", f"AR$ {CAPITAL_INICIAL:,.2f}")

st.markdown("---")
# Nueva sección de comparativa estable
col_b1, col_b2, col_b3 = st.columns(3)
col_b1.metric("Rendimiento Bot", f"{((pat/CAPITAL_INICIAL)-1)*100:+.2f}%")
col_b2.metric("S&P 500 (USD)", f"{bench['S&P 500']:+.2f}%")
col_b3.metric("Merval (ARS)", f"{bench['Merval']:+.2f}%")

# --- MARKET DATA & RATIOS CORREGIDOS ---
cfg = {
    'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 
    'GGAL':10, 'YPF':1, 'BMA':10, 'CEPU':10,
    'GOOGL':58, 'AMZN':144, 'META':24, 'VIST':3, 'PAMP':25 # Corregido PAM por PAMP
}

def get_data():
    filas, ccls = [], []
    for t, r in cfg.items():
        try:
            # Lógica de tickers para Yahoo Finance
            t_usa = 'PAM' if t == 'PAMP' else t
            ba_ticker = f"{t if t!='YPF' else 'YPFD'}.BA"
            
            u = yf.download(t_usa, period="2d", interval="1m", progress=False, auto_adjust=True)
            a = yf.download(ba_ticker, period="2d", interval="1m", progress=False, auto_adjust=True)
            
            if u.empty or a.empty: continue
            
            pu, pa = float(u.Close.iloc[-1]), float(a.Close.iloc[-1])
            ccl = (pa * r) / pu
            ccls.append(ccl)
            
            h = yf.download(t_usa, period="3mo", interval="1d", progress=False)
            cl = "⚪"
            if not h.empty and len(h)>10:
                re = np.diff(np.log(h.Close.values.flatten().reshape(-1, 1)), axis=0)
                cl = "🟢" if GaussianHMM(n_components=3).fit(re).predict(re)[-1]==0 else "🔴"
            filas.append({"Activo": t, "USD": pu, "ARS": pa, "CCL": ccl, "Clima": cl})
        except: continue
    return pd.DataFrame(filas), np.median(ccls) if ccls else 0

if st.button('🔄 Sincronizar con Bull Market'): st.rerun()
df, avg_ccl = get_data()

# --- LOGIC & MAIL TRIGGER ---
if not df.empty:
    st.metric("📊 CCL Promedio (Benchmark)", f"AR$ {avg_ccl:,.2f}")
    
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
            enviar_alerta_mail(f"🟢 COMPRA: {tk}", f"Simons GG inició posición en {tk} a AR$ {r['ARS']:,.2f}.\nCapital asignado: {MONTO_OPERACION}")
            
        elif r['Señal'] == "🔴 VENTA" and tk in st.session_state.pos:
            p = st.session_state.pos.pop(tk)
            st.session_state.saldo += p['m'] * (r['ARS'] / p['pc'])
            upd = True
            enviar_alerta_mail(f"🔴 VENTA: {tk}", f"Simons GG cerró {tk} a AR$ {r['ARS']:,.2f}.\nProfit del trade: {((r['ARS']/p['pc'])-1)*100:+.2f}%")
    
    if upd: save()

    st.subheader("🏢 Cartera Activa")
    if st.session_state.pos:
        pos_list = []
        for t, p in st.session_state.pos.items():
            if t in df.Activo.values:
                act = df[df.Activo==t].iloc[0]['ARS']
                rend = ((act/p['pc'])-1)*100
                # Fix visual para Tesla u otros errores de data
                if rend > 100: rend = 0.0
                pos_list.append({"Activo":t, "Inversión":f"${p['m']:,.0f}", "Rendimiento":f"{rend:+.2f}%"})
        if pos_list: st.table(pd.DataFrame(pos_list))

    st.subheader("📊 Monitor de Arbitraje")
    st.dataframe(df[['Activo', 'USD', 'ARS', 'CCL', 'Clima', 'Señal']], use_container_width=True, hide_index=True)

st_autorefresh(interval=600000, key="simons_30m_refresh")
