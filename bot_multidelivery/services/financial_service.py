"""
💰 SERVIÇO FINANCEIRO EMPRESARIAL
Sistema completo de gestão financeira com:
- Fechamento diário (receitas vs custos)
- Fechamento semanal (reserva + divisão de lucros)
- Relatórios detalhados
- Histórico persistente
"""
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class DailyFinancialReport:
    """Relatório financeiro diário"""
    date: str  # YYYY-MM-DD
    revenue: float  # Receita bruta do dia
    delivery_costs: float  # Custos com entregadores
    other_costs: float  # Outros custos operacionais
    net_profit: float  # Lucro líquido
    total_packages: int
    total_deliveries: int
    deliverer_breakdown: Dict[str, float]  # {nome: custo}
    expenses: List[dict] = None  # Lista detalhada de despesas [{type, value, desc}]
    
    def to_dict(self) -> dict:
        data = asdict(self)
        if self.expenses is None:
            data['expenses'] = []
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DailyFinancialReport':
        # Compatibilidade com dados antigos sem expenses
        if 'expenses' not in data:
            data['expenses'] = []
        return cls(**data)


@dataclass
class WeeklyFinancialReport:
    """Relatório financeiro semanal com divisão de lucros"""
    week_start: str  # YYYY-MM-DD
    week_end: str
    total_revenue: float
    total_delivery_costs: float
    total_operational_costs: float
    gross_profit: float  # Lucro bruto
    
    reserve_amount: float  # 10% reserva (do lucro bruto)
    distributable_profit: float  # 90% para distribuir
    
    partner_1_share: float  # 70% do distribuível
    partner_2_share: float  # 30% do distribuível
    
    daily_reports: List[str]  # Lista de datas dos relatórios diários
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'WeeklyFinancialReport':
        return cls(**data)


@dataclass
class PartnerConfig:
    """Configuração dos sócios"""
    partner_1_name: str
    partner_1_share: float  # Percentual (0.70 = 70%)
    partner_2_name: str
    partner_2_share: float  # Percentual (0.30 = 30%)
    reserve_percentage: float  # Percentual de reserva (0.10 = 10%)


class FinancialService:
    """Serviço de gestão financeira empresarial"""
    
    def __init__(self, data_dir: str = "data/financial"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.daily_dir = self.data_dir / "daily"
        self.weekly_dir = self.data_dir / "weekly"
        self.config_file = self.data_dir / "config.json"
        
        self.daily_dir.mkdir(exist_ok=True)
        self.weekly_dir.mkdir(exist_ok=True)
        
        self._load_or_create_config()
    
    def _load_or_create_config(self):
        """Carrega ou cria configuração padrão dos sócios"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.partner_config = PartnerConfig(**data)
        else:
            # Configuração padrão
            self.partner_config = PartnerConfig(
                partner_1_name="Sócio 1",
                partner_1_share=0.70,  # 70%
                partner_2_name="Sócio 2",
                partner_2_share=0.30,  # 30%
                reserve_percentage=0.10  # 10%
            )
            self._save_config()
    
    def _save_config(self):
        """Salva configuração dos sócios"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.partner_config), f, indent=2, ensure_ascii=False)
    
    def update_partner_config(
        self,
        partner_1_name: Optional[str] = None,
        partner_1_share: Optional[float] = None,
        partner_2_name: Optional[str] = None,
        partner_2_share: Optional[float] = None,
        reserve_percentage: Optional[float] = None
    ):
        """Atualiza configuração dos sócios"""
        if partner_1_name:
            self.partner_config.partner_1_name = partner_1_name
        if partner_1_share is not None:
            self.partner_config.partner_1_share = partner_1_share
        if partner_2_name:
            self.partner_config.partner_2_name = partner_2_name
        if partner_2_share is not None:
            self.partner_config.partner_2_share = partner_2_share
        if reserve_percentage is not None:
            self.partner_config.reserve_percentage = reserve_percentage
        
        self._save_config()
    
    def close_day(
        self,
        date: datetime,
        revenue: float,
        deliverer_costs: Dict[str, float],
        other_costs: float = 0.0,
        total_packages: int = 0,
        total_deliveries: int = 0,
        expenses: List[dict] = None
    ) -> DailyFinancialReport:
        """
        Fecha o dia financeiro
        """
        date_str = date.strftime('%Y-%m-%d')
        
        # Calcula custos totais com entregadores
        total_delivery_costs = sum(deliverer_costs.values())
        
        # Se other_costs for 0 mas tivermos lista detalhada, calcula da lista
        if other_costs == 0.0 and expenses:
            other_costs = sum(e['value'] for e in expenses)
        
        # Lucro líquido do dia
        net_profit = revenue - total_delivery_costs - other_costs
        
        report = DailyFinancialReport(
            date=date_str,
            revenue=revenue,
            delivery_costs=total_delivery_costs,
            other_costs=other_costs,
            net_profit=net_profit,
            total_packages=total_packages,
            total_deliveries=total_deliveries,
            deliverer_breakdown=deliverer_costs,
            expenses=expenses or []
        )
            deliverer_breakdown=deliverer_costs
        )
        
        # Salva relatório
        filename = self.daily_dir / f"daily_{date_str}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Fechamento diário salvo: {date_str} | Lucro: R$ {net_profit:.2f}")
        return report
    
    def get_daily_report(self, date: datetime) -> Optional[DailyFinancialReport]:
        """Busca relatório diário específico"""
        date_str = date.strftime('%Y-%m-%d')
        filename = self.daily_dir / f"daily_{date_str}.json"
        
        if not filename.exists():
            return None
        
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return DailyFinancialReport.from_dict(data)
    
    def get_daily_reports_range(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[DailyFinancialReport]:
        """Busca relatórios diários em um intervalo"""
        reports = []
        current = start_date
        
        while current <= end_date:
            report = self.get_daily_report(current)
            if report:
                reports.append(report)
            current += timedelta(days=1)
        
        return reports
    
    def close_week(
        self,
        week_start: datetime,
        operational_costs: float = 0.0
    ) -> Tuple[WeeklyFinancialReport, str]:
        """
        Fecha a semana financeira e divide lucros
        
        Args:
            week_start: Data de início da semana (segunda-feira)
            operational_costs: Custos operacionais da semana (aluguel, contas, etc)
        
        Returns:
            (WeeklyFinancialReport, mensagem_formatada)
        """
        # Calcula fim da semana (domingo)
        week_end = week_start + timedelta(days=6)
        
        # Busca relatórios diários da semana
        daily_reports = self.get_daily_reports_range(week_start, week_end)
        
        if not daily_reports:
            raise ValueError("Nenhum relatório diário encontrado para a semana especificada")
        
        # Soma totais
        total_revenue = sum(r.revenue for r in daily_reports)
        total_delivery_costs = sum(r.delivery_costs for r in daily_reports)
        total_other_costs = sum(r.other_costs for r in daily_reports)
        
        # Adiciona custos operacionais semanais
        total_operational_costs = total_other_costs + operational_costs
        
        # Lucro bruto = Receita - Todos os custos
        gross_profit = total_revenue - total_delivery_costs - total_operational_costs
        
        # Reserva de 10% do lucro bruto
        reserve_amount = gross_profit * self.partner_config.reserve_percentage
        
        # Lucro distribuível = 90% do lucro bruto
        distributable_profit = gross_profit - reserve_amount
        
        # Divisão entre sócios (70/30)
        partner_1_share = distributable_profit * self.partner_config.partner_1_share
        partner_2_share = distributable_profit * self.partner_config.partner_2_share
        
        # Cria relatório semanal
        report = WeeklyFinancialReport(
            week_start=week_start.strftime('%Y-%m-%d'),
            week_end=week_end.strftime('%Y-%m-%d'),
            total_revenue=total_revenue,
            total_delivery_costs=total_delivery_costs,
            total_operational_costs=total_operational_costs,
            gross_profit=gross_profit,
            reserve_amount=reserve_amount,
            distributable_profit=distributable_profit,
            partner_1_share=partner_1_share,
            partner_2_share=partner_2_share,
            daily_reports=[r.date for r in daily_reports]
        )
        
        # Salva relatório semanal
        filename = self.weekly_dir / f"week_{week_start.strftime('%Y-%m-%d')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        
        # Gera mensagem formatada
        message = self._format_weekly_report(report)
        
        logger.info(f"Fechamento semanal salvo: {week_start.strftime('%Y-%m-%d')}")
        return report, message
    
    def _format_weekly_report(self, report: WeeklyFinancialReport) -> str:
        """Formata relatório semanal para exibição"""
        cfg = self.partner_config
        
        msg = f"""💰 <b>FECHAMENTO SEMANAL</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 <b>Período:</b> {report.week_start} a {report.week_end}
📊 <b>Dias com dados:</b> {len(report.daily_reports)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💵 RECEITAS E CUSTOS</b>

📈 Receita Total: <b>R$ {report.total_revenue:,.2f}</b>
📦 Custos Entregadores: R$ {report.total_delivery_costs:,.2f}
🏢 Custos Operacionais: R$ {report.total_operational_costs:,.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💰 LUCRO BRUTO</b>
<b>R$ {report.gross_profit:,.2f}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📊 DISTRIBUIÇÃO</b>

🏦 <b>Reserva Empresa ({cfg.reserve_percentage*100:.0f}%):</b>
   R$ {report.reserve_amount:,.2f}

💼 <b>Lucro Distribuível ({(1-cfg.reserve_percentage)*100:.0f}%):</b>
   R$ {report.distributable_profit:,.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>👥 DIVISÃO ENTRE SÓCIOS</b>

🤝 <b>{cfg.partner_1_name} ({cfg.partner_1_share*100:.0f}%):</b>
   <b>R$ {report.partner_1_share:,.2f}</b>

🤝 <b>{cfg.partner_2_name} ({cfg.partner_2_share*100:.0f}%):</b>
   <b>R$ {report.partner_2_share:,.2f}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ <b>Fechamento concluído com sucesso!</b>"""
        
        return msg
    
    def get_weekly_report(self, week_start: datetime) -> Optional[WeeklyFinancialReport]:
        """Busca relatório semanal específico"""
        filename = self.weekly_dir / f"week_{week_start.strftime('%Y-%m-%d')}.json"
        
        if not filename.exists():
            return None
        
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return WeeklyFinancialReport.from_dict(data)
    
    def get_month_summary(self, year: int, month: int) -> Dict:
        """Gera resumo financeiro do mês"""
        start_date = datetime(year, month, 1)
        
        # Último dia do mês
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        
        # Busca todos os relatórios diários do mês
        daily_reports = self.get_daily_reports_range(start_date, end_date)
        
        if not daily_reports:
            return {
                'has_data': False,
                'message': 'Nenhum dado encontrado para este mês'
            }
        
        # Calcula totais
        total_revenue = sum(r.revenue for r in daily_reports)
        total_delivery_costs = sum(r.delivery_costs for r in daily_reports)
        total_other_costs = sum(r.other_costs for r in daily_reports)
        total_profit = sum(r.net_profit for r in daily_reports)
        total_packages = sum(r.total_packages for r in daily_reports)
        total_deliveries = sum(r.total_deliveries for r in daily_reports)
        
        # Médias
        days_with_data = len(daily_reports)
        avg_revenue = total_revenue / days_with_data
        avg_profit = total_profit / days_with_data
        
        # Melhor e pior dia
        best_day = max(daily_reports, key=lambda r: r.net_profit)
        worst_day = min(daily_reports, key=lambda r: r.net_profit)
        
        return {
            'has_data': True,
            'month': f"{month:02d}/{year}",
            'days_with_data': days_with_data,
            'total_revenue': total_revenue,
            'total_delivery_costs': total_delivery_costs,
            'total_other_costs': total_other_costs,
            'total_profit': total_profit,
            'total_packages': total_packages,
            'total_deliveries': total_deliveries,
            'avg_revenue_per_day': avg_revenue,
            'avg_profit_per_day': avg_profit,
            'best_day': {
                'date': best_day.date,
                'profit': best_day.net_profit
            },
            'worst_day': {
                'date': worst_day.date,
                'profit': worst_day.net_profit
            }
        }
    
    def format_daily_report(self, report: DailyFinancialReport) -> str:
        """Formata relatório diário para exibição"""
        msg = f"""💰 <b>FECHAMENTO DO DIA</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 Data: <b>{report.date}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📊 RESUMO OPERACIONAL</b>

📦 Pacotes Processados: {report.total_packages}
✅ Entregas Realizadas: {report.total_deliveries}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💵 FINANCEIRO</b>

📈 Receita Bruta: <b>R$ {report.revenue:,.2f}</b>
📦 Custos Entregadores: R$ {report.delivery_costs:,.2f}
🏢 Outros Custos: R$ {report.other_costs:,.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💰 LUCRO LÍQUIDO</b>
<b>R$ {report.net_profit:,.2f}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💸 CUSTOS POR ENTREGADOR:</b>
"""
        
        for name, cost in sorted(report.deliverer_breakdown.items()):
            emoji = "🤝" if cost == 0 else "💼"
            msg += f"\n{emoji} {name}: R$ {cost:,.2f}"
        
        return msg
    
    def format_month_summary(self, summary: Dict) -> str:
        """Formata resumo mensal para exibição"""
        if not summary['has_data']:
            return f"❌ {summary['message']}"
        
        msg = f"""📊 <b>RESUMO MENSAL</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📅 Mês: <b>{summary['month']}</b>
📆 Dias com dados: {summary['days_with_data']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💵 TOTAIS DO MÊS</b>

📈 Receita Total: <b>R$ {summary['total_revenue']:,.2f}</b>
📦 Custos Entregadores: R$ {summary['total_delivery_costs']:,.2f}
🏢 Outros Custos: R$ {summary['total_other_costs']:,.2f}

<b>💰 Lucro Total: R$ {summary['total_profit']:,.2f}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📊 OPERAÇÃO</b>

📦 Total Pacotes: {summary['total_packages']:,}
✅ Total Entregas: {summary['total_deliveries']:,}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>📈 MÉDIAS DIÁRIAS</b>

💵 Receita: R$ {summary['avg_revenue_per_day']:,.2f}
💰 Lucro: R$ {summary['avg_profit_per_day']:,.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🏆 MELHOR DIA</b>
{summary['best_day']['date']}: R$ {summary['best_day']['profit']:,.2f}

<b>📉 PIOR DIA</b>
{summary['worst_day']['date']}: R$ {summary['worst_day']['profit']:,.2f}"""
        
        return msg


# Instância global do serviço
financial_service = FinancialService()
