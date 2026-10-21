import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from scipy.stats import poisson
from src.api_client import FootballDataAPI
from src.odds_api_client import OddsAPIClient
from src.model import PoissonModel
from src.value_engine import ValueBettingEngine

st.set_page_config(
    page_title="Football Value Betting Engine (Live & Props)",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ Motor Cuantitativo Avanzado: Resultado, Faltas, Tarjetas y Combinadas")
st.markdown("Plataforma de análisis probabilístico basado en **Poisson** para mercado principal (1X2), **Props** (Faltas/Tarjetas) y **Simulador de Apuestas Combinadas**.")

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

currencies = {
    "COP (Peso Colombiano)": "$",
    "MXN (Peso Mexicano)": "$",
    "USD (Dólar estadounidense)": "$",
    "EUR (Euro)": "€"
}

# Configuración General
st.sidebar.header("🌍 Configuración General")
selected_league_label = st.sidebar.selectbox("Liga / Torneo", list(leagues_map.keys()), index=0)
fd_code, odds_key = leagues_map[selected_league_label]

selected_currency_name = st.sidebar.selectbox("Moneda", list(currencies.keys()), index=0)
currency_symbol = currencies[selected_currency_name]

@st.cache_data(ttl=3600)
def load_historical_data(code):
    return fd_api.fetch_matches_data(code)

@st.cache_data(ttl=600)
def load_live_odds(key):
    return odds_api.fetch_live_odds(key)

with st.spinner("Cargando modelo de estadísticas y cuotas..."):
    try:
        try:
            df_matches = load_historical_data(fd_code)
        except Exception:
            df_matches = pd.read_csv('data/SP1.csv')
            
        model = PoissonModel(df_matches)
        available_teams_model = sorted(list(model.teams_df.index))
        live_events = load_live_odds(odds_key)
        st.sidebar.success(f"¡{len(live_events)} encuentros sincronizados!")
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        st.stop()

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Selección del Partido")

if live_events:
    event_options = [f"{e['home_team']} vs {e['away_team']}" for e in live_events]
    selected_event_idx = st.sidebar.selectbox("Encuentro", range(len(event_options)), format_func=lambda x: event_options[x])
    selected_event = live_events[selected_event_idx]
    
    home_team_default = selected_event['home_team']
    away_team_default = selected_event['away_team']
    
    auto_odds = selected_event['odds']
    default_home_odd = auto_odds.get('home', 2.0)
    default_draw_odd = auto_odds.get('draw', 3.0)
    default_away_odd = auto_odds.get('away', 3.5)
    bookmaker_name = auto_odds.get('bookmaker_name', 'Mercado')
    
    st.sidebar.info(f"📍 Casa proveedora: **{bookmaker_name}**")
else:
    home_team_default = available_teams_model[0]
    away_team_default = available_teams_model[1] if len(available_teams_model) > 1 else available_teams_model[0]
    default_home_odd, default_draw_odd, default_away_odd = 1.85, 3.80, 4.50

home_team = st.sidebar.text_input("Equipo Local", value=home_team_default)
away_team = st.sidebar.text_input("Equipo Visitante", value=away_team_default)

# --- ESTADO EN VIVO (LIVE TRACKER) ---
st.sidebar.markdown("---")
st.sidebar.header("⏱️ Estado del Partido en Vivo")
is_live = st.sidebar.checkbox("¿El partido está en curso (En Vivo)?", value=False)

if is_live:
    live_minute = st.sidebar.slider("Minuto del Partido", min_value=1, max_value=90, value=35)
    live_score_home = st.sidebar.number_input(f"Goles {home_team}", min_value=0, value=1)
    live_score_away = st.sidebar.number_input(f"Goles {away_team}", min_value=0, value=0)
    red_cards_home = st.sidebar.number_input(f"Tarjetas Rojas {home_team}", min_value=0, value=0)
    red_cards_away = st.sidebar.number_input(f"Tarjetas Rojas {away_team}", min_value=0, value=0)
else:
    live_minute = 0
    live_score_home, live_score_away = 0, 0
    red_cards_home, red_cards_away = 0, 0

# Ajustar por tarjetas rojas
for t in [home_team, away_team]:
    if t not in model.teams_df.index:
        model.teams_df.loc[t] = [model.avg_home_goals, model.avg_away_goals, model.avg_away_goals, model.avg_home_goals, 1.0, 1.0, 1.0, 1.0]

if red_cards_home > 0:
    model.teams_df.loc[home_team, 'attack_home'] *= (0.75 ** red_cards_home)
    model.teams_df.loc[home_team, 'defense_home'] *= (1.25 ** red_cards_home)
if red_cards_away > 0:
    model.teams_df.loc[away_team, 'attack_away'] *= (0.75 ** red_cards_away)
    model.teams_df.loc[away_team, 'defense_away'] *= (1.25 ** red_cards_away)

# Cuotas
st.sidebar.subheader("💰 Cuotas 1X2")
odds_home = st.sidebar.number_input(f"Cuota Local ({home_team})", min_value=1.01, value=float(default_home_odd), step=0.05)
odds_draw = st.sidebar.number_input("Cuota Empate (X)", min_value=1.01, value=float(default_draw_odd), step=0.05)
odds_away = st.sidebar.number_input(f"Cuota Visitante ({away_team})", min_value=1.01, value=float(default_away_odd), step=0.05)

prediction = model.predict_match(home_team, away_team)

# Reajuste de tiempo restante si está en vivo
if is_live:
    time_factor = (90 - live_minute) / 90.0
    prediction['expected_goals_home'] = round(prediction['expected_goals_home'] * time_factor, 2)
    prediction['expected_goals_away'] = round(prediction['expected_goals_away'] * time_factor, 2)

engine = ValueBettingEngine()
market_odds = {'home': odds_home, 'draw': odds_draw, 'away': odds_away}

# Pestañas Principales
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💵 Calculadora y Simulación", 
    "🟨 Mercado de Faltas y Tarjetas", 
    "🔗 Constructor de Combinadas", 
    "🔥 Marcadores Exactos (%)", 
    "📈 Métricas de Equipos"
])

# --- PESTAÑA 1: CALCULADORA Y SIMULACIÓN ---
with tab1:
    if is_live:
        st.warning(f"🚨 **PARTIDO EN VIVO ({live_minute}')** — Marcador Actual: {home_team} {live_score_home} - {live_score_away} {away_team}")

    st.subheader("💵 Calculadora Directa de Ganancias")
    col_input, col_market = st.columns(2)
    with col_input:
        user_bet_amount = st.number_input(
            f"Monto a Apostar ({currency_symbol})",
            min_value=1000.0 if "COP" in selected_currency_name else 1.0,
            value=10000.0 if "COP" in selected_currency_name else 10.0,
            step=1000.0 if "COP" in selected_currency_name else 5.0
        )
    with col_market:
        selected_market_bet = st.selectbox(
            "Seleccionar Mercado 1X2",
            [f"Gana Local ({home_team}) @ {odds_home}", f"Empate (X) @ {odds_draw}", f"Gana Visitante ({away_team}) @ {odds_away}"]
        )
    
    if "Gana Local" in selected_market_bet:
        chosen_odd, chosen_prob = odds_home, prediction['prob_home']
    elif "Empate" in selected_market_bet:
        chosen_odd, chosen_prob = odds_draw, prediction['prob_draw']
    else:
        chosen_odd, chosen_prob = odds_away, prediction['prob_away']

    retorno_total = user_bet_amount * chosen_odd
    ganancia_neta = user_bet_amount * (chosen_odd - 1)
    ev_calculado = (chosen_prob * chosen_odd) - 1

    c1, c2, c3 = st.columns(3)
    c1.metric("Retorno Total (Cobro)", f"{currency_symbol}{retorno_total:,.2f}")
    c2.metric("Ganancia Neta Limpia", f"{currency_symbol}{ganancia_neta:,.2f}")
    c3.metric("Valor Esperado (EV)", f"{ev_calculado*100:.2f}%", delta="🟢 Con Valor" if ev_calculado > 0.02 else "🔴 Sin Valor")

    if ev_calculado > 0.02:
        st.success(f"✅ **DECISIÓN:** Apostar {currency_symbol}{user_bet_amount:,.2f}. El modelo confirma ventaja matemática (Retorno esperado: +{ev_calculado*100:.2f}%).")
    else:
        st.error(f"❌ **DECISIÓN:** NO APOSTAR. La cuota no compensa el riesgo estadístico.")

# --- PESTAÑA 2: FALTAS Y TARJETAS ---
with tab2:
    st.subheader("🟨 Modelado Estadístico de Faltas y Tarjetas (Props)")
    st.markdown("Estimación mediante distribución de Poisson basada en promedios históricos del equipo y nivel de severidad del arbitraje:")

    col_fouls_1, col_fouls_2 = st.columns(2)
    with col_fouls_1:
        avg_referee_cards = st.slider("Promedio de Tarjetas del Árbitro por Partido", min_value=2.0, max_value=8.0, value=4.5, step=0.1)
        line_cards = st.number_input("Línea de Tarjetas de la Casa (Over/Under)", min_value=1.5, max_value=8.5, value=4.5, step=1.0)
        cards_odds_over = st.number_input("Cuota Over Tarjetas", min_value=1.01, value=1.85, step=0.05)
    
    with col_fouls_2:
        # Probabilidad acumulada de Poisson para Tarjetas Over
        prob_under_cards = sum([poisson.pmf(i, avg_referee_cards) for i in range(int(np.floor(line_cards)) + 1)])
        prob_over_cards = 1.0 - prob_under_cards
        ev_cards = (prob_over_cards * cards_odds_over) - 1

        st.metric("Promedio Esperado de Tarjetas", f"{avg_referee_cards:.1f}")
        st.write(f"**Probabilidad Over {line_cards} Tarjetas:** {prob_over_cards*100:.1f}% *(Cuota Justa: `{1/prob_over_cards:.2f}`)*")
        st.write(f"**Valor Esperado (EV):** `{ev_cards*100:.2f}%`")
        
        if ev_cards > 0.02:
            st.success(f"🟢 **APUESTA CON VALOR EN PROPS:** Apostar al Over {line_cards} Tarjetas @ {cards_odds_over}")
        else:
            st.error("🔴 **SIN VALOR:** No se recomienda entrar a la línea de tarjetas seleccionada.")

# --- PESTAÑA 3: CONSTRUCTOR DE COMBINADAS ---
with tab3:
    st.subheader("🔗 Estimador de Apuestas Combinadas (Parley / Bet Builder)")
    st.markdown("Calcula la probabilidad real conjunta multiplicando eventos independientes:")

    col_par1, col_par2 = st.columns(2)
    with col_par1:
        leg1_prob = st.slider("Probabilidad Leg 1 (ej. Resultado Partido)", min_value=10, max_value=95, value=int(prediction['prob_home']*100)) / 100.0
        leg1_odds = st.number_input("Cuota Leg 1", min_value=1.01, value=float(odds_home))
        
        leg2_prob = st.slider("Probabilidad Leg 2 (ej. Over Tarjetas)", min_value=10, max_value=95, value=int(prob_over_cards*100)) / 100.0
        leg2_odds = st.number_input("Cuota Leg 2", min_value=1.01, value=float(cards_odds_over))

    with col_par2:
        combined_odds = leg1_odds * leg2_odds
        combined_prob = leg1_prob * leg2_prob
        ev_combined = (combined_prob * combined_odds) - 1

        st.metric("Cuota Total Combinada", f"{combined_odds:.2f}")
        st.metric("Probabilidad Conjunta Real", f"{combined_prob*100:.1f}%")
        st.metric("EV de la Combinada", f"{ev_combined*100:.2f}%", delta="🟢 Combinada Rentable" if ev_combined > 0.02 else "🔴 Sin Valor")

# --- PESTAÑA 4: MARCADORES EXACTOS ---
with tab4:
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
    fig.update_layout(height=480, width=580)
    st.plotly_chart(fig, use_container_width=True)

# --- PESTAÑA 5: MÉTRICAS DE EQUIPOS (RESTAURADAS) ---
with tab5:
    st.subheader("📈 Métricas Históricas de Fuerza Ofensiva y Defensiva")
    st.markdown("Valores calculados respecto al promedio general de la competición (1.0 = Promedio Liga):")
    
    df_teams = model.teams_df[['attack_home', 'defense_home', 'attack_away', 'defense_away']].copy()
    df_teams.columns = ["Ataque (Local)", "Defensa (Local)", "Ataque (Visitante)", "Defensa (Visitante)"]
    
    st.dataframe(df_teams.round(2), use_container_width=True)