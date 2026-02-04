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
st.set_page_config(page_title="Simons GG v01 - Performance", layout="wide")

if 'init' not in st.session_state:
    d = load()
    st.session_state.update({'saldo': d["s"], 'pos': d["p"], 'hist': d["h"], 'init': True})

v_i = sum(float(i['m']) for i in st.session_state.pos.values())
pat = st.session_state.saldo + v_i
rend_bot = ((pat / CAPITAL_INICIAL) - 1) * 100

# --- FUNCION BENCHMARK CORREGIDA ---
@st.cache_data(ttl=3600)
def get_benchmarks():
    indices = {"S&P 500": "SPY", "Merval (USD)": "^MERV"}
    bench_data = {}
    for name, ticker in indices.items():
        try:
            h = yf.download(ticker, period="10d", interval="1d", progress=False)
            if not h.empty and len(h) > 1:
                v = ((h.Close.iloc[-1] / h.Close.iloc[0]) - 1) * 100
                bench_data[name] = float(v)
        except: continue
    return bench_data

bench = get_benchmarks()

st.title("🦅 Simons GG v01")

# --- DASHBOARD PRINCIPAL ---
c1, c2, c3 = st.columns(3)
c1.metric("Patrimonio Total", f"AR$ {pat:,.2f}", f"{rend_bot:+.2f}%")
c2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Capital Inicial", f"AR$ {CAPITAL_INICIAL:,.2f}")

st.markdown("---")
st.subheader("📊 Comparativa de Rendimiento (7 Días Hábiles)")
b1, b2, b3 = st.columns(3)
b1.metric("Simons GG (Bot)", f"{rend_bot:+.2f}%")

# Validación para evitar el TypeError
if "S&P 500" in bench:
    b2.metric("S&P 500 (SPY)", f"{bench['S&P 500']:+.2f}%", f"{rend_bot - bench['S&P 500']:+.2f}% vs Bot")
else:
    b2.info("S&P 500: Cargando datos...")

if "Merval (USD)" in bench:
    b3.metric("Merval (Indice)", f"{bench['Merval (USD)']:+.2f}%", f"{rend_bot - bench['Merval (USD)']:+.2f}% vs Bot")
else:
    b3.info("Merval: Cargando datos...")

# --- MARKET DATA & LOGIC ---
cfg = {
    'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 
    'GGAL':10, 'YPF':1, 'BMA':10, 'CEPU':10, 'VIST':3,
    'GOOGL':58, 'AMZN':144, 'META':24, 'PAM':25
}

def get_data():
    filas, ccls = [], []
    for t, r in cfg.items():
        try:
            u = yf.download(t, period="2d", interval="1m", progress=False)
            ba_t = f"{t if t!='YPF' else 'YPFD'}.BA"
            a = yf.download(ba_t, period="2d", interval="1m", progress=False)
            if u.empty or a.empty: continue
            pu, pa = float(u.Close.iloc[-1]), float(a.Close.iloc[-1])
            ccl = (pa * r) / pu
            ccls.append(ccl)
            h = yf.download(t, period="3mo", interval="1d", progress=False)
            cl = "⚪"
            if not h.empty and len(h)>10:
                re = np.diff(np.log(h.Close.values.flatten().reshape(-1, 1)), axis=0)
                cl = "🟢" if GaussianHMM(n_components=3).fit(re).predict(re)[-1]==0 else "🔴"
            filas.append({"Activo": t, "USD": pu, "ARS": pa, "CCL": ccl, "Clima": cl})
        except: continue
    return pd.DataFrame(filas), np.median(ccls) if ccls else 0

if st.button('🔄 Sincronizar y Comparar'): st.rerun()

df, avg_ccl = get_data()

if not df.empty:
    st.metric("📊 CCL Promedio", f"AR$ {avg_ccl:,.2f}")
    df['Señal'] = df.apply(lambda r: "🟢 COMPRA" if r['CCL'] < avg_ccl * 0.995 and r['Clima'] != "🔴" else ("🔴 VENTA" if r['CCL'] > avg_ccl * 1.005 else "⚖️ MANTENER"), axis=1)
    
    upd = False
    for _, r in df.iterrows():
        tk = r['Activo']
        if r['Señal'] == "🟢 COMPRA" and st.session_state.saldo >= 1500000 and tk not in st.session_state.pos:
            st.session_state.saldo -= 1500000
            st.session_state.pos[tk] = {"m": 1500000, "pc": r['ARS']}
            upd = True
            enviar_alerta_mail(f"🟢 COMPRA: {tk}", f"Simons GG inició {tk} a {r['ARS']}")
        elif r['Señal'] == "🔴 VENTA" and tk in st.session_state.pos:
            p = st.session_state.pos.pop(tk)
            st.session_state.saldo += p['m'] * (r['ARS'] / p['pc'])
            upd = True
            enviar_alerta_mail(f"🔴 VENTA: {tk}", f"Simons GG cerró {tk}")
    if upd: save()
    
    st.subheader("🏢 Cartera Activa")
    if st.session_state.pos:
        p_l = [{"Activo":t, "Inversión":f"${p['m']:,.0f}", "Rendimiento":f"{((df[df.Activo==t].iloc[0]['ARS']/p['pc'])-1)*100:+.2f}%"} for t, p in st.session_state.pos.items() if t in df.Activo.values]
        st.table(pd.DataFrame(p_l))
    st.dataframe(df, use_container_width=True, hide_index=True)

st_autorefresh(interval=600000, key="simons_fix_refresh")
