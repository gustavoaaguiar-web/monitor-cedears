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
    # Evitar duplicados en el mismo minuto
    if not st.session_state.hist or st.session_state.hist[-1]['t'] != tot:
        st.session_state.hist.append({"fecha": ahora_str, "t": tot})
    with open(DB, "w") as f:
        json.dump({"s": st.session_state.saldo, "p": st.session_state.pos, "h": st.session_state.hist}, f, indent=4)

# --- INICIALIZACIÓN ---
st.set_page_config(page_title="Simons GG v01 - Full", layout="wide")

if 'init' not in st.session_state:
    d = load()
    st.session_state.update({'saldo': d["s"], 'pos': d["p"], 'hist': d["h"], 'init': True})

abierto, en_cierre, ahora_arg = obtener_estado_mercado()
v_i = sum(float(i['m']) for i in st.session_state.pos.values())
patrimonio_total = st.session_state.saldo + v_i

# --- DASHBOARD SUPERIOR ---
st.title("🦅 Simons GG v01🤑")
c1, c2, c3 = st.columns(3)
c1.metric("Patrimonio Total", f"AR$ {patrimonio_total:,.2f}", f"{((patrimonio_total/CAPITAL_ORIGEN)-1)*10
