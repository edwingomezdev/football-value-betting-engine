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

st.title("⚽ Motor Estadístico y de Apuestas de Valor en Fútbol")
st.markdown("Plataforma cuantitativa para identificar **Apuestas con Valor Esperado ($EV > 0$)** y gestión de riesgo en tiempo real.")

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

# Configuración Regional y Monedas
currencies = {
    "COP (Peso Colombiano)": "$",
    "MXN (Peso Mexicano)": "$",
    "USD (Dólar estadounidense)": "$",
    "EUR (Euro)": "€",
    "ARS (Peso Argentino)": "$"
}

# Barra Lateral: Configuración General
st.sidebar.header("🌍 Configuración General")
selected_league_label = st.sidebar.selectbox("Liga / Torneo", list(leagues_map.keys()), index=0)
fd_code, odds_key = leagues_map[selected_league_label]

selected_currency_name = st.sidebar.selectbox("Moneda del Bankroll", list(currencies.keys()), index=0)
currency_symbol = currencies[selected_currency_name]

# Cargar Datos
@st.cache_data(ttl=3600)
def load_historical_data(code):
    return fd_api.fetch_matches_data(code)

@st.cache_data(ttl=600)
def load_live_odds(key):
    return odds_api.fetch_live_odds(key)

with st.spinner("Cargando modelo estadístico y cuotas en tiempo real..."):
    try:
        try:
            df_matches = load_historical_data(fd_code)
        except Exception:
            df_matches = pd.read_csv('data/SP1.csv')
            
        model = PoissonModel(df_matches)
        available_teams_model = sorted(list(model.teams_df.index))
        live_events = load_live_odds(odds_key)
        st.sidebar.success(f"¡{len(live_events)} partidos listos con cuotas!")
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        st.stop()

# --- BANNER SUPERIOR DE OPORTUNIDADES DE VALOR DESTACADAS ---
st.markdown("### 🔥 Oportunidades de Apuestas de Valor Destacadas en Tiempo Real")
top_opportunities = []

if live_events:
    engine_temp = ValueBettingEngine()
    for ev_item in live_events:
        h_team = ev_item['home_team']
        a_team = ev_item['away_team']
        
        # Ajustar si el equipo no está en el histórico
        for t_name in [h_team, a_team]:
            if t_name not in model.teams_df.index:
                model.teams_df.loc[t_name] = [model.avg_home_goals, model.avg_away_goals, model.avg_away_goals, model.avg_home_goals, 1.0, 1.0, 1.0, 1.0]
        
        pred_temp = model.predict_match(h_team, a_team)
        opps_temp = engine_temp.analyze_opportunity(pred_temp, ev_item['odds'], bankroll=1000)
        
        for o in opps_temp:
            ev_val = float(o['ev'].replace('%', ''))
            if ev_val > 2.0:
                top_opportunities.append({
                    'Partido': f"{h_team} vs {a_team}",
                    'Mercado': o['market'],
                    'Cuota Casa': o['bookmaker_odds'],
                    'EV': f"{ev_val:.2f}%",
                    'Casa': ev_item['odds'].get('bookmaker_name', 'Mercado')
                })

if top_opportunities:
    df_banner = pd.DataFrame(top_opportunities).sort_values(by='EV', ascending=False).head(3)
    st.info("💡 **Oportunidades de alto valor identificadas para hoy:**")
    st.dataframe(df_banner, use_container_width=True)
else:
    st.warning("No se detectaron oportunidades con EV > +2.0% en los partidos próximos de esta competición.")

st.markdown("---")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Selección del Partido")

if live_events:
    event_options = [f"{e['home_team']} vs {e['away_team']}" for e in live_events]
    selected_event_idx = st.sidebar.selectbox("Seleccionar Encuentro", range(len(event_options)), format_func=lambda x: event_options[x])
    selected_event = live_events[selected_event_idx]
    
    home_team_default = selected_event['home_team']
    away_team_default = selected_event['away_team']
    
    auto_odds = selected_event['odds']
    default_home_odd = auto_odds.get('home', 2.0)
    default_draw_odd = auto_odds.get('draw', 3.0)
    default_away_odd = auto_odds.get('away', 3.5)
    bookmaker_name = auto_odds.get('bookmaker_name', 'Mercado')
    
    st.sidebar.info(f"📍 Cuotas de: **{bookmaker_name}**")
else:
    home_team_default = available_teams_model[0]
    away_team_default = available_teams_model[1] if len(available_teams_model) > 1 else available_teams_model[0]
    default_home_odd, default_draw_odd, default_away_odd = 1.85, 3.80, 4.50

home_team = st.sidebar.text_input("Equipo Local", value=home_team_default)
away_team = st.sidebar.text_input("Equipo Visitante", value=away_team_default)

bankroll = st.sidebar.number_input(f"Capital Disponible ({selected_currency_name})", min_value=10.0, value=100000.0 if "COP" in selected_currency_name else 1000.0, step=1000.0 if "COP" in selected_currency_name else 50.0)

st.sidebar.subheader("💰 Cuotas de la Casa de Apuestas")
odds_home = st.sidebar.number_input(f"Cuota Local ({home_team})", min_value=1.01, value=float(default_home_odd), step=0.05)
odds_draw = st.sidebar.number_input("Cuota Empate (X)", min_value=1.01, value=float(default_draw_odd), step=0.05)
odds_away = st.sidebar.number_input(f"Cuota Visitante ({away_team})", min_value=1.01, value=float(default_away_odd), step=0.05)

# Procesar Predicción
for t in [home_team, away_team]:
    if t not in model.teams_df.index:
        model.teams_df.loc[t] = [model.avg_home_goals, model.avg_away_goals, model.avg_away_goals, model.avg_home_goals, 1.0, 1.0, 1.0, 1.0]

prediction = model.predict_match(home_team, away_team)
engine = ValueBettingEngine()
market_odds = {'home': odds_home, 'draw': odds_draw, 'away': odds_away}
opportunities = engine.analyze_opportunity(prediction, market_odds, bankroll=bankroll)

# Pestañas
tab1, tab2, tab3 = st.tabs(["📊 Análisis y Diagnóstico", "🔥 Matriz de Marcadores Probables", "📈 Métricas de Equipos"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⚽ Goles Esperados (xG)")
        st.metric(f"xG {home_team}", prediction['expected_goals_home'])
        st.metric(f"xG {away_team}", prediction['expected_goals_away'])

    with col2:
        st.subheader("🎯 Probabilidades y Cuotas Justas")
        st.write(f"**Victoria Local ({home_team}):** {prediction['prob_home']*100:.1f}% *(Cuota Justa: `{prediction['fair_odds_home']}`)*")
        st.write(f"**Empate (X):** {prediction['prob_draw']*100:.1f}% *(Cuota Justa: `{prediction['fair_odds_draw']}`)*")
        st.write(f"**Victoria Visitante ({away_team}):** {prediction['prob_away']*100:.1f}% *(Cuota Justa: `{prediction['fair_odds_away']}`)*")

    st.markdown("---")
    st.subheader("💡 Decisiones de Apuesta (Diagnóstico en Tiempo Real)")
    
    has_value_any = False
    for opp in opportunities:
        ev_val = float(opp['ev'].replace('%', ''))
        market_label = opp['market'].replace('Home (1)', f'Gana Local ({home_team})').replace('Draw (X)', 'Empate (X)').replace('Away (2)', f'Gana Visitante ({away_team})')
        
        # Calcular monto en formato de moneda local
        pct_float = float(opp['suggested_stake'].split('(')[1].replace('%)', '')) / 100
        stake_amount = bankroll * pct_float
        
        if ev_val > 2.0:
            has_value_any = True
            st.success(f"🟢 **¡APOSTAR!** — Mercado: **{market_label}** | EV: **+{ev_val:.2f}%** | Apuesta Sugerida: **{currency_symbol}{stake_amount:,.2f}** ({pct_float*100:.2f}% del capital)")
        else:
            st.error(f"🔴 **NO APOSTAR** — Mercado: **{market_label}** | EV: **{ev_val:.2f}%** (Sin ventaja matemática)")

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
    st.subheader("🛡️ Métricas de Fuerza Ofensiva y Defensiva")
    df_teams = model.teams_df[['attack_home', 'defense_home', 'attack_away', 'defense_away']].copy()
    df_teams.columns = ["Ataque (Local)", "Defensa (Local)", "Ataque (Visitante)", "Defensa (Visitante)"]
    st.dataframe(df_teams.round(2), use_container_width=True)