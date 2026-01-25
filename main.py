import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os
from datetime import datetime

# --- DATABASE ---
DB = "bot_v10.json"
def load():
    if os.path.exists(DB):
        try:
            with open(DB, "r") as f: return json.load(f)
        except: pass
    return {"s": 10000000.0, "p": {}, "h": [{"fecha": datetime.now().strftime("%Y-%m-%d"), "t": 10000000.0}]}

def save():
    v_a = sum(i['m'] for i in st.session_state.pos.values())
    tot = st.session_state.saldo + v_a
    hoy = datetime.now().strftime("%Y-%m-%d")
    if not st.session_state.hist or st.session_state.hist[-1]['fecha'] != hoy:
        st.session_state.hist.append({"fecha": hoy, "t": tot})
    else: st.session_state.hist[-1]['t'] = tot
    with open(DB, "w") as f:
        json.dump({"s": st.session_state.saldo, "p": st.session_state.pos, "h": st.session_state.hist}, f)

# --- UI ---
st.set_page_config(page_title="Simons-Arg", layout="wide")
if 'init' not in st.session_state:
    d = load()
    st.session_state.update({'saldo': d["s"], 'pos': d["p"], 'hist': d["h"], 'init': True})

v_i = sum(i['m'] for i in st.session_state.pos.values())
pat = st.session_state.saldo + v_i

st.title("🦅 Simons-Arg Pro")
c1, c2, c3 = st.columns(3)
c1.metric("Patrimonio Total", f"AR$ {pat:,.2f}", f"{((pat/10000000.0)-1)*100:+.2f}%")
c2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Capital Inicial", "AR$ 10,000,000.00")

st.subheader("📈 Evolución de Cartera")
st.line_chart(pd.DataFrame(st.session_state.hist).set_index("fecha"))

# --- MARKET ---
cfg = {'AAPL':20,'TSLA':15,'NVDA':24,'MSFT':30,'MELI':120,'GGAL':10,'YPF':1,'PAM':25,'BMA':10,'CEPU':10}

def get_data():
    filas, ccls = [], []
    for t, r in cfg.items():
        try:
            u = yf.download(t, period="2d", interval="1m", progress=False, auto_adjust=True)
            ba = f"{t if t!='YPF' else 'YPFD'}.BA"
            a = yf.download(ba, period="2d", interval="1m", progress=False, auto_adjust=True)
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

if st.button('🔄 Actualizar'): st.rerun()
df, avg_ccl = get_data()

# --- LOGIC ---
if not df.empty:
    st.metric("📊 CCL Promedio", f"$ {avg_ccl:,.2f}")
    
    def get_s(r):
        if r['CCL'] < avg_ccl * 0.995 and r['Clima'] != "🔴": return "🟢 COMPRA"
        if r['CCL'] > avg_ccl * 1.005: return "🔴 VENTA"
        return "⚖️ MANTENER"
    
    df['Señal'] = df.apply(get_s, axis=1)
    
    upd = False
    for _, r in df.iterrows():
        tk = r['Activo']
        if r['Señal'] == "🟢 COMPRA" and st.session_state.saldo >= 500000 and tk not in st.session_state.pos:
            st.session_state.saldo -= 500000
            st.session_state.pos[tk] = {"m": 500000, "pc": r['ARS']}
            upd = True
        elif r['Señal'] == "🔴 VENTA" and tk in st.session_state.pos:
            p = st.session_state.pos.pop(tk)
            st.session_state.saldo += p['m'] * (r['ARS'] / p['pc'])
            upd = True
    if upd: save()

    st.subheader("🏢 Posiciones")
    if st.session_state.pos:
        pos_df = []
        for t, p in st.session_state.pos.items():
            act = df[df.Activo==t].iloc[0]['ARS'] if t in df.Activo.values else p['pc']
            pos_df.append({"Activo":t, "Monto":f"${p['m']:,.0f}", "Var":f"{((act/p['pc'])-1)*100:+.2f}%"})
        st.table(pd.DataFrame(pos_df))

    st.subheader("📊 Monitor")
    st.dataframe(df, use_container_width=True, hide_index=True)

st_autorefresh(interval=900000, key="bot")
