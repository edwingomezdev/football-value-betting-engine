import streamlit as st
import pandas as pd
import plotly.express as px
from src.api_client import FootballDataAPI
from src.odds_api_client import OddsAPIClient
from src.model import PoissonModel
from src.value_engine import ValueBettingEngine

st.set_page_config(
    page_title="Football Value Betting Engine (Live)",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ Football Value Betting Engine — Champions League & Ligas en Vivo")
st.markdown("Analizador de **Valor Esperado ($EV > 0$)** con datos históricos y **cuotas reales en tiempo real** extraídas de casas de apuestas.")

# Inicializar Clientes
fd_api = FootballDataAPI()
odds_api = OddsAPIClient()

leagues_map = {
    "UEFA Champions League": ("CL", "soccer_uefa_champs_league"),
    "Premier League (Inglaterra)": ("PL", "soccer_epl"),
    "LaLiga (España)": ("PD", "soccer_spain_la_liga"),
    "Serie A (Italia)": ("SA", "soccer_italy_serie_a"),
    "Bundesliga (Alemania)": ("BL1", "soccer_germany_bundesliga"),
    "Ligue 1 (Francia)": ("FL1", "soccer_france_ligue_one")
}

# Barra Lateral: Selección de Liga
st.sidebar.header("🌍 Seleccionar Competición")
selected_league_label = st.sidebar.selectbox("Liga / Torneo", list(leagues_map.keys()), index=0)
fd_code, odds_key = leagues_map[selected_league_label]

# Cargar Datos Históricos para el Modelo (con caché de 1 hora)
@st.cache_data(ttl=3600)
def load_historical_data(code):
    return fd_api.fetch_matches_data(code)

# Cargar Cuotas Reales en Tiempo Real (con caché de 10 minutos)
@st.cache_data(ttl=600)
def load_live_odds(key):
    return odds_api.fetch_live_odds(key)

with st.spinner("Cargando modelo estadístico y cuotas en tiempo real..."):
    try:
        # Si la API de resultados históricos no trae la Champions League por restricción,
        # usamos los datos de LaLiga/Premier como base general o el dataset histórico local.
        try:
            df_matches = load_historical_data(fd_code)
        except Exception:
            df_matches = pd.read_csv('data/SP1.csv')
            
        model = PoissonModel(df_matches)
        available_teams_model = sorted(list(model.teams_df.index))
        
        # Cargar eventos en vivo con cuotas
        live_events = load_live_odds(odds_key)
        st.sidebar.success(f"¡{len(live_events)} partidos con cuotas en vivo!")
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        st.stop()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Selección de Partido")

# Crear opciones de partidos en vivo si están disponibles
if live_events:
    event_options = [f"{e['home_team']} vs {e['away_team']}" for e in live_events]
    selected_event_idx = st.sidebar.selectbox("Partidos Próximos (Con Cuotas Reales)", range(len(event_options)), format_func=lambda x: event_options[x])
    selected_event = live_events[selected_event_idx]
    
    # Asignación automática de equipos y cuotas desde la API
    home_team_default = selected_event['home_team']
    away_team_default = selected_event['away_team']
    
    auto_odds = selected_event['odds']
    default_home_odd = auto_odds.get('home', 2.0)
    default_draw_odd = auto_odds.get('draw', 3.0)
    default_away_odd = auto_odds.get('away', 3.5)
    bookmaker_name = auto_odds.get('bookmaker_name', 'Mercado')
    
    st.sidebar.info(f"📍 Cuotas en vivo extraídas de: **{bookmaker_name}**")
else:
    home_team_default = available_teams_model[0]
    away_team_default = available_teams_model[1] if len(available_teams_model) > 1 else available_teams_model[0]
    default_home_odd, default_draw_odd, default_away_odd = 1.85, 3.80, 4.50

# Selector manual o verificado
home_team = st.sidebar.text_input("Equipo Local", value=home_team_default)
away_team = st.sidebar.text_input("Equipo Visitante", value=away_team_default)

bankroll = st.sidebar.number_input("Capital Disponible ($)", min_value=10.0, value=1000.0, step=50.0)

st.sidebar.subheader("💰 Cuotas de la Casa de Apuestas (Modificables)")
odds_home = st.sidebar.number_input(f"Cuota Local ({home_team})", min_value=1.01, value=float(default_home_odd), step=0.05)
odds_draw = st.sidebar.number_input("Cuota Empate (X)", min_value=1.01, value=float(default_draw_odd), step=0.05)
odds_away = st.sidebar.number_input(f"Cuota Visitante ({away_team})", min_value=1.01, value=float(default_away_odd), step=0.05)

# Si los equipos del partido en vivo no están en la tabla histórica, añadirlos temporalmente con promedio liga
for t in [home_team, away_team]:
    if t not in model.teams_df.index:
        model.teams_df.loc[t] = [model.avg_home_goals, model.avg_away_goals, model.avg_away_goals, model.avg_home_goals, 1.0, 1.0, 1.0, 1.0]

# Procesar Predicción y Análisis
prediction = model.predict_match(home_team, away_team)
engine = ValueBettingEngine()
market_odds = {'home': odds_home, 'draw': odds_draw, 'away': odds_away}
opportunities = engine.analyze_opportunity(prediction, market_odds, bankroll=bankroll)

# Pestañas Principales
tab1, tab2, tab3 = st.tabs(["📊 Análisis y Apuestas de Valor", "🔥 Matriz de Marcadores Probables", "📈 Métricas de Equipos"])

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
    st.subheader(f"🛡️ Métricas de Fuerza Ofensiva y Defensiva")
    df_teams = model.teams_df[['attack_home', 'defense_home', 'attack_away', 'defense_away']].copy()
    df_teams.columns = ["Ataque (Local)", "Defensa (Local)", "Ataque (Visitante)", "Defensa (Visitante)"]
    st.dataframe(df_teams.round(2), use_container_width=True)