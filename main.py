import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os, pytz, smtplib
from datetime import datetime
from email.message import EmailMessage

# --- CONFIGURACIÓN DE TIEMPO (ARGENTINA) ---
def obtener_estado_mercado():
    tz = pytz.timezone('America/Argentina/Buenos_Aires')
    ahora = datetime.now(tz)
    hora_min = ahora.hour * 100 + ahora.minute
    es_dia_habil = ahora.weekday() <= 4
    
    esta_abierto = es_dia_habil and (1100 <= hora_min < 1700)
    ventana_cierre = es_dia_habil and (1640 <= hora_min < 1700) # De 16:40 a 17:00 solo cierra
    return esta_abierto, ventana_cierre

# --- DATABASE / PERSISTENCIA ---
DB = "simons_gg_v01.json"
CAPITAL_ORIGEN = 30000000.0
# Rendimiento actual del 10.365127833%
CAPITAL_PARTIDA = CAPITAL_ORIGEN * 1.10365127833 

def load():
    if os.path.exists(DB):
        try:
            with open(DB, "r") as f: return json.load(f)
        except: pass
    return {"s": CAPITAL_PARTIDA, "p": {}, "h": [{"fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "t": CAPITAL_PARTIDA}]}

def save():
    v_a = sum(float(i['m']) for i in st.session_state.pos.values())
    tot = st.session_state.saldo + v_a
    ahora = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')).strftime("%Y-%m-%d %H:%M")
    if not st.session_state.hist or st.session_state.hist[-1]['t'] != tot:
        st.session_state.hist.append({"fecha": ahora, "t": tot})
    with open(DB, "w") as f:
        json.dump({"s": st.session_state.saldo, "p": st.session_state.pos, "h": st.session_state.hist}, f, indent=4)

# --- UI CONFIG ---
st.set_page_config(page_title="Simons GG v01 - High Performance", layout="wide")

if 'init' not in st.session_state:
    d = load()
    st.session_state.update({'saldo': d["s"], 'pos': d["p"], 'hist': d["h"], 'init': True})

abierto, en_cierre = obtener_estado_mercado()
v_i = sum(float(i['m']) for i in st.session_state.pos.values())
patrimonio_total = st.session_state.saldo + v_i

# --- DASHBOARD ---
st.title("🦅 Simons GG v01🤑")
c1, c2, c3 = st.columns(3)
c1.metric("Patrimonio Total", f"AR$ {patrimonio_total:,.2f}", f"{((patrimonio_total/CAPITAL_ORIGEN)-1)*100:+.4f}%")
c2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Ticket de Operación (8%)", f"AR$ {patrimonio_total * 0.08:,.2f}")

if not abierto:
    st.error("🔴 MERCADO CERRADO - El script está en modo lectura.")
elif en_cierre:
    st.warning("⚠️ VENTANA DE CIERRE (16:40 - 17:00) - No se abren nuevas posiciones.")

# --- LÓGICA DE TRADING ---
if abierto:
    cfg = {'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 'GGAL':10, 'YPF':1, 'BMA':10, 'CEPU':10, 'GOOGL':58, 'AMZN':144, 'META':24, 'VIST':3, 'PAM':25}

    @st.cache_data(ttl=60)
    def get_market_data():
        filas, ccls = [], []
        for t, r in cfg.items():
            try:
                ba_tk = "YPFD.BA" if t=='YPF' else ("PAMP.BA" if t=='PAM' else f"{t}.BA")
                u = yf.download(t, period="2d", interval="1m", progress=False, auto_adjust=True)
                a = yf.download(ba_tk, period="2d", interval="1m", progress=False, auto_adjust=True)
                if u.empty or a.empty: continue
                pu, pa = float(u.Close.iloc[-1]), float(a.Close.iloc[-1])
                ccl = (pa * r) / pu
                ccls.append(ccl)
                
                # Clima HMM
                h = yf.download(t, period="3mo", interval="1d", progress=False)
                cl = "⚪"
                if not h.empty and len(h)>10:
                    re = np.diff(np.log(h.Close.values.flatten().reshape(-1, 1)), axis=0)
                    cl = "🟢" if GaussianHMM(n_components=3, random_state=42).fit(re).predict(re)[-1]==0 else "🔴"
                filas.append({"Activo": t if t!='PAM' else 'PAMP', "USD": pu, "ARS": pa, "CCL": ccl, "Clima": cl})
            except: continue
        return pd.DataFrame(filas), np.median(ccls) if ccls else 0

    df, avg_ccl = get_market_data()

    if not df.empty:
        # Cálculo de Señales
        df['Señal'] = df.apply(lambda r: "🟢 COMPRA" if r['CCL'] < avg_ccl*0.995 and r['Clima']!="🔴" else ("🔴 VENTA" if r['CCL'] > avg_ccl*1.005 else "⚖️ MANTENER"), axis=1)
        
        upd = False
        MONTO_DINAMICO = patrimonio_total * 0.08 # 8% del patrimonio actual
        
        for _, r in df.iterrows():
            tk = r['Activo']
            # COMPRA (Solo si NO estamos en ventana de cierre)
            if not en_cierre and r['Señal'] == "🟢 COMPRA" and st.session_state.saldo >= MONTO_DINAMICO and tk not in st.session_state.pos:
                st.session_state.saldo -= MONTO_DINAMICO
                st.session_state.pos[tk] = {"m": MONTO_DINAMICO, "pc": r['ARS']}
                upd = True
            
            # VENTA (Estrategia normal O ventana de cierre)
            elif tk in st.session_state.pos:
                if r['Señal'] == "🔴 VENTA" or (en_cierre and r['CCL'] >= avg_ccl):
                    p = st.session_state.pos.pop(tk)
                    st.session_state.saldo += p['m'] * (r['ARS'] / p['pc'])
                    upd = True
        
        if upd: save()
        st.subheader("📊 Monitor de Arbitraje")
        st.dataframe(df, use_container_width=True, hide_index=True)

# --- CARTERA Y GRÁFICO ---
st.subheader("🏢 Cartera Activa")
if st.session_state.pos:
    pos_data = [{"Activo":t, "Inversión":f"${p['m']:,.0f}", "Entrada":f"${p['pc']:,.2f}"} for t, p in st.session_state.pos.items()]
    st.table(pd.DataFrame(pos_data))

if st.session_state.hist:
    st.subheader("📈 Curva de Equidad")
    st.line_chart(pd.DataFrame(st.session_state.hist).set_index('fecha')['t'])

st_autorefresh(interval=600000 if abierto else 3600000, key="simons_refresh")
