import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, os, pytz
from datetime import datetime

# --- CONFIGURACIÓN DE TIEMPO (ARGENTINA) ---
def obtener_estado_mercado():
    tz = pytz.timezone('America/Argentina/Buenos_Aires')
    ahora = datetime.now(tz)
    hora_min = ahora.hour * 100 + ahora.minute
    es_dia_habil = ahora.weekday() <= 4
    
    esta_abierto = es_dia_habil and (1100 <= hora_min < 1700)
    ventana_cierre = es_dia_habil and (1640 <= hora_min < 1700)
    return esta_abierto, ventana_cierre, ahora

# --- DATABASE / PERSISTENCIA ---
DB = "simons_gg_v01.json"
CAPITAL_ORIGEN = 30000000.0
# Rendimiento fijado: 10.365127833%
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
    ahora_str = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires')).strftime("%Y-%m-%d %H:%M")
    if not st.session_state.hist or st.session_state.hist[-1]['t'] != tot:
        st.session_state.hist.append({"fecha": ahora_str, "t": tot})
    with open(DB, "w") as f:
        json.dump({"s": st.session_state.saldo, "p": st.session_state.pos, "h": st.session_state.hist}, f, indent=4)

# --- INICIALIZACIÓN ---
st.set_page_config(page_title="Simons GG v01", layout="wide")

if 'init' not in st.session_state:
    d = load()
    st.session_state.update({'saldo': d["s"], 'pos': d["p"], 'hist': d["h"], 'init': True})

abierto, en_cierre, ahora_arg = obtener_estado_mercado()
v_i = sum(float(i['m']) for i in st.session_state.pos.values())
patrimonio_total = st.session_state.saldo + v_i

# --- DASHBOARD SUPERIOR ---
st.title("🦅 Simons GG v01🤑")

c1, c2, c3 = st.columns(3)
# Corregido el error de llaves aquí:
porcentaje_var = ((patrimonio_total / CAPITAL_ORIGEN) - 1) * 100
c1.metric("Patrimonio Total", f"AR$ {patrimonio_total:,.2f}", f"{porcentaje_var:+.4f}%")
c2.metric("Efectivo en Cuenta", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Ticket de Op. (8%)", f"AR$ {(patrimonio_total * 0.08):,.2f}")

if not abierto:
    st.error(f"🔴 MERCADO CERRADO (Hora Arg: {ahora_arg.strftime('%H:%M')})")
elif en_cierre:
    st.warning("⚠️ VENTANA DE CIERRE: Prohibidas las compras.")
else:
    st.success("🟢 SISTEMA ACTIVO")

# --- OBTENCIÓN DE DATOS (SIEMPRE VISIBLE) ---
cfg = {'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 'GGAL':10, 'YPF':1, 'BMA':10, 'CEPU':10, 'GOOGL':58, 'AMZN':144, 'META':24, 'VIST':3, 'PAM':25}

@st.cache_data(ttl=300)
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
            filas.append({"Activo": t if t!='PAM' else 'PAMP', "USD": pu, "ARS": pa, "CCL": ccl})
        except: continue
    return pd.DataFrame(filas), np.median(ccls) if ccls else 0

df, avg_ccl = get_market_data()

# --- LÓGICA DE TRADING (SOLO SI ESTÁ ABIERTO) ---
if abierto and not df.empty:
    upd = False
    MONTO_TICKET = patrimonio_total * 0.08
    
    for _, r in df.iterrows():
        tk = r['Activo']
        # Compras
        if not en_cierre and r['CCL'] < avg_ccl*0.995 and st.session_state.saldo >= MONTO_TICKET and tk not in st.session_state.pos:
            st.session_state.saldo -= MONTO_TICKET
            st.session_state.pos[tk] = {"m": MONTO_TICKET, "pc": r['ARS']}
            upd = True
        # Ventas
        elif tk in st.session_state.pos:
            if r['CCL'] > avg_ccl*1.005 or (en_cierre and r['CCL'] >= avg_ccl):
                p = st.session_state.pos.pop(tk)
                st.session_state.saldo += p['m'] * (r['ARS'] / p['pc'])
                upd = True
    if upd: save()

# --- TABLAS Y GRÁFICOS ---
st.subheader("📊 Monitor de Arbitraje")
if not df.empty:
    st.metric("CCL Promedio", f"AR$ {avg_ccl:,.2f}")
    st.dataframe(df, use_container_width=True, hide_index=True)

st.subheader("🏢 Cartera Activa")
if st.session_state.pos:
    st.table(pd.DataFrame([{"Activo":t, "Monto":f"${p['m']:,.0f}"} for t, p in st.session_state.pos.items()]))

if st.session_state.hist:
    st.subheader("📈 Curva de Equidad")
    st.line_chart(pd.DataFrame(st.session_state.hist).set_index('fecha')['t'])

st_autorefresh(interval=600000 if abierto else 3600000, key="simons_refresh")
