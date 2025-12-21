"""
📊 DASHBOARD WEB
Interface visual com gráficos para análise financeira
"""
from flask import Flask, render_template, jsonify, request, send_file
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging
import threading

logger = logging.getLogger(__name__)

# Importa serviços
try:
    from bot_multidelivery.services.financial_service import financial_service
    from bot_multidelivery.services.projection_service import projection_service
    from bot_multidelivery.services.export_service import export_service
except ImportError:
    logger.warning("Serviços não importados - dashboard em modo standalone")
    financial_service = None
    projection_service = None
    export_service = None


app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.config['JSON_AS_ASCII'] = False


@app.route('/')
def index():
    """Página principal do dashboard"""
    return render_template('dashboard.html')


@app.route('/api/daily_data')
def get_daily_data():
    """API: Dados diários dos últimos 30 dias"""
    try:
        days = int(request.args.get('days', 30))
        
        if not financial_service:
            return jsonify({'error': 'Serviço financeiro não disponível'}), 503
        
        data = []
        end_date = datetime.now()
        
        for i in range(days):
            date = end_date - timedelta(days=days - i - 1)
            report = financial_service.get_daily_report(date)
            
            if report:
                data.append({
                    'date': report.date,
                    'revenue': report.revenue,
                    'delivery_costs': report.delivery_costs,
                    'other_costs': report.other_costs,
                    'net_profit': report.net_profit,
                    'total_packages': report.total_packages,
                    'total_deliveries': report.total_deliveries
                })
        
        return jsonify(data)
    
    except Exception as e:
        logger.error(f"Erro ao buscar dados diários: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/weekly_data')
def get_weekly_data():
    """API: Dados semanais"""
    try:
        if not financial_service:
            return jsonify({'error': 'Serviço financeiro não disponível'}), 503
        
        # Busca últimas 8 semanas
        data = []
        end_date = datetime.now()
        
        for i in range(8):
            week_end = end_date - timedelta(weeks=i)
            week_start = week_end - timedelta(days=6)
            
            report = financial_service.get_weekly_report(week_start)
            
            if report:
                data.append({
                    'week_start': report.week_start,
                    'week_end': report.week_end,
                    'gross_profit': report.gross_profit,
                    'reserve_amount': report.reserve_amount,
                    'distributable_profit': report.distributable_profit,
                    'partner_1_share': report.partner_1_share,
                    'partner_2_share': report.partner_2_share
                })
        
        return jsonify(data[::-1])  # Inverte para ordem cronológica
    
    except Exception as e:
        logger.error(f"Erro ao buscar dados semanais: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/monthly_summary')
def get_monthly_summary():
    """API: Resumo mensal"""
    try:
        month = request.args.get('month')
        year = request.args.get('year')
        
        if not financial_service:
            return jsonify({'error': 'Serviço financeiro não disponível'}), 503
        
        if month and year:
            summary = financial_service.get_month_summary(int(year), int(month))
        else:
            summary = financial_service.get_month_summary()
        
        return jsonify(summary)
    
    except Exception as e:
        logger.error(f"Erro ao buscar resumo mensal: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/projections')
def get_projections():
    """API: Projeções futuras"""
    try:
        days = int(request.args.get('days', 7))
        
        if not projection_service:
            return jsonify({'error': 'Serviço de projeção não disponível'}), 503
        
        predictions = projection_service.predict_next_days(days)
        growth = projection_service.analyze_growth_rate()
        
        return jsonify({
            'predictions': predictions,
            'growth_analysis': growth
        })
    
    except Exception as e:
        logger.error(f"Erro ao gerar projeções: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/excel')
def export_excel():
    """API: Exporta para Excel"""
    try:
        days = int(request.args.get('days', 30))
        
        if not financial_service or not export_service:
            return jsonify({'error': 'Serviços não disponíveis'}), 503
        
        # Busca dados
        reports = []
        end_date = datetime.now()
        
        for i in range(days):
            date = end_date - timedelta(days=days - i - 1)
            report = financial_service.get_daily_report(date)
            
            if report:
                reports.append({
                    'date': report.date,
                    'revenue': report.revenue,
                    'delivery_costs': report.delivery_costs,
                    'other_costs': report.other_costs,
                    'net_profit': report.net_profit,
                    'total_packages': report.total_packages,
                    'total_deliveries': report.total_deliveries
                })
        
        # Exporta
        filepath = export_service.export_to_excel(reports)
        
        return send_file(filepath, as_attachment=True)
    
    except Exception as e:
        logger.error(f"Erro ao exportar Excel: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/pdf')
def export_pdf():
    """API: Exporta para PDF"""
    try:
        days = int(request.args.get('days', 30))
        
        if not financial_service or not export_service:
            return jsonify({'error': 'Serviços não disponíveis'}), 503
        
        # Busca dados
        reports = []
        end_date = datetime.now()
        week_start = end_date - timedelta(days=6)
        
        for i in range(days):
            date = end_date - timedelta(days=days - i - 1)
            report = financial_service.get_daily_report(date)
            
            if report:
                reports.append({
                    'date': report.date,
                    'revenue': report.revenue,
                    'delivery_costs': report.delivery_costs,
                    'other_costs': report.other_costs,
                    'net_profit': report.net_profit,
                    'total_packages': report.total_packages,
                    'total_deliveries': report.total_deliveries
                })
        
        # Busca configuração de sócios
        config = financial_service.partner_config
        
        # Busca relatório semanal
        weekly_report = financial_service.get_weekly_report(week_start)
        weekly_summary = None
        if weekly_report:
            weekly_summary = {
                'gross_profit': weekly_report.gross_profit,
                'reserve_amount': weekly_report.reserve_amount,
                'distributable_profit': weekly_report.distributable_profit,
                'partner_1_share': weekly_report.partner_1_share,
                'partner_2_share': weekly_report.partner_2_share
            }
        
        # Exporta
        filepath = export_service.export_to_pdf(
            reports,
            week_start=week_start,
            week_end=end_date,
            partner_config={
                'partner_1_name': config.partner_1_name,
                'partner_2_name': config.partner_2_name,
                'partner_1_share': config.partner_1_share,
                'partner_2_share': config.partner_2_share,
                'reserve_percentage': config.reserve_percentage
            },
            weekly_summary=weekly_summary
        )
        
        return send_file(filepath, as_attachment=True)
    
    except Exception as e:
        logger.error(f"Erro ao exportar PDF: {e}")
        return jsonify({'error': str(e)}), 500


def start_dashboard(host='0.0.0.0', port=5000, debug=False):
    """
    Inicia servidor do dashboard
    
    Args:
        host: Host para bind
        port: Porta para bind
        debug: Modo debug
    """
    logger.info(f"Iniciando dashboard em http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


def start_dashboard_thread(host='0.0.0.0', port=5000):
    """Inicia dashboard em thread separada"""
    thread = threading.Thread(
        target=start_dashboard,
        args=(host, port, False),
        daemon=True
    )
    thread.start()
    logger.info(f"Dashboard iniciado em thread separada: http://{host}:{port}")
    return thread


if __name__ == '__main__':
    start_dashboard(debug=True)
