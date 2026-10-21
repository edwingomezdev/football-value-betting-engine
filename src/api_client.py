import os
import requests
import pandas as pd
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

class FootballDataAPI:
    def __init__(self):
        self.api_key = os.getenv("FOOTBALL_DATA_API_KEY")
        self.base_url = "https://api.football-data.org/v4"
        self.headers = {"X-Auth-Token": self.api_key} if self.api_key else {}

    def get_competitions(self):
        """Devuelve las ligas disponibles en la capa gratuita."""
        return {
           "Premier League (Inglaterra)": "PL",
        "LaLiga (España)": "PD",
        "Serie A (Italia)": "SA",
        "Bundesliga (Alemania)": "BL1",
        "Ligue 1 (Francia)": "FL1",
        "Eredivisie (Países Bajos)": "DED",
        "Primeira Liga (Portugal)": "PPD"
        }

    def fetch_matches_data(self, competition_code="PD"):
        """Descarga los partidos terminados de la temporada actual para alimentar el modelo de Poisson."""
        url = f"{self.base_url}/competitions/{competition_code}/matches"
        params = {"status": "FINISHED"}
        
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code != 200:
            raise Exception(f"Error en la API ({response.status_code}): {response.json().get('message', 'Sin clave o límite excedido')}")
            
        data = response.json()
        matches = data.get("matches", [])
        
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
                
        df = pd.DataFrame(parsed_matches)
        return df

# Prueba directa
if __name__ == "__main__":
    client = FootballDataAPI()
    try:
        df_matches = client.fetch_matches_data("PL") # Probar Premier League
        print(f"¡Éxito! Se descargaron {len(df_matches)} partidos reales en tiempo real.")
        print(df_matches.head())
    except Exception as e:
        print(f"Atención: {e}")