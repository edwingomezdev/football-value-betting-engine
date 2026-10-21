import pandas as pd
import numpy as np
from scipy.stats import poisson

class PoissonModel:
    def __init__(self, csv_path):
        """Carga el dataset de partidos y calcula promedios generales de la liga."""
        self.df = pd.read_csv(csv_path)
        # Filtrar columnas esenciales
        self.df = self.df[['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']].dropna()
        
        # Promedio general de goles marcados en la liga
        self.avg_home_goals = self.df['FTHG'].mean()
        self.avg_away_goals = self.df['FTAG'].mean()
        
        self._calculate_team_strengths()

    def _calculate_team_strengths(self):
        """Calcula las fuerzas de ataque y defensa de cada equipo."""
        # Rendimiento de local
        home_stats = self.df.groupby('HomeTeam').agg(
            home_goals_scored=('FTHG', 'mean'),
            home_goals_conceded=('FTAG', 'mean')
        )
        
        # Rendimiento de visitante
        away_stats = self.df.groupby('AwayTeam').agg(
            away_goals_scored=('FTAG', 'mean'),
            away_goals_conceded=('FTHG', 'mean')
        )
        
        # Combinar estadísticas
        self.teams_df = pd.concat([home_stats, away_stats], axis=1).fillna(0)
        
        # Fuerzas relativas
        self.teams_df['attack_home'] = self.teams_df['home_goals_scored'] / self.avg_home_goals
        self.teams_df['defense_home'] = self.teams_df['home_goals_conceded'] / self.avg_away_goals
        
        self.teams_df['attack_away'] = self.teams_df['away_goals_scored'] / self.avg_away_goals
        self.teams_df['defense_away'] = self.teams_df['away_goals_conceded'] / self.avg_home_goals

    def predict_match(self, home_team, away_team, max_goals=6):
        """Calcula las probabilidades 1X2 para un partido específico usando Poisson."""
        if home_team not in self.teams_df.index or away_team not in self.teams_df.index:
            raise ValueError(f"Uno o ambos equipos ('{home_team}', '{away_team}') no se encuentran en el dataset.")
        
        # Goles esperados (Lambda λ)
        lambda_home = (self.teams_df.loc[home_team, 'attack_home'] * 
                       self.teams_df.loc[away_team, 'defense_away'] * 
                       self.avg_home_goals)
        
        lambda_away = (self.teams_df.loc[away_team, 'attack_away'] * 
                       self.teams_df.loc[home_team, 'defense_home'] * 
                       self.avg_away_goals)
        
        # Matriz de Marcadores Probables
        matrix = np.zeros((max_goals, max_goals))
        for i in range(max_goals):
            for j in range(max_goals):
                matrix[i, j] = poisson.pmf(i, lambda_home) * poisson.pmf(j, lambda_away)
        
        # Sumar probabilidades para 1, X, 2
        prob_home = float(np.sum(np.tril(matrix, -1)))
        prob_draw = float(np.sum(np.diag(matrix)))
        prob_away = float(np.sum(np.triu(matrix, 1)))
        
        return {
            'home_team': home_team,
            'away_team': away_team,
            'expected_goals_home': round(lambda_home, 2),
            'expected_goals_away': round(lambda_away, 2),
            'prob_home': round(prob_home, 4),
            'prob_draw': round(prob_draw, 4),
            'prob_away': round(prob_away, 4),
            'fair_odds_home': round(1 / prob_home, 2) if prob_home > 0 else 0,
            'fair_odds_draw': round(1 / prob_draw, 2) if prob_draw > 0 else 0,
            'fair_odds_away': round(1 / prob_away, 2) if prob_away > 0 else 0,
        }

# Bloque de prueba ejecutable
if __name__ == '__main__':
    model = PoissonModel('data/SP1.csv')
    test_match = model.predict_match('Real Madrid', 'Barcelona')
    print("\n--- PRUEBA DE PREDICCIÓN CON DATOS REALES ---")
    for key, val in test_match.items():
        print(f"{key}: {val}")