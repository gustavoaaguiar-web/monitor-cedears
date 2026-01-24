import streamlit as st
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
import numpy as np
import pandas as pd
from streamlit_autorefresh import st_autorefresh # Importar aquí para usarlo

# Configuración de la página
st.set_page_config(page_title="Simons-Arg ADRs", page_icon="🦅", layout="wide") # Layout wide para más columnas

st.title("🦅 Monitor Simons-Arg")
st.write("Seguimiento de CEDEARs y ADRs Argentinos")

# Diccionario con Ratios Actualizados
cedears = {
    'AAPL': 20, 'TSLA': 15, 'NVDA': 24, 'MSFT': 30, 'MELI': 120,
    'GGAL': 10, 'YPF': 2, 'PAM': 25, 'BMA': 10, 'CEPU': 10, 'VIST': 1
}

def procesar_datos():
    filas = []
    lista_ccl = []
    
    for t, ratio in cedears.items():
        try:
            # Descarga de datos para el activo en EE.UU.
            u = yf.download(t, period="2d", interval="1m", progress=False, auto_adjust=True)
            
            if u.empty: continue # Si no hay datos de USA, saltar
            
            val_usa = float(u['Close'].values.flatten()[-1])
            
            # Descarga de datos para el activo en Argentina (solo si no es un activo directo de USA como AAPL)
            if '.BA' in t + '.BA': # Verifica si existe una contraparte argentina (si no, no intenta bajarla)
                a = yf.download(t + ".BA", period="2d", interval="1m", progress=False, auto_adjust=True)
                if a.empty: 
                    # Si falla bajar .BA, asumimos que es un activo solo de USA y no calculamos CCL
                    ccl = np.nan # No es un ADR o CEDEAR, no aplica CCL
                    val_arg = np.nan
                else:
                    val_arg = float(a['Close'].values.flatten()[-1])
                    ccl = (val_arg * ratio) / val_usa
            else: # Para activos puramente de USA, no aplica CCL
                ccl = np.nan
                val_arg = np.nan

            lista_ccl.append(ccl)
            
            # Modelo de Clima (HMM) - Usamos más data para mayor precisión
            h = yf.download(t, period="3mo", interval="1d", progress=False) # 3 meses para más estabilidad
            
            if h.empty: # Si no hay datos históricos, no podemos calcular el clima
                clima = "❓" 
            else:
                rets = np.diff(np.log(h['Close'].values.flatten().reshape(-1, 1)), axis=0)
                # Asegurarse de que haya suficientes puntos para el modelo
                if len(rets) < 5: # Necesitamos al menos unos pocos puntos para el HMM
                    clima = "❓"
                else:
                    model = GaussianHMM(n_components=3, random_state=42, n_iter=100).fit(rets) # Más iteraciones para mejor ajuste
                    estado = model.predict(rets)[-1]
                    
                    # 0: Calmo (Verde), 1: Incierto (Amarillo), 2: Tenso (Rojo)
                    clima = "🟢" if estado == 0 else "🟡" if estado 1 else "🔴"
            
            filas.append({"Activo": t, "USD": round(val_usa, 2), "CCL": round(ccl, 2) if not np.isnan(ccl) else "N/A", "Clima": clima})
        except Exception as e:
            # st.warning(f"Error al procesar {t}: {e}") # Para depuración, se puede descomentar
            continue
            
    df = pd.DataFrame(filas)
    
    # Cálculo de señales basado en la desviación del promedio del CCL
    if not df.empty and 'CCL' in df.columns:
        df_ccl_valid = df[df['CCL'] != "N/A"] # Solo considerar CCLs válidos para el promedio
        if not df_ccl_valid.empty:
            ccl_mean = df_ccl_valid['CCL'].astype(float).mean() # Usar la media para la señal
            ccl_std = df_ccl_valid['CCL'].astype(float).std() # Desviación estándar para rangos
            
            # Definimos umbrales para Compra/Venta/Mantener
            # Puedes ajustar estos porcentajes según tu estrategia
            compra_threshold = ccl_mean - (ccl_std * 0.5) # Compra si está 0.5 desviaciones estándar por debajo de la media
            venta_threshold = ccl_mean + (ccl_std * 0.5)  # Venta si está 0.5 desviaciones estándar por encima de la media
            
            def obtener_senal(ccl_val):
                if ccl_val == "N/A":
                    return "---" # No aplica señal si no hay CCL
                
                ccl_val_float = float(ccl_val)
                if ccl_val_float < compra_threshold:
                    return "🐂 COMPRA" # Toro verde
                elif ccl_val_float > venta_threshold:
                    return "🐻 VENTA" # Oso rojo
                else:
                    return "⚖️ MANTENER" # Balanza
            
            df['Señal'] = df['CCL'].apply(obtener_senal)
            
        else: # Si no hay CCLs válidos para calcular la media
            df['Señal'] = "N/A" # No aplica señal
            ccl_mean = 0 # Para que el metric de CCL Promedio sea 0
            
    else: # Si el DataFrame está vacío o no tiene columna CCL
        df['Señal'] = "N/A"
        ccl_mean = 0

    return df, ccl_mean

# Botón de actualización
if st.button('Actualizar Ahora'):
    st.rerun()

# Procesamiento y visualización
# Usamos st.empty para que el spinner no cause un "re-render" visual brusco
placeholder = st.empty()
with placeholder.container():
    with st.spinner('Analizando mercado...'):
        data, ccl_avg = procesar_datos()

if not data.empty:
    # Mostrar CCL Promedio en un recuadro destacado
    st.metric("CCL Promedio del Panel", f"${ccl_avg:,.2f}")
    
    # Tabla principal
    st.dataframe(data, use_container_width=True, hide_index=True)
else:
    st.error("No se pudieron obtener datos. Verificá la conexión o los símbolos de los activos.")

# Auto-refresco cada 15 min (900000ms)
st_autorefresh(interval=900000, key="datarefresh")
