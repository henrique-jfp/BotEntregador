"""
Router para Análise de Bairros (Neighborhoods Analytics)
Mapa de Calor e Estatísticas por Zona Geográfica

NOTA: Usa lat/lng para determinar bairros via bounding box,
pois o campo 'neighborhood' não existe no modelo PackageDB
"""
import logging
from fastapi import APIRouter, Query
from sqlalchemy import func, desc
from typing import Dict, List, Optional, Tuple
from bot_multidelivery.database import db_manager, PackageDB, DelivererDB
from datetime import datetime, timedelta

router = APIRouter(prefix="/stats", tags=["Analytics"])
logger = logging.getLogger(__name__)


# Bounding boxes aproximados dos bairros da Zona Sul do Rio
# Formato: (lat_min, lat_max, lng_min, lng_max)
BAIRROS_BOUNDS = {
    'Copacabana': (-22.990, -22.960, -43.195, -43.170),
    'Ipanema': (-22.995, -22.980, -43.215, -43.195),
    'Leblon': (-23.015, -22.995, -43.240, -43.215),
    'Lagoa': (-22.980, -22.960, -43.220, -43.195),
    'Jardim Botânico': (-22.975, -22.955, -43.235, -43.210),
    'Gávea': (-22.995, -22.975, -43.265, -43.235),
    'São Conrado': (-23.015, -22.990, -43.280, -43.255),
    'Laranjeiras': (-22.960, -22.935, -43.210, -43.185),
    'Flamengo': (-22.950, -22.925, -43.185, -43.165),
    'Botafogo': (-22.965, -22.940, -43.200, -43.175),
    'Urca': (-22.965, -22.950, -43.175, -43.155),
    'Humaitá': (-22.970, -22.955, -43.210, -43.190),
    'Catete': (-22.935, -22.920, -43.185, -43.170),
    'Glória': (-22.925, -22.905, -43.180, -43.165),
    'Centro': (-22.920, -22.890, -43.195, -43.165),
}

# Coordenadas centrais para exibição no mapa
BAIRROS_COORDS = {
    'Copacabana': {'lat': -22.974, 'lng': -43.182},
    'Ipanema': {'lat': -22.987, 'lng': -43.204},
    'Leblon': {'lat': -23.005, 'lng': -43.225},
    'Lagoa': {'lat': -22.971, 'lng': -43.208},
    'Jardim Botânico': {'lat': -22.963, 'lng': -43.222},
    'Gávea': {'lat': -22.984, 'lng': -43.251},
    'São Conrado': {'lat': -23.000, 'lng': -43.265},
    'Laranjeiras': {'lat': -22.948, 'lng': -43.197},
    'Flamengo': {'lat': -22.940, 'lng': -43.173},
    'Botafogo': {'lat': -22.953, 'lng': -43.194},
    'Urca': {'lat': -22.956, 'lng': -43.162},
    'Humaitá': {'lat': -22.962, 'lng': -43.200},
    'Catete': {'lat': -22.928, 'lng': -43.178},
    'Glória': {'lat': -22.915, 'lng': -43.172},
    'Centro': {'lat': -22.905, 'lng': -43.180},
}


def get_bairro_from_coords(lat: float, lng: float) -> Optional[str]:
    """
    Determina o bairro baseado nas coordenadas lat/lng
    usando bounding boxes aproximados
    """
    for bairro, bounds in BAIRROS_BOUNDS.items():
        lat_min, lat_max, lng_min, lng_max = bounds
        if lat_min <= lat <= lat_max and lng_min <= lng <= lng_max:
            return bairro
    return None


@router.get("/neighborhoods")
async def get_neighborhoods_stats(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    zone: Optional[str] = Query("south", description="Zona (south, north, west, center, east)")
):
    """
    Retorna estatísticas de entregas agrupadas por bairro
    
    Args:
        start_date: Data inicial (YYYY-MM-DD)
        end_date: Data final (YYYY-MM-DD)
        zone: Zona da cidade (padrão: sul - Zona Sul)
    
    Returns:
        Dict com formato:
        {
            "Copacabana": {
                "total_packages": 150,
                "success_count": 135,
                "failed_count": 15,
                "success_rate": 90.0,
                "top_deliverer": "João Silva",
                "avg_delivery_time": 45.2,
                "lat": -22.974,
                "lng": -43.182
            },
            ...
        }
    """
    try:
        with db_manager.get_session() as db:
            # Definir filtro de datas - filtrar coordenadas válidas
            query = db.query(PackageDB).filter(
                PackageDB.lat != 0,
                PackageDB.lng != 0
            )
            
            if start_date:
                try:
                    start = datetime.strptime(start_date, "%Y-%m-%d")
                    query = query.filter(PackageDB.created_at >= start)
                except ValueError:
                    pass
            
            if end_date:
                try:
                    end = datetime.strptime(end_date, "%Y-%m-%d")
                    end = end.replace(hour=23, minute=59, second=59)
                    query = query.filter(PackageDB.created_at <= end)
                except ValueError:
                    pass
            
            # Buscar todos os pacotes com coordenadas válidas
            all_packages = query.all()
            
            neighborhoods_data: Dict = {}
            
            # Processar dados por bairro (determinado via lat/lng)
            for package in all_packages:
                bairro = get_bairro_from_coords(package.lat, package.lng)
                
                if not bairro:
                    continue  # Pacote fora dos bairros mapeados
                
                if bairro not in neighborhoods_data:
                    neighborhoods_data[bairro] = {
                        'total': 0,
                        'success': 0,
                        'failed': 0,
                        'deliverers': {}
                    }
                
                neighborhoods_data[bairro]['total'] += 1
                
                # Contar sucessos e falhas
                if package.status == 'delivered':
                    neighborhoods_data[bairro]['success'] += 1
                    
                    # Registrar entregador com sucesso
                    if package.assigned_to_telegram_id:
                        deliverer = db.query(DelivererDB).filter(
                            DelivererDB.telegram_id == package.assigned_to_telegram_id
                        ).first()
                        
                        if deliverer:
                            if deliverer.name not in neighborhoods_data[bairro]['deliverers']:
                                neighborhoods_data[bairro]['deliverers'][deliverer.name] = 0
                            neighborhoods_data[bairro]['deliverers'][deliverer.name] += 1
                
                elif package.status == 'failed':
                    neighborhoods_data[bairro]['failed'] += 1
            
            # Formatar resposta final
            result = {}
            
            for bairro, data in neighborhoods_data.items():
                total = data['total']
                success = data['success']
                failed = data['failed']
                
                # Calcular taxa de sucesso
                success_rate = (success / total * 100) if total > 0 else 0
                
                # Encontrar top deliverer
                top_deliverer = None
                if data['deliverers']:
                    top_deliverer = max(data['deliverers'].items(), key=lambda x: x[1])[0]
                
                # Usar coordenadas do dicionário global
                coords = BAIRROS_COORDS.get(bairro, {'lat': 0, 'lng': 0})
                
                result[bairro] = {
                    'total_packages': total,
                    'success_count': success,
                    'failed_count': failed,
                    'success_rate': round(success_rate, 2),
                    'top_deliverer': top_deliverer or 'N/A',
                    'lat': coords['lat'],
                    'lng': coords['lng']
                }
            
            logger.info(f"✅ Estatísticas de bairros retornadas: {len(result)} bairros")
            
            return result
    
    except Exception as e:
        logger.error(f"❌ Erro ao buscar estatísticas de bairros: {str(e)}")
        return {}


@router.get("/neighborhoods/heatmap")
async def get_neighborhoods_heatmap(
    status: Optional[str] = Query("failed", description="Status a filtrar (failed, delivered, pending)")
):
    """
    Retorna coordenadas de falhas para heatmap
    Formato: Lista de [lat, lng, intensity]
    
    Args:
        status: Status dos pacotes a filtrar
    
    Returns:
        Lista de coordenadas para heatmap
    """
    try:
        with db_manager.get_session() as db:
            # Buscar pacotes com status específico e coordenadas válidas
            packages = db.query(PackageDB).filter(
                PackageDB.status == status,
                PackageDB.lat != 0,
                PackageDB.lng != 0
            ).all()
            
            # Converter para formato de heatmap
            heatmap_data = []
            for package in packages:
                intensity = 0.5  # Intensidade padrão
                if status == 'failed':
                    intensity = 0.8  # Mais intenso para falhas
                elif status == 'delivered':
                    intensity = 0.3
                
                heatmap_data.append([package.lat, package.lng, intensity])
            
            logger.info(f"✅ Dados de heatmap retornados: {len(heatmap_data)} pontos")
            
            return heatmap_data
    
    except Exception as e:
        logger.error(f"❌ Erro ao buscar dados de heatmap: {str(e)}")
        return []


@router.get("/neighborhoods/{bairro}")
async def get_neighborhood_detail(bairro: str):
    """
    Retorna detalhe completo de um bairro específico
    
    Args:
        bairro: Nome do bairro
    
    Returns:
        Dict com estatísticas detalhadas
    """
    try:
        bounds = BAIRROS_BOUNDS.get(bairro)
        if not bounds:
            return {'error': 'Bairro não encontrado', 'bairro': bairro}
        
        lat_min, lat_max, lng_min, lng_max = bounds
        
        with db_manager.get_session() as db:
            # Buscar todos os pacotes dentro das coordenadas do bairro
            packages = db.query(PackageDB).filter(
                PackageDB.lat >= lat_min,
                PackageDB.lat <= lat_max,
                PackageDB.lng >= lng_min,
                PackageDB.lng <= lng_max
            ).all()
            
            if not packages:
                return {
                    'bairro': bairro,
                    'total_packages': 0,
                    'success_count': 0,
                    'failed_count': 0,
                    'pending_count': 0,
                    'success_rate': 0,
                    'deliverers': {}
                }
            
            total = len(packages)
            success = len([p for p in packages if p.status == 'delivered'])
            failed = len([p for p in packages if p.status == 'failed'])
            pending = len([p for p in packages if p.status == 'pending'])
            
            # Entregadores por performance
            deliverers_data = {}
            for package in packages:
                if package.assigned_to_telegram_id:
                    deliverer = db.query(DelivererDB).filter(
                        DelivererDB.telegram_id == package.assigned_to_telegram_id
                    ).first()
                    
                    if deliverer:
                        if deliverer.name not in deliverers_data:
                            deliverers_data[deliverer.name] = {
                                'total': 0,
                                'success': 0,
                                'failed': 0
                            }
                        
                        deliverers_data[deliverer.name]['total'] += 1
                        
                        if package.status == 'delivered':
                            deliverers_data[deliverer.name]['success'] += 1
                        elif package.status == 'failed':
                            deliverers_data[deliverer.name]['failed'] += 1
            
            # Calcular taxa de sucesso por entregador
            for name, data in deliverers_data.items():
                data['success_rate'] = round(
                    (data['success'] / data['total'] * 100) if data['total'] > 0 else 0,
                    2
                )
            
            return {
                'bairro': bairro,
                'total_packages': total,
                'success_count': success,
                'failed_count': failed,
                'pending_count': pending,
                'success_rate': round((success / total * 100) if total > 0 else 0, 2),
                'deliverers': deliverers_data
            }
    
    except Exception as e:
        logger.error(f"❌ Erro ao buscar detalhe do bairro: {str(e)}")
        return {'error': str(e)}
