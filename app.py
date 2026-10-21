import streamlit as st
import pandas as pd
import plotly.express as px
from src.api_client import FootballDataAPI
from src.model import PoissonModel
from src.value_engine import ValueBettingEngine

st.set_page_config(
    page_title="Football Value Betting Engine (Live)",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ Football Value Betting Engine — Datos en Tiempo Real")
st.markdown("Plataforma interactiva conectada a la API oficial de fútbol para el análisis probabilístico de **Poisson**, **Expected Value ($EV$)** y gestión de riesgo mediante el **Criterio de Kelly**.")

# Inicializar API
api = FootballDataAPI()
competitions = api.get_competitions()

# Panel Lateral
st.sidebar.header("🌍 Seleccionar Competición")
selected_league_name = st.sidebar.selectbox("Liga", list(competitions.keys()), index=0)
league_code = competitions[selected_league_name]

# Carga de datos dinámicos con caché de Streamlit
@st.cache_data(ttl=3600)
def load_live_data(code):
    return api.fetch_matches_data(code)

with st.spinner(f"Cargando datos en vivo de {selected_league_name}..."):
    try:
        df_matches = load_live_data(league_code)
        model = PoissonModel(df_matches)
        available_teams = sorted(list(model.teams_df.index))
        st.sidebar.success(f"¡{len(df_matches)} partidos analizados!")
    except Exception as e:
        st.error(f"Error al conectar con la API: {e}")
        st.stop()

st.sidebar.markdown("---")
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

# Pestañas
tab1, tab2, tab3 = st.tabs(["📊 Análisis y Apuestas de Valor", "🔥 Matriz de Marcadores Probables", "📈 Tabla de Equipos y Métricas"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⚽ Goles Esperados (xG)")
        st.metric(f"xG {home_team}", prediction['expected_goals_home'])
        st.metric(f"xG {away_team}", prediction['expected_goals_away'])

    with col2:
        st.subheader("🎯 Probabilidades del Modelo (Cuotas Justas)")
        st.write(f"**Victoria Local ({home_team}):** {prediction['prob_home']*100:.1f}% *(Cuota Justa: `{prediction['fair_odds_home']}`)*")
        st.write(f"**Empate (X):** {prediction['prob_draw']*100:.1f}% *(Cuota Justa: `{prediction['fair_odds_draw']}`)*")
        st.write(f"**Victoria Visitante ({away_team}):** {prediction['prob_away']*100:.1f}% *(Cuota Justa: `{prediction['fair_odds_away']}`)*")

    st.markdown("---")
    st.subheader("💡 Diagnóstico de Apuestas de Valor (Value Bets)")
    
    df_opps = pd.DataFrame(opportunities)
    traduccion_mercados = {
        'Home (1)': f'Gana Local ({home_team})',
        'Draw (X)': 'Empate (X)',
        'Away (2)': f'Gana Visitante ({away_team})'
    }
    df_opps['market'] = df_opps['market'].map(traduccion_mercados)
    df_opps['is_value_bet'] = df_opps['is_value_bet'].map({True: 'SÍ 🟢 (Apuesta Recomendada)', False: 'NO 🔴'})
    df_opps.columns = ["Mercado", "Prob. Modelo", "Cuota Casa", "Cuota Justa", "Valor Esperado (EV)", "¿Tiene Valor?", "Apuesta Sugerida"]
    
    st.dataframe(df_opps, use_container_width=True)

with tab2:
    st.subheader("🔥 Mapa de Calor: Probabilidad de Marcadores Exactos (%)")
    st.markdown("Distribución bivariada de Poisson para cada marcador posible hasta 5 goles:")
    
    matrix_pct = prediction['matrix'] * 100
    
    fig = px.imshow(
        matrix_pct,
        labels=dict(x=f"Goles {away_team}", y=f"Goles {home_team}", color="Probabilidad (%)"),
        x=[str(i) for i in range(6)],
        y=[str(i) for i in range(6)],
        color_continuous_scale="Viridis",
        text_auto=".1f"
    )
    fig.update_layout(height=500, width=600)
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader(f"🛡️ Métricas de Fuerza Ofensiva y Defensiva en {selected_league_name}")
    df_teams = model.teams_df[['attack_home', 'defense_home', 'attack_away', 'defense_away']].copy()
    df_teams.columns = ["Ataque (Local)", "Defensa (Local)", "Ataque (Visitante)", "Defensa (Visitante)"]
    st.dataframe(df_teams.round(2), use_container_width=True)