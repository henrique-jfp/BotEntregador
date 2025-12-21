"""
🔮 SERVIÇO DE PROJEÇÕES
Machine Learning para prever lucros futuros
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import json
import logging
from pathlib import Path
import statistics

logger = logging.getLogger(__name__)


class ProjectionService:
    """Serviço de projeções de lucro com análise preditiva"""
    
    def __init__(self, data_dir: str = "data/financial"):
        self.data_dir = Path(data_dir)
        self.daily_dir = self.data_dir / "daily"
    
    def _load_historical_data(self, days: int = 90) -> List[Dict]:
        """
        Carrega dados históricos
        
        Args:
            days: Número de dias para trás
        
        Returns:
            Lista de relatórios diários
        """
        reports = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        current_date = start_date
        while current_date <= end_date:
            filename = f"{current_date.strftime('%Y-%m-%d')}.json"
            filepath = self.daily_dir / filename
            
            if filepath.exists():
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        report = json.load(f)
                        reports.append(report)
                except Exception as e:
                    logger.warning(f"Erro ao carregar {filename}: {e}")
            
            current_date += timedelta(days=1)
        
        return reports
    
    def _calculate_trend(self, values: List[float]) -> float:
        """
        Calcula tendência usando regressão linear simples
        
        Args:
            values: Lista de valores
        
        Returns:
            Coeficiente angular (tendência)
        """
        if len(values) < 2:
            return 0.0
        
        n = len(values)
        x = list(range(n))
        y = values
        
        # Cálculo de regressão linear: y = ax + b
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(y)
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        return slope
    
    def _calculate_seasonality(self, reports: List[Dict]) -> Dict[int, float]:
        """
        Calcula sazonalidade por dia da semana
        
        Args:
            reports: Lista de relatórios
        
        Returns:
            Dicionário com multiplicador por dia da semana (0=segunda, 6=domingo)
        """
        weekday_profits = {i: [] for i in range(7)}
        
        for report in reports:
            date_str = report['date']
            date = datetime.strptime(date_str, '%Y-%m-%d')
            weekday = date.weekday()
            profit = report.get('net_profit', 0)
            
            weekday_profits[weekday].append(profit)
        
        # Calcula média por dia da semana
        weekday_avg = {}
        overall_avg = statistics.mean([p for profits in weekday_profits.values() for p in profits]) if reports else 1
        
        for weekday, profits in weekday_profits.items():
            if profits:
                avg = statistics.mean(profits)
                weekday_avg[weekday] = avg / overall_avg if overall_avg > 0 else 1.0
            else:
                weekday_avg[weekday] = 1.0
        
        return weekday_avg
    
    def predict_next_days(
        self,
        days: int = 7,
        historical_days: int = 30
    ) -> List[Dict]:
        """
        Prevê lucros dos próximos dias
        
        Args:
            days: Número de dias para prever
            historical_days: Dias históricos para análise
        
        Returns:
            Lista de previsões
        """
        # Carrega histórico
        reports = self._load_historical_data(historical_days)
        
        if not reports:
            logger.warning("Sem dados históricos para projeção")
            return []
        
        # Extrai valores
        revenues = [r['revenue'] for r in reports]
        delivery_costs = [r['delivery_costs'] for r in reports]
        other_costs = [r['other_costs'] for r in reports]
        profits = [r['net_profit'] for r in reports]
        
        # Calcula médias
        avg_revenue = statistics.mean(revenues)
        avg_delivery_costs = statistics.mean(delivery_costs)
        avg_other_costs = statistics.mean(other_costs)
        avg_profit = statistics.mean(profits)
        
        # Calcula tendências
        revenue_trend = self._calculate_trend(revenues)
        profit_trend = self._calculate_trend(profits)
        
        # Calcula sazonalidade
        seasonality = self._calculate_seasonality(reports)
        
        # Gera previsões
        predictions = []
        start_date = datetime.now() + timedelta(days=1)
        
        for i in range(days):
            pred_date = start_date + timedelta(days=i)
            weekday = pred_date.weekday()
            
            # Aplica tendência
            days_ahead = i + 1
            predicted_revenue = avg_revenue + (revenue_trend * days_ahead)
            predicted_profit = avg_profit + (profit_trend * days_ahead)
            
            # Aplica sazonalidade
            seasonal_factor = seasonality.get(weekday, 1.0)
            predicted_revenue *= seasonal_factor
            predicted_profit *= seasonal_factor
            
            # Garante valores positivos
            predicted_revenue = max(0, predicted_revenue)
            predicted_profit = max(0, predicted_profit)
            
            # Estimativa de custos proporcional
            cost_ratio = (avg_delivery_costs + avg_other_costs) / avg_revenue if avg_revenue > 0 else 0.3
            predicted_costs = predicted_revenue * cost_ratio
            
            predictions.append({
                'date': pred_date.strftime('%Y-%m-%d'),
                'weekday': pred_date.strftime('%A'),
                'predicted_revenue': round(predicted_revenue, 2),
                'predicted_costs': round(predicted_costs, 2),
                'predicted_profit': round(predicted_profit, 2),
                'confidence': 'alta' if i < 3 else 'média' if i < 7 else 'baixa',
                'seasonal_factor': round(seasonal_factor, 2)
            })
        
        logger.info(f"Geradas {len(predictions)} previsões")
        return predictions
    
    def predict_week_profit(self, historical_days: int = 30) -> Dict:
        """
        Prevê lucro da próxima semana
        
        Args:
            historical_days: Dias históricos para análise
        
        Returns:
            Previsão semanal detalhada
        """
        daily_predictions = self.predict_next_days(7, historical_days)
        
        if not daily_predictions:
            return {
                'week_start': '',
                'week_end': '',
                'total_predicted_revenue': 0,
                'total_predicted_costs': 0,
                'total_predicted_profit': 0,
                'daily_breakdown': []
            }
        
        total_revenue = sum(p['predicted_revenue'] for p in daily_predictions)
        total_costs = sum(p['predicted_costs'] for p in daily_predictions)
        total_profit = sum(p['predicted_profit'] for p in daily_predictions)
        
        return {
            'week_start': daily_predictions[0]['date'],
            'week_end': daily_predictions[-1]['date'],
            'total_predicted_revenue': round(total_revenue, 2),
            'total_predicted_costs': round(total_costs, 2),
            'total_predicted_profit': round(total_profit, 2),
            'daily_breakdown': daily_predictions,
            'confidence': 'média'
        }
    
    def predict_month_profit(self, historical_days: int = 90) -> Dict:
        """
        Prevê lucro do próximo mês
        
        Args:
            historical_days: Dias históricos para análise
        
        Returns:
            Previsão mensal
        """
        daily_predictions = self.predict_next_days(30, historical_days)
        
        if not daily_predictions:
            return {
                'month': '',
                'total_predicted_revenue': 0,
                'total_predicted_costs': 0,
                'total_predicted_profit': 0,
                'weekly_breakdown': []
            }
        
        # Agrupa por semana
        weeks = []
        current_week = []
        
        for pred in daily_predictions:
            current_week.append(pred)
            
            if len(current_week) == 7:
                week_revenue = sum(p['predicted_revenue'] for p in current_week)
                week_costs = sum(p['predicted_costs'] for p in current_week)
                week_profit = sum(p['predicted_profit'] for p in current_week)
                
                weeks.append({
                    'week_start': current_week[0]['date'],
                    'week_end': current_week[-1]['date'],
                    'predicted_revenue': round(week_revenue, 2),
                    'predicted_costs': round(week_costs, 2),
                    'predicted_profit': round(week_profit, 2)
                })
                
                current_week = []
        
        # Adiciona semana parcial se houver
        if current_week:
            week_revenue = sum(p['predicted_revenue'] for p in current_week)
            week_costs = sum(p['predicted_costs'] for p in current_week)
            week_profit = sum(p['predicted_profit'] for p in current_week)
            
            weeks.append({
                'week_start': current_week[0]['date'],
                'week_end': current_week[-1]['date'],
                'predicted_revenue': round(week_revenue, 2),
                'predicted_costs': round(week_costs, 2),
                'predicted_profit': round(week_profit, 2)
            })
        
        total_revenue = sum(p['predicted_revenue'] for p in daily_predictions)
        total_costs = sum(p['predicted_costs'] for p in daily_predictions)
        total_profit = sum(p['predicted_profit'] for p in daily_predictions)
        
        next_month = datetime.now() + timedelta(days=1)
        
        return {
            'month': next_month.strftime('%B/%Y'),
            'total_predicted_revenue': round(total_revenue, 2),
            'total_predicted_costs': round(total_costs, 2),
            'total_predicted_profit': round(total_profit, 2),
            'weekly_breakdown': weeks,
            'confidence': 'baixa'
        }
    
    def analyze_growth_rate(self, days: int = 30) -> Dict:
        """
        Analisa taxa de crescimento
        
        Args:
            days: Período para análise
        
        Returns:
            Análise de crescimento
        """
        reports = self._load_historical_data(days)
        
        if len(reports) < 7:
            return {
                'growth_rate': 0,
                'trend': 'insuficiente',
                'analysis': 'Dados insuficientes para análise'
            }
        
        # Divide em duas metades
        mid = len(reports) // 2
        first_half = reports[:mid]
        second_half = reports[mid:]
        
        avg_first = statistics.mean([r['net_profit'] for r in first_half])
        avg_second = statistics.mean([r['net_profit'] for r in second_half])
        
        if avg_first == 0:
            growth_rate = 0
        else:
            growth_rate = ((avg_second - avg_first) / avg_first) * 100
        
        if growth_rate > 10:
            trend = 'crescimento forte'
        elif growth_rate > 5:
            trend = 'crescimento moderado'
        elif growth_rate > 0:
            trend = 'crescimento leve'
        elif growth_rate > -5:
            trend = 'estável'
        elif growth_rate > -10:
            trend = 'queda leve'
        else:
            trend = 'queda acentuada'
        
        return {
            'growth_rate': round(growth_rate, 2),
            'trend': trend,
            'avg_first_period': round(avg_first, 2),
            'avg_second_period': round(avg_second, 2),
            'analysis': f"Taxa de crescimento de {growth_rate:.1f}% ({trend})"
        }


# Instância global
projection_service = ProjectionService()
