import streamlit as st
import pandas as pd
from src.model import PoissonModel
from src.value_engine import ValueBettingEngine

# Configuración de la página
st.set_page_config(
    page_title="Motor de Apuestas de Valor en Fútbol",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ Motor Estadístico y de Apuestas de Valor en Fútbol")
st.markdown("Herramienta de análisis basada en la **Distribución de Poisson** y el **Criterio de Kelly** para identificar apuestas con valor esperado positivo ($EV > 0$).")

# Cargar Modelo con caché
@st.cache_data
def load_model():
    return PoissonModel('data/SP1.csv')

try:
    model = load_model()
    available_teams = sorted(list(model.teams_df.index))
except Exception as e:
    st.error(f"Error al cargar los datos: {e}")
    st.stop()

# Panel Lateral de Configuración
st.sidebar.header("⚙️ Configuración del Partido")

home_team = st.sidebar.selectbox("Equipo Local", available_teams, index=0)
away_teams_filtered = [t for t in available_teams if t != home_team]
away_team = st.sidebar.selectbox("Equipo Visitante", away_teams_filtered, index=0)

bankroll = st.sidebar.number_input("Capital Disponible ($)", min_value=10.0, value=1000.0, step=50.0)

st.sidebar.subheader("💰 Cuotas de la Casa de Apuestas")
odds_home = st.sidebar.number_input(f"Cuota Local ({home_team})", min_value=1.01, value=1.85, step=0.05)
odds_draw = st.sidebar.number_input("Cuota Empate (X)", min_value=1.01, value=3.80, step=0.05)
odds_away = st.sidebar.number_input(f"Cuota Visitante ({away_team})", min_value=1.01, value=4.50, step=0.05)

# Procesar Predicción y Análisis
prediction = model.predict_match(home_team, away_team)
engine = ValueBettingEngine()
market_odds = {'home': odds_home, 'draw': odds_draw, 'away': odds_away}
opportunities = engine.analyze_opportunity(prediction, market_odds, bankroll=bankroll)

# Pestañas Principales
tab1, tab2 = st.tabs(["📊 Análisis del Partido", "📈 Tabla de Equipos y Métricas"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⚽ Goles Esperados (xG)")
        st.metric(f"xG {home_team}", prediction['expected_goals_home'])
        st.metric(f"xG {away_team}", prediction['expected_goals_away'])

    with col2:
        st.subheader("🎯 Probabilidades del Modelo (Cuotas Justas)")
        st.write(f"**Victoria Local:** {prediction['prob_home']*100:.1f}% *(Cuota Justa: `{prediction['fair_odds_home']}`)*")
        st.write(f"**Empate:** {prediction['prob_draw']*100:.1f}% *(Cuota Justa: `{prediction['fair_odds_draw']}`)*")
        st.write(f"**Victoria Visitante:** {prediction['prob_away']*100:.1f}% *(Cuota Justa: `{prediction['fair_odds_away']}`)*")

    st.markdown("---")
    st.subheader("💡 Diagnóstico de Apuestas de Valor (Value Bets)")
    
    # Crear DataFrame explicativo traducido
    df_opps = pd.DataFrame(opportunities)
    
    # Renombrar valores de la columna de mercado al español
    traduccion_mercados = {
        'Home (1)': f'Gana Local ({home_team})',
        'Draw (X)': 'Empate (X)',
        'Away (2)': f'Gana Visitante ({away_team})'
    }
    df_opps['market'] = df_opps['market'].map(traduccion_mercados)
    
    # Traducir booleano de valor
    df_opps['is_value_bet'] = df_opps['is_value_bet'].map({True: 'SÍ 🟢', False: 'NO 🔴'})
    
    df_opps.columns = ["Mercado", "Prob. Modelo", "Cuota Casa", "Cuota Justa", "Valor Esperado (EV)", "¿Tiene Valor?", "Apuesta Sugerida"]
    
    st.dataframe(df_opps, use_container_width=True)

with tab2:
    st.subheader("🛡️ Métricas de Fuerza Ofensiva y Defensiva por Equipo")
    
    df_teams = model.teams_df[['attack_home', 'defense_home', 'attack_away', 'defense_away']].copy()
    df_teams.columns = ["Ataque (Local)", "Defensa (Local)", "Ataque (Visitante)", "Defensa (Visitante)"]
    
    st.dataframe(df_teams.round(2), use_container_width=True)