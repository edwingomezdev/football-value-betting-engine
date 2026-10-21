class ValueBettingEngine:
    def __init__(self, kelly_fraction=0.25):
        """
        Engine para calcular Valor Esperado (EV) y tamaño de apuesta según Criterio de Kelly.
        kelly_fraction: Fracción de Kelly para mitigar la varianza (0.25 = Quarter Kelly, recomendado en la industria).
        """
        self.kelly_fraction = kelly_fraction

    def calculate_ev(self, model_prob, bookmaker_odds):
        """Calcula el Expected Value (EV) en porcentaje."""
        if bookmaker_odds <= 1.0:
            return 0.0
        ev = (model_prob * bookmaker_odds) - 1
        return round(ev, 4)

    def calculate_kelly_stake(self, model_prob, bookmaker_odds, bankroll):
        """Calcula el monto sugerido a apostar según la fórmula de Kelly ajustada."""
        b = bookmaker_odds - 1  # Ganancia neta por unidad apostada
        q = 1 - model_prob      # Probabilidad de perder
        p = model_prob          # Probabilidad de ganar
        
        kelly_percentage = (b * p - q) / b if b > 0 else 0
        
        # Aplicar fracción de Kelly para gestión prudente del riesgo
        adjusted_kelly = max(0, kelly_percentage * self.kelly_fraction)
        suggested_stake = bankroll * adjusted_kelly
        
        return round(suggested_stake, 2), round(adjusted_kelly * 100, 2)

    def analyze_opportunity(self, match_prediction, bookmaker_odds_dict, bankroll=1000):
        """
        Compara las cuotas del modelo con las cuotas reales del mercado (1X2).
        bookmaker_odds_dict = {'home': 1.80, 'draw': 3.50, 'away': 4.20}
        """
        outcomes = [
            ('Home (1)', match_prediction['prob_home'], bookmaker_odds_dict.get('home', 1.0)),
            ('Draw (X)', match_prediction['prob_draw'], bookmaker_odds_dict.get('draw', 1.0)),
            ('Away (2)', match_prediction['prob_away'], bookmaker_odds_dict.get('away', 1.0))
        ]
        
        recommendations = []
        for name, prob, odds in outcomes:
            ev = self.calculate_ev(prob, odds)
            stake, pct = self.calculate_kelly_stake(prob, odds, bankroll)
            
            is_value = ev > 0.02  # Mínimo 2% de valor positivo para recomendar
            
            recommendations.append({
                'market': name,
                'model_prob': f"{prob*100:.1f}%",
                'bookmaker_odds': odds,
                'fair_odds': round(1/prob, 2) if prob > 0 else 0,
                'ev': f"{ev*100:.2f}%",
                'is_value_bet': is_value,
                'suggested_stake': f"${stake} ({pct}%)" if is_value else "$0.00 (0%)"
            })
            
        return recommendations

# Prueba ejecutable del módulo
if __name__ == '__main__':
    from model import PoissonModel
    
    # 1. Cargar modelo
    model = PoissonModel('data/SP1.csv')
    prediction = model.predict_match('Real Madrid', 'Barcelona')
    
    # 2. Simular cuotas ofrecidas por la casa de apuestas en el mercado
    # (En este ejemplo, la casa ofrece una cuota inflada para el Real Madrid de 1.85 cuando la cuota justa del modelo es 1.54)
    market_odds = {
        'home': 1.85, 
        'draw': 3.80, 
        'away': 4.50
    }
    
    # 3. Analizar valor con un bankroll de $1000
    engine = ValueBettingEngine()
    opportunities = engine.analyze_opportunity(prediction, market_odds, bankroll=1000)
    
    print("\n--- ANÁLISIS DE OPORTUNIDADES DE VALOR (VALUE BETS) ---")
    for opp in opportunities:
        print(f"\nMercado: {opp['market']}")
        print(f"Probabilidad Modelo: {opp['model_prob']} | Cuota Casa: {opp['bookmaker_odds']} (Cuota Justa: {opp['fair_odds']})")
        print(f"Valor Esperado (EV): {opp['ev']}")
        print(f"¿Es Apuesta con Valor?: {'SÍ' if opp['is_value_bet'] else 'NO'}")
        print(f"Apuesta Sugerida: {opp['suggested_stake']}")