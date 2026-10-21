import pandas as pd
import numpy as np
from scipy.stats import poisson

class PoissonModel:
    def __init__(self, data_source):
        """Acepta tanto una ruta a un archivo CSV como un DataFrame de Pandas directamente."""
        if isinstance(data_source, str):
            self.df = pd.read_csv(data_source)
        elif isinstance(data_source, pd.DataFrame):
            self.df = data_source.copy()
        else:
            raise ValueError("data_source debe ser una ruta string o un DataFrame de Pandas.")
            
        self.df = self.df[['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']].dropna()
        
        self.avg_home_goals = self.df['FTHG'].mean()
        self.avg_away_goals = self.df['FTAG'].mean()
        
        self._calculate_team_strengths()

    def _calculate_team_strengths(self):
        home_stats = self.df.groupby('HomeTeam').agg(
            home_goals_scored=('FTHG', 'mean'),
            home_goals_conceded=('FTAG', 'mean')
        )
        away_stats = self.df.groupby('AwayTeam').agg(
            away_goals_scored=('FTAG', 'mean'),
            away_goals_conceded=('FTHG', 'mean')
        )
        
        self.teams_df = pd.concat([home_stats, away_stats], axis=1).fillna(0)
        
        self.teams_df['attack_home'] = self.teams_df['home_goals_scored'] / (self.avg_home_goals if self.avg_home_goals > 0 else 1)
        self.teams_df['defense_home'] = self.teams_df['home_goals_conceded'] / (self.avg_away_goals if self.avg_away_goals > 0 else 1)
        
        self.teams_df['attack_away'] = self.teams_df['away_goals_scored'] / (self.avg_away_goals if self.avg_away_goals > 0 else 1)
        self.teams_df['defense_away'] = self.teams_df['home_goals_conceded'] / (self.avg_home_goals if self.avg_home_goals > 0 else 1)

    def predict_match(self, home_team, away_team, max_goals=6):
        if home_team not in self.teams_df.index or away_team not in self.teams_df.index:
            raise ValueError(f"Equipos '{home_team}' o '{away_team}' no encontrados.")
        
        lambda_home = (self.teams_df.loc[home_team, 'attack_home'] * 
                       self.teams_df.loc[away_team, 'defense_away'] * 
                       self.avg_home_goals)
        
        lambda_away = (self.teams_df.loc[away_team, 'attack_away'] * 
                       self.teams_df.loc[home_team, 'defense_home'] * 
                       self.avg_away_goals)
        
        matrix = np.zeros((max_goals, max_goals))
        for i in range(max_goals):
            for j in range(max_goals):
                matrix[i, j] = poisson.pmf(i, lambda_home) * poisson.pmf(j, lambda_away)
        
        prob_home = float(np.sum(np.tril(matrix, -1)))
        prob_draw = float(np.sum(np.diag(matrix)))
        prob_away = float(np.sum(np.triu(matrix, 1)))
        
        return {
            'home_team': home_team,
            'away_team': away_team,
            'expected_goals_home': round(lambda_home, 2),
            'expected_goals_away': round(lambda_away, 2),
            'matrix': matrix,
            'prob_home': round(prob_home, 4),
            'prob_draw': round(prob_draw, 4),
            'prob_away': round(prob_away, 4),
            'fair_odds_home': round(1 / prob_home, 2) if prob_home > 0 else 0,
            'fair_odds_draw': round(1 / prob_draw, 2) if prob_draw > 0 else 0,
            'fair_odds_away': round(1 / prob_away, 2) if prob_away > 0 else 0,
        }