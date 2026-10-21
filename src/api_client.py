import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

class FootballDataAPI:
    def __init__(self):
        self.api_key = os.getenv("FOOTBALL_DATA_API_KEY")
        self.base_url = "https://api.football-data.org/v4"
        self.headers = {"X-Auth-Token": self.api_key} if self.api_key else {}

    def get_competitions(self):
        """Devuelve las ligas disponibles en la capa gratuita."""
        return {
            "UEFA Champions League": "CL",
            "Premier League (Inglaterra)": "PL",
            "LaLiga (España)": "PD",
            "Serie A (Italia)": "SA",
            "Bundesliga (Alemania)": "BL1",
            "Ligue 1 (Francia)": "FL1"
        }

    def fetch_matches_data(self, competition_code="PD"):
        """Descarga partidos terminados para alimentar el modelo de Poisson."""
        url = f"{self.base_url}/competitions/{competition_code}/matches"
        params = {"status": "FINISHED"}
        
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code != 200:
            raise Exception(f"Error en FootballDataAPI ({response.status_code})")
            
        matches = response.json().get("matches", [])
        parsed_matches = []
        for match in matches:
            home_team = match["homeTeam"]["name"]
            away_team = match["awayTeam"]["name"]
            score_home = match["score"]["fullTime"]["home"]
            score_away = match["score"]["fullTime"]["away"]
            
            if score_home is not None and score_away is not None:
                parsed_matches.append({
                    "HomeTeam": home_team,
                    "AwayTeam": away_team,
                    "FTHG": score_home,
                    "FTAG": score_away
                })
                
        return pd.DataFrame(parsed_matches)

    def fetch_live_match_score(self, home_team, away_team):
        """Busca partidos en curso (IN_PLAY) y retorna marcador y minuto en vivo."""
        url = f"{self.base_url}/matches"
        params = {"status": "IN_PLAY"}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                matches = response.json().get("matches", [])
                for match in matches:
                    h_name = match["homeTeam"]["name"]
                    a_name = match["awayTeam"]["name"]
                    
                    if home_team.lower() in h_name.lower() or h_name.lower() in home_team.lower():
                        return {
                            "is_live": True,
                            "minute": match.get("minute", 45),
                            "score_home": match["score"]["fullTime"]["home"] or 0,
                            "score_away": match["score"]["fullTime"]["away"] or 0
                        }
        except Exception:
            pass
            
        return {"is_live": False, "minute": 0, "score_home": 0, "score_away": 0}