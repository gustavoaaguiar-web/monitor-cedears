import streamlit as st
from streamlit_gsheets import GSheetsConnection
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import json, pytz, smtplib
from datetime import datetime
from email.message import EmailMessage

# --- CONFIG CORREO ---
MI_MAIL = "gustavoaaguiar99@gmail.com"
CLAVE_APP = "zmupyxmxwbjsllsu"

def enviar_alerta(asunto, cuerpo):
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

# --- VALORES DE PERSISTENCIA ---
CAPITAL_ORIGEN = 30000000.0
PATRIMONIO_HOY = 33362112.69 

def obtener_estado_mercado():
    tz = pytz.timezone('America/Argentina/Buenos_Aires')
    ahora = datetime.now(tz)
    hora_min = ahora.hour * 100 + ahora.minute
    es_dia_habil = ahora.weekday() <= 4
    abierto = es_dia_habil and (1100 <= hora_min < 1700)
    cierre = es_dia_habil and (1640 <= hora_min < 1700)
    return abierto, cierre, ahora

# --- CONEXIÓN GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_memoria():
    try:
        df = conn.read(worksheet="Hoja1")
        if not df.empty:
            u = df.iloc[-1]
            return float(u['saldo']), json.loads(u['posiciones']), json.loads(u['historial'])
    except: pass
    return PATRIMONIO_HOY, {}, [{"fecha": datetime.now().strftime("%Y-%m-%d"), "t": PATRIMONIO_HOY}]

def guardar_memoria(s, p, h):
    nuevo = pd.DataFrame([{"saldo": s, "posiciones": json.dumps(p), "historial": json.dumps(h), "update": datetime.now().strftime("%Y-%m-%d %H:%M")}])
    conn.create(data=nuevo)

# --- APP ---
st.set_page_config(page_title="Simons GG v02", layout="wide")
if 'init' not in st.session_state:
    s, p, h = cargar_memoria()
    st.session_state.update({'saldo': s, 'pos': p, 'hist': h, 'init': True})

abierto, en_cierre, ahora_arg = obtener_estado_mercado()
patrimonio_total = st.session_state.saldo + sum(float(i['m']) for i in st.session_state.pos.values())

# DASHBOARD
st.title("🦅 Simons GG v02 🤑")
c1, c2, c3 = st.columns(3)
var = ((patrimonio_total / CAPITAL_ORIGEN) - 1) * 100
c1.metric("Patrimonio Total", f"AR$ {patrimonio_total:,.2f}", f"{var:+.4f}%")
c2.metric("Efectivo", f"AR$ {st.session_state.saldo:,.2f}")
c3.metric("Ticket 8%", f"AR$ {(patrimonio_total*0.08):,.2f}")

# MOTOR DE DATOS (IGUAL AL ANTERIOR)
cfg = {'AAPL':20, 'TSLA':15, 'NVDA':24, 'MSFT':30, 'MELI':120, 'GGAL':10, 'YPF':1, 'BMA':10, 'CEPU':10, 'GOOGL':58, 'AMZN':144, 'META':24, 'VIST':3, 'PAM':25}

@st.cache_data(ttl=300)
def get_data():
    filas, ccls = [], []
    for t, r in cfg.items():
        try:
            ba = "YPFD.BA" if t=='YPF' else ("PAMP.BA" if t=='PAM' else f"{t}.BA")
            u, a = yf.download(t, period="2d", interval="1m", progress=False), yf.download(ba, period="2d", interval="1m", progress=False)
            pu, pa = float(u.Close.iloc[-1]), float(a.Close.iloc[-1])
            ccl = (pa * r) / pu
            ccls.append(ccl)
            h = yf.download(t, period="3mo", interval="1d", progress=False)
            re = np.diff(np.log(h.Close.values.flatten().reshape(-1, 1)), axis=0)
            cl = "🟢" if GaussianHMM(n_components=3, random_state=42).fit(re).predict(re)[-1] == 0 else "🔴"
            filas.append({"Activo": t, "USD": pu, "ARS": pa, "CCL": ccl, "Clima": cl})
        except: continue
    df = pd.DataFrame(filas)
    avg = np.median(ccls) if ccls else 0
    df['Señal'] = df.apply(lambda x: "🟢 COMPRA" if x['CCL'] < avg*0.995 and x['Clima']!="🔴" else ("🔴 VENTA" if x['CCL'] > avg*1.005 else "⚖️ MANTENER"), axis=1)
    return df, avg

df, avg_ccl = get_data()

# OPERATORIA
if abierto and not df.empty:
    upd = False
    monto = patrimonio_total * 0.08
    for _, r in df.iterrows():
        tk = r['Activo']
        if not en_cierre and r['Señal'] == "🟢 COMPRA" and st.session_state.saldo >= monto and tk not in st.session_state.pos:
            st.session_state.saldo -= monto
            st.session_state.pos[tk] = {"m": monto, "pc": r['ARS']}
            upd, msg = True, f"Compra {tk} a {r['ARS']}"
            enviar_alerta("🟢 COMPRA", msg)
        elif tk in st.session_state.pos and (r['Señal'] == "🔴 VENTA" or (en_cierre and r['CCL'] >= avg_ccl)):
            p = st.session_state.pos.pop(tk)
            st.session_state.saldo += p['m'] * (r['ARS'] / p['pc'])
            upd, msg = True, f"Venta {tk} a {r['ARS']}"
            enviar_alerta("🔴 VENTA", msg)
    if upd: guardar_memoria(st.session_state.saldo, st.session_state.pos, st.session_state.hist)

# TABLAS
st.subheader("📊 Monitor")
st.dataframe(df, use_container_width=True, hide_index=True)
st.subheader("🏢 Cartera")
if st.session_state.pos: st.table(pd.DataFrame([{"Activo":k, "Monto":f"${v['m']:,.0f}"} for k,v in st.session_state.pos.items()]))

st_autorefresh(interval=600000 if abierto else 3600000, key="v2_ref")
