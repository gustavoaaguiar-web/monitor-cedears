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
            t_usa = 'PAM' if
