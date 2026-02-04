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
    except: pass # Silencioso para no romper la app

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
    return {"s": SALDO_ACTUAL, "p": {}, "h": []}

def save():
    v_a = sum(float(i['m']) for i in st.session_state.pos.values())
    with open(DB, "w") as f:
        json.dump({"s": st.session_state.saldo, "p": st.session_state.pos, "h": []}, f)

# --- UI CONFIG ---
st.set_page_config(page_title="Simons GG v01.7", layout="wide")

if 'init' not in st.session_state:
    d = load()
    st.session_state.update({'saldo': d["s"], 'pos': d["p"], 'init': True})

# --- BENCHMARKS TOTALMENTE SEGUROS (SOLUCIÓN AL ERROR TYPEERROR) ---
@st.cache_data(ttl=3600)
def get_safe_benchmarks():
    data = {"sp": 0.0, "mer": 0.0}
    try:
        s = yf.download("SPY", period="5d", progress=False)
        if not s.empty and len(s) > 1:
            data["sp"] = float(((s['Close'].iloc[-1] / s['Close'].iloc[0]) - 1) * 100)
        
        m = yf.download("^MERV", period="5d", progress=False)
        if not m.empty and len(m) > 1:
            data["mer"] = float(((m['Close'].iloc[-1] / m['Close'].iloc[0]) - 1) * 100)
    except: pass
    return data

bench = get_safe_benchmarks()

# --- MARKET DATA & RATIOS ---
cfg = {
    'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 
    'GGAL':10, 'YPF':1, 'BMA':10, 'CEPU':10, 'VIST':3,
    'GOOGL':58, 'AMZN':144, 'META':24, 'PAMP':25 
}

def get_market():
    filas, ccls = [], []
    for t, r in cfg.items():
        try:
            t_usa = 'PAM' if t == 'PAMP' else t
            t_ars = 'YPFD.BA' if t == 'YPF' else f"{t}.BA"
            u = yf.download(t_usa, period="2d", interval="5m", progress=False)
            a = yf.download(t_ars, period="2d", interval="5m", progress=False)
            
            if u.empty or a.empty: continue
            
            pu, pa = float(u.Close.iloc[-1]), float(a.Close.iloc[-1])
            ccl = (pa * r) / pu
            
            # Filtro para CCL coherente (evita el error de los $21)
            if 1000 < ccl < 2000: 
                ccls.append(ccl)
            
            clima = "🟢" if pu > u.Close.iloc[0] else "🔴"
            filas.append({"Activo": t, "USD": pu, "ARS": pa, "CCL": ccl, "Clima": clima})
        except: continue
    return pd.DataFrame(filas), np.median(ccls) if ccls else 1490.0

df, avg_ccl = get_market()

# --- CÁLCULO PATRIMONIO ---
val_cartera = 0
for t, p in st.session_state.pos.items():
    if not df.empty and t in df.Activo.values:
        actual = df[df.Activo==t].iloc[0]['ARS']
        # Si el precio local saltó más del 50%, es un error de Yahoo, usamos precio de compra
        if actual / p['pc'] > 1.5: actual = p['pc']
        val_cartera += p['m'] * (actual / p['pc'])
    else: val_cartera += p['m']

pat = st.session_state.saldo + val_cartera
rend_bot = ((pat / CAPITAL_INICIAL) - 1) * 100

# --- INTERFAZ ---
st.title("🦅 Simons GG v01.7")

c1, c2, c3 = st.columns(3)
c1.metric("Patrimonio Total", f"AR$ {pat:,.0f}", f"{rend_bot:+.2f}%")
c2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.0f}")
c3.metric("CCL Promedio", f"AR$ {avg_ccl:,.2f}")

st.markdown("---")
st.subheader("📊 Comparativa de Rendimiento")
b1, b2, b3 = st.columns(3)
b1.metric("Simons Bot", f"{rend_bot:+.2f}%")
# Aquí está el fix definitivo para el error de la línea 95:
b2.metric("S&P 500 (USD)", f"{bench['sp']:+.2f}%")
b3.metric("Merval (ARS)", f"{bench['mer']:+.2f}%")

if not df.empty:
    def get_s(r):
        if r['CCL'] < avg_ccl * 0.995: return "🟢 COMPRA"
        if r['CCL'] > avg_ccl * 1.005: return "🔴 VENTA"
        return "⚖️ MANTENER"
    
    df['Señal'] = df.apply(get_s, axis=1)
    
    st.subheader("🏢 Monitor de Arbitraje")
    st.dataframe(df[['Activo', 'USD', 'ARS', 'CCL', 'Clima', 'Señal']], use_container_width=True, hide_index=True)

    # --- LÓGICA DE TRADING AUTOMÁTICO ---
    upd = False
    MONTO_OP = 1500000
    for _, r in df.iterrows():
        tk = r['Activo']
        if r['Señal'] == "🟢 COMPRA" and st.session_state.saldo >= MONTO_OP and tk not in st.session_state.pos:
            st.session_state.saldo -= MONTO_OP
            st.session_state.pos[tk] = {"m": MONTO_OP, "pc": r['ARS']}
            enviar_alerta_mail(f"🟢 COMPRA: {tk}", f"Entrada en {tk} a AR$ {r['ARS']}")
            upd = True
        elif r['Señal'] == "🔴 VENTA" and tk in st.session_state.pos:
            p = st.session_state.pos.pop(tk)
            st.session_state.saldo += p['m'] * (r['ARS'] / p['pc'])
            enviar_alerta_mail(f"🔴 VENTA: {tk}", f"Salida en {tk} a AR$ {r['ARS']}")
            upd = True
    if upd: save()

st_autorefresh(interval=600000, key="refresh_v7")
