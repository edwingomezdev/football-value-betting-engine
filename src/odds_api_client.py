import os
import requests
from dotenv import load_dotenv

load_dotenv()

class OddsAPIClient:
    def __init__(self):
        self.api_key = os.getenv("ODDS_API_KEY")
        self.base_url = "https://api.the-odds-api.com/v4/sports"

    def get_supported_leagues(self):
        """Devuelve los códigos de las ligas principales incluyendo la Champions League."""
        return {
            "UEFA Champions League": "soccer_uefa_champs_league",
            "Premier League (Inglaterra)": "soccer_epl",
            "LaLiga (España)": "soccer_spain_la_liga",
            "Serie A (Italia)": "soccer_italy_serie_a",
            "Bundesliga (Alemania)": "soccer_germany_bundesliga",
            "Ligue 1 (Francia)": "soccer_france_ligue_one"
        }

    def fetch_live_odds(self, sport_key="soccer_uefa_champs_league", regions="eu", markets="h2h"):
        """Descarga partidos próximos y cuotas en tiempo real."""
        if not self.api_key:
            raise Exception("ODDS_API_KEY no encontrada en el archivo .env")

        url = f"{self.base_url}/{sport_key}/odds/"
        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
            "oddsFormat": "decimal"
        }

        response = requests.get(url, params=params)
        if response.status_code != 200:
            raise Exception(f"Error en The Odds API ({response.status_code}): {response.json().get('message', 'Sin acceso')}")

        data = response.json()
        parsed_events = []
        for event in data:
            home_team = event.get("home_team")
            away_team = event.get("away_team")
            bookmakers = event.get("bookmakers", [])

            odds_data = {"home": 1.0, "draw": 1.0, "away": 1.0, "bookmaker_name": "N/A"}
            
            if bookmakers:
                bm = bookmakers[0]
                odds_data["bookmaker_name"] = bm.get("title", "Desconocido")
                
                for market in bm.get("markets", []):
                    if market.get("key") == "h2h":
                        for outcome in market.get("outcomes", []):
                            name = outcome.get("name")
                            price = outcome.get("price")
                            if name == home_team:
                                odds_data["home"] = price
                            elif name == away_team:
                                odds_data["away"] = price
                            elif name == "Draw":
                                odds_data["draw"] = price

            parsed_events.append({
                "id": event.get("id"),
                "commence_time": event.get("commence_time"),
                "home_team": home_team,
                "away_team": away_team,
                "odds": odds_data
            })

        return parsed_events