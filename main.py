import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# --- TUS DATOS DE ACCESO DIRECTOS ---
URL_FINAL = "https://docs.google.com/spreadsheets/d/19BvTkyD2ddrMsX1ghYGgnnq-BAfYJ_7qkNGqAsJel-M/edit?usp=drivesdk"

# Datos de la cuenta de servicio (Tu llave)
creds = {
    "type": "service_account",
    "project_id": "simons-gg-database",
    "private_key_id": "980e731ad59082e0596f2ae24917e5e93f0c59da",
    "private_key": st.secrets["connections"]["gsheets"]["private_key"] if "connections" in st.secrets else "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDPRxWZs46dcd/9\nbUTQ8jfneyRPQOkEnWI+/MEIapor8nsnwtOxaMEA+gn63j1JLv1n8/K9dceL9fOj\nwBEBNhlu4MkomR4U2ayDQQ235xG0J6GgdF5svVhOmnQuDQrXbTiX9K/nlGBgODmH\nM1DFLB53xMHnh5D0cKLi7lhNNqVouBvHkCfQ38Oc7yoNsicgLJXF3B8/rYCC4rad\nd8M1y2/cjfBrcBdxSPgGxIcE/4xZSCoQe7l5d6eRhw8O9qe0K+G2AJIYjBdxC1Xl\nAkhrp17WA9rRrq+YaNgn1MrV47/DRdvT5BDJc9J2W8zowPjOXlI4ziUdA87wpmcg\n17hyN/mPAgMBAAECgf81cB4hgilCbhlRPNqBA/FlvFmgFRv+FJU/p+ocQV999QXL\nOm9ZTah0mAH6q1EhjPvH0RzDu5m2e7JUhS/dIBVugIVb8h3PQk83h44B25C04YLJ\n2zZ80lPx7+AD/1jMMVxl0K+JBLfUFqq+MHyiWL2CIzfaeRjl7CQSXWBmh7AdTuMI\n0rnZoSnaD107VULqqRZVbd3Ru+9a9f69Ea/Bml3fGZe1lp6r9gsUUx3BPZj9vbI0\n8Sx4bN3lU7zu9HBZ0WBS22ski7ZI451g7lkPI2mHqiKoEHYAq+v/hCERWifaB8ol\nbfj2lUw5Egcmp5TPtJ9oxtk8B1OV1pXli8ZlnjECgYEA7KC8GFCc4+p8Or+3Mub1\nHMPWQk0MYxA+VKes1riOk4rpTdIAYxrvhXGcnHqkqU0c1J+h6C9CtsVRyavhRXGK\nB2UfAmoplEX4OZ4/qtd0gfz9MrgKAnaMVGuiMny6/JR/8UEFzBflesU3r17yXYbN\n17omMpey7V3lussEaVezfv0CgYEA4D851pYnq2filPXxSJacTl0cW/vvpNvF7sMe\nm7ZL5h1opzfDwtf5lVWrCUMnGHOVRiDMtInSqbvw34cvF2Cqqzi0BAudQeLstmOs\nZ1BflHAAMn23nVuHeWFJX8fG7Q8FXkCQO2mVFoEq5mBfKPzBOBwjEYHp21Asndkx\nrGpyrnsCgYEAmHb8myId5NCqWOQ8c0TS/ETG4hNo/s9xifQ77mIeI7zmlGjSLQkm\n+bF5em2feSKhh/KPTN5euwsqpqnjzW3ZxOgH8fNbdRkcVmu7lCWdAUB0GGDyuiGO\nS7rKWIN7q9E3GsiNprJi/xbhyVKBEXgRW4WqpQCPnlfY9OFop0OF+TUCgYEAouOq\nasJ1nF+Ayf2Ayf2Av96POakO8Y4mvFTcCRx4vlkD9uqD23t5Wq4xYJVzAO5jlrJWyzMG\nH1pByQN465Wx0kRolKlCsfGR0Is6sR3j3MQYOaXFrud9GfOji7rsZoOibw5LMvSp\nEE8YedlnxSJZ3VcEL3LY0l3Q9nrdfeeH2psUJMMCgYA+gs269sYb+OzooLjtPpFm\ns0lm6PoF2nOor5Kd73Ln4n5RW+ghfw04aQLDDGnYsockmuJXS4wiVgOl9orBRV1b\npaByZkEuUeGY8HYZU688p8fbtXMcfGc2Q+8YtHgJC656Z62FaU0Lfr4B5S2+Ye0p\n3IDzotp6hoemCdB1T6EStA==\n-----END PRIVATE KEY-----\n",
    "client_email": "simons-bot@simons-gg-database.iam.gserviceaccount.com",
    "client_id": "104750006903474484966",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/official/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/simons-bot%40simons-gg-database.iam.gserviceaccount.com",
}

st.title("🦅 Simons GG v02 - Conexión Directa")

# Conexión forzada
conn = st.connection("gsheets", type=GSheetsConnection, **creds)

if st.button("🚀 PROBAR GUARDADO"):
    try:
        df_test = pd.DataFrame([{"saldo": 33362112.69, "posiciones": "{}", "historial": "[]", "update": "OK"}])
        conn.create(spreadsheet=URL_FINAL, worksheet="Hoja1", data=df_test)
        st.success("¡LO LOGRAMOS! El bot escribió en el Excel.")
        st.balloons()
    except Exception as e:
        st.error(f"Error: {e}")
        
