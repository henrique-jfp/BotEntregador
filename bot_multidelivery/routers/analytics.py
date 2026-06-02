# -*- coding: utf-8 -*-
"""
🧠 Analytics Router: Geração de Insights Geográficos
Transforma dados brutos de entregas em inteligência de negócio
"""
import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
from collections import defaultdict
from datetime import datetime, timedelta
from sqlalchemy import text
from bot_multidelivery.database import db_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics"])


def get_neighborhood_from_coords(lat: float, lng: float) -> str:
    """
    Identifica bairro baseado em coordenadas.
    TODO: Integrar com GeoJSON para precisão (atual: heurística simples)
    """
    # Heurística simplificada para Zona Sul do Rio
    # Copacabana: lat -22.96 a -22.98, lng -43.17 a -43.19
    # Ipanema: lat -22.98 a -23.00, lng -43.19 a -43.21
    # Leblon: lat -22.98 a -23.01, lng -43.21 a -43.23
    
    if -22.98 <= lat <= -22.96 and -43.19 <= lng <= -43.17:
        return "Copacabana"
    elif -23.00 <= lat <= -22.98 and -43.21 <= lng <= -43.19:
        return "Ipanema"
    elif -23.01 <= lat <= -22.98 and -43.23 <= lng <= -43.21:
        return "Leblon"
    elif -22.95 <= lat <= -22.93 and -43.19 <= lng <= -43.17:
        return "Botafogo"
    elif -22.93 <= lat <= -22.91 and -43.21 <= lng <= -43.19:
        return "Lagoa"
    elif -23.03 <= lat <= -23.01 and -43.25 <= lng <= -43.23:
        return "São Conrado"
    else:
        return "Zona Sul"


@router.get("/neighborhood-stats")
async def get_neighborhood_stats(days: int = 7):
    """
    Retorna estatísticas simples por bairro para o dashboard
    Formato esperado pelo frontend: { neighborhoods: [{ name, total_deliveries, success_rate }] }
    """
    try:
        if not db_manager.is_connected:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")

        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        query = text("""
            SELECT 
                p.lat AS delivery_lat,
                p.lng AS delivery_lng,
                p.status AS status
            FROM packages p
            WHERE p.lat IS NOT NULL 
              AND p.lng IS NOT NULL
              AND DATE(COALESCE(p.delivered_at, p.created_at)) >= :start_date
        """)

        with db_manager.get_session() as session:
            deliveries = session.execute(query, {"start_date": start_date}).fetchall()

        neighborhood_data = defaultdict(lambda: {"total": 0, "success": 0})

        for delivery in deliveries:
            lat, lng, status = delivery
            neighborhood = get_neighborhood_from_coords(lat, lng)
            neighborhood_data[neighborhood]["total"] += 1
            if status == "delivered":
                neighborhood_data[neighborhood]["success"] += 1

        neighborhoods = []
        for name, data in neighborhood_data.items():
            total = data["total"]
            success_rate = (data["success"] / total * 100) if total > 0 else 0
            neighborhoods.append({
                "name": name,
                "total_deliveries": total,
                "success_rate": round(success_rate, 1)
            })

        neighborhoods.sort(key=lambda x: x["total_deliveries"], reverse=True)

        return {"neighborhoods": neighborhoods, "period_days": days}

    except Exception as e:
        logger.error(f"❌ Erro ao gerar analytics de neighborhoods: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar analytics: {str(e)}")


@router.get("/heatmap")
async def get_heatmap_data(days: int = 7):
    """
    🎨 Retorna dados para renderizar mapa de calor inteligente
    
    Returns:
    - neighborhood_stats: Volume e performance por bairro
    - failure_heatmap: Coordenadas de insucessos (manchas vermelhas)
    - top_performers: Melhores entregadores por região
    """
    try:
        if not db_manager.is_connected:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        # Período de análise
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # ==== 1. BUSCAR TODAS AS ENTREGAS DO PERÍODO ====
        query = text("""
            SELECT 
                p.lat AS delivery_lat,
                p.lng AS delivery_lng,
                p.status AS status,
                d.name AS deliverer_name,
                p.delivered_at AS delivered_at,
                p.notes AS failure_reason,
                p.created_at AS created_at
            FROM packages p
            LEFT JOIN deliverers d ON p.assigned_to_telegram_id = d.telegram_id
            WHERE p.lat IS NOT NULL 
              AND p.lng IS NOT NULL
              AND DATE(COALESCE(p.delivered_at, p.created_at)) >= :start_date
        """)
        
        with db_manager.get_session() as session:
            deliveries = session.execute(query, {"start_date": start_date}).fetchall()
        
        # ==== 2. AGRUPAR POR BAIRRO ====
        neighborhood_data = defaultdict(lambda: {
            'total': 0,
            'success': 0,
            'failures': 0,
            'deliverers': defaultdict(int),
            'failure_reasons': defaultdict(int),
            'avg_time': [],
            'coords': []
        })
        
        failure_points = []  # Para heatmap de problemas
        
        for delivery in deliveries:
            lat, lng, status, deliverer_name, delivered_at, failure_reason, created_at = delivery
            
            # Identificar bairro
            neighborhood = get_neighborhood_from_coords(lat, lng)
            
            # Acumular métricas
            neighborhood_data[neighborhood]['total'] += 1
            neighborhood_data[neighborhood]['coords'].append([lat, lng])
            
            if status == 'delivered':
                neighborhood_data[neighborhood]['success'] += 1
            else:
                neighborhood_data[neighborhood]['failures'] += 1
                failure_points.append({
                    'lat': lat,
                    'lng': lng,
                    'intensity': 0.8,
                    'reason': failure_reason or 'Não especificado'
                })
                neighborhood_data[neighborhood]['failure_reasons'][failure_reason or 'Não especificado'] += 1
            
            # Rastrear entregadores
            if deliverer_name:
                neighborhood_data[neighborhood]['deliverers'][deliverer_name] += 1
        
        # ==== 3. CALCULAR ESTATÍSTICAS POR BAIRRO ====
        neighborhood_stats = []
        
        for neighborhood, data in neighborhood_data.items():
            total = data['total']
            success_rate = (data['success'] / total * 100) if total > 0 else 0
            
            # Melhor entregador (top performer)
            top_deliverer = max(data['deliverers'].items(), key=lambda x: x[1])[0] if data['deliverers'] else "N/A"
            top_deliverer_count = data['deliverers'][top_deliverer] if data['deliverers'] else 0
            
            # Motivo de falha mais comum
            top_failure_reason = max(data['failure_reasons'].items(), key=lambda x: x[1])[0] if data['failure_reasons'] else "N/A"
            
            # Centro do bairro (média das coordenadas)
            center_lat = sum(c[0] for c in data['coords']) / len(data['coords'])
            center_lng = sum(c[1] for c in data['coords']) / len(data['coords'])
            
            neighborhood_stats.append({
                'name': neighborhood,
                'volume': total,
                'success_rate': round(success_rate, 1),
                'failures': data['failures'],
                'top_deliverer': top_deliverer,
                'top_deliverer_deliveries': top_deliverer_count,
                'top_failure_reason': top_failure_reason,
                'center': [center_lat, center_lng],
                'color_intensity': min(total / 50, 1.0)  # Normalizar para cor (max 50 entregas = 100%)
            })
        
        return {
            'neighborhood_stats': sorted(neighborhood_stats, key=lambda x: x['volume'], reverse=True),
            'failure_heatmap': failure_points[:200],  # Limitar para performance
            'period_days': days,
            'total_deliveries': sum(d['volume'] for d in neighborhood_stats),
            'generated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar analytics de heatmap: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar analytics: {str(e)}")


@router.get("/neighborhood/{name}")
async def get_neighborhood_detail(name: str, days: int = 7):
    """
    🔍 Detalhes de um bairro específico (para modal ao clicar)
    """
    try:
        if not db_manager.is_connected:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Buscar todas entregas (filtro por bairro será feito em memória por agora)
        query = text("""
            SELECT 
                p.lat AS delivery_lat,
                p.lng AS delivery_lng,
                p.status AS status,
                d.name AS deliverer_name,
                p.delivered_at AS delivered_at,
                p.notes AS failure_reason,
                p.created_at AS created_at
            FROM packages p
            LEFT JOIN deliverers d ON p.assigned_to_telegram_id = d.telegram_id
            WHERE p.lat IS NOT NULL 
              AND p.lng IS NOT NULL
              AND DATE(COALESCE(p.delivered_at, p.created_at)) >= :start_date
        """)
        
        with db_manager.get_session() as session:
            deliveries = session.execute(query, {"start_date": start_date}).fetchall()
        
        # Filtrar por bairro
        neighborhood_deliveries = [
            d for d in deliveries 
            if get_neighborhood_from_coords(d[0], d[1]) == name
        ]
        
        if not neighborhood_deliveries:
            raise HTTPException(status_code=404, detail=f"Nenhuma entrega encontrada para {name}")
        
        # Calcular estatísticas detalhadas
        total = len(neighborhood_deliveries)
        success = sum(1 for d in neighborhood_deliveries if d[2] == 'delivered')
        
        deliverer_stats = defaultdict(lambda: {'total': 0, 'success': 0})
        failure_reasons = defaultdict(int)
        
        for d in neighborhood_deliveries:
            deliverer = d[3]
            if deliverer:
                deliverer_stats[deliverer]['total'] += 1
                if d[2] == 'delivered':
                    deliverer_stats[deliverer]['success'] += 1
            
            if d[2] != 'delivered':
                failure_reasons[d[5] or 'Não especificado'] += 1
        
        # Top performers
        top_deliverers = sorted(
            [
                {
                    'name': name,
                    'total_deliveries': stats['total'],
                    'success_rate': round(stats['success'] / stats['total'] * 100, 1)
                }
                for name, stats in deliverer_stats.items()
            ],
            key=lambda x: x['success_rate'],
            reverse=True
        )[:5]
        
        return {
            'neighborhood': name,
            'total_deliveries': total,
            'success_rate': round(success / total * 100, 1),
            'total_failures': total - success,
            'top_deliverers': top_deliverers,
            'failure_breakdown': [
                {'reason': reason, 'count': count}
                for reason, count in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)
            ],
            'period_days': days
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao buscar detalhes do bairro {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
