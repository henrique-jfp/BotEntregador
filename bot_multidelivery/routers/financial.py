# -*- coding: utf-8 -*-
from fastapi import APIRouter
from bot_multidelivery.persistence import data_store
from datetime import datetime, timedelta

router = APIRouter(prefix="/financial", tags=["Financial"])

def get_current_week_financials():
    """Helper para buscar finanças da semana atual"""
    today = datetime.now()
    start_week = today - timedelta(days=today.weekday()) # Segunda
    end_week = start_week + timedelta(days=6) # Domingo

    reports = data_store.get_financial_reports(start_week, end_week)
    
    total_rev = sum(r.total_revenue for r in reports)
    total_cost = sum(r.total_cost for r in reports)
    net_profit = total_rev - total_cost

    return {
        "start_date": start_week.strftime('%Y-%m-%d'),
        "end_date": end_week.strftime('%Y-%m-%d'),
        "revenue": total_rev,
        "costs": total_cost,
        "profit": net_profit,
        "days_closed": len(reports)
    }

@router.get("/balance")
async def get_financial_balance(user_id: int):
    """
    Retorna resumo financeiro para o painel.
    Se for sócio/admin, vê o lucro da empresa. Se for entregador, vê seus ganhos.
    """
    from bot_multidelivery.persistence import data_store
    
    week_data = get_current_week_financials()
    
    # Verificar se é admin/sócio ou entregador
    deliverer = data_store.get_deliverer(user_id)
    
    # Admin IDs conhecidos (pode vir de env var futuramente)
    import os
    admin_id = os.getenv('ADMIN_TELEGRAM_ID', '')
    is_admin = str(user_id) == admin_id
    
    if is_admin or (deliverer and deliverer.is_partner):
        # Visão da empresa
        return {
            "view": "company",
            "balance": week_data["profit"],
            "revenue": week_data["revenue"],
            "costs": week_data["costs"],
            "period": "Semana Atual",
            "currency": "BRL",
            "days_closed": week_data["days_closed"]
        }
    elif deliverer:
        # Visão pessoal do entregador
        # TODO: Calcular ganhos reais do entregador
        personal_balance = week_data["profit"] * 0.3  # Placeholder: 30% do lucro
        return {
            "view": "personal",
            "balance": personal_balance,
            "period": "Semana Atual",
            "currency": "BRL"
        }
    else:
        # Guest ou não cadastrado - retorna visão pessoal vazia
        return {
            "view": "personal",
            "balance": 0.0,
            "period": "Semana Atual",
            "currency": "BRL"
        }

@router.get("/session/{session_id}")
async def get_session_financials(session_id: str):
    """Retorna detalhes financeiros de uma sessão específica"""
    # Exemplo: Retorna dados mockados ou carrega do histórico
    # Como a lógica completa financeiro é complexa e estava no api_routes gigante
    # vamos deixar o stub aqui pronto para ser expandido.
    return {
        "session_id": session_id,
        "revenue": 0.0,
        "costs": 0.0,
        "profit": 0.0,
        "details": "Not implemented yet in modular router (TODO)"
    }


@router.post("/daily-closure")
async def daily_closure(request: dict):
    """
    Processa fechamento financeiro diário
    Recebe custos, receitas e salários para salvar no sistema
    """
    from bot_multidelivery.services.financial_service import FinancialService
    from datetime import datetime
    
    try:
        financial_service = FinancialService()
        
        # Extrair dados do request
        date_str = request.get('date', datetime.now().strftime('%Y-%m-%d'))
        revenue = float(request.get('revenue', 0))
        delivery_costs = float(request.get('delivery_costs', 0))
        other_costs = float(request.get('other_costs', 0))
        net_profit = float(request.get('net_profit', 0))
        total_packages = int(request.get('total_packages', 0))
        total_deliveries = int(request.get('total_deliveries', 0))
        deliverer_breakdown = request.get('deliverer_breakdown', {})
        expenses = request.get('expenses', [])
        
        # Converter deliverer_breakdown de {telegram_id: value} para {name: value}
        deliverer_costs = {}
        for telegram_id_str, cost in deliverer_breakdown.items():
            deliverer = data_store.get_deliverer(int(telegram_id_str))
            if deliverer:
                deliverer_costs[deliverer.name] = float(cost)
        
        # Salvar relatório diário (corrigido)
        report = financial_service.close_day(
            date=datetime.strptime(date_str, '%Y-%m-%d'),
            revenue=revenue,
            deliverer_costs=deliverer_costs,
            other_costs=other_costs,
            total_packages=total_packages,
            total_deliveries=total_deliveries,
            expenses=expenses
        )
        
        return {
            "status": "success",
            "message": "Fechamento diário salvo com sucesso",
            "report": {
                "date": report.date,
                "revenue": report.revenue,
                "net_profit": report.net_profit,
                "total_packages": report.total_packages
            }
        }
    
    except Exception as e:
        import logging
        logging.error(f"❌ Erro ao salvar fechamento diário: {e}")
        return {
            "status": "error",
            "message": str(e)
        }, 500
