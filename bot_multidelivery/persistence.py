"""
💾 PERSISTÊNCIA DE DADOS - Sistema Multi-Entregador
Armazena dados em PostgreSQL (quando disponível) ou arquivos JSON/JSONL
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from pathlib import Path
from .models import Package, Deliverer

try:
    from .database import db_manager, DelivererDB, RouteDB, PackageDB
    HAS_DATABASE = db_manager.is_connected
except Exception as e:
    print(f"⚠️ Database import failed: {e}")
    HAS_DATABASE = False


class DataStore:
    """Gerenciador de persistência de dados"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Diretórios específicos
        self.deliverers_file = self.data_dir / "deliverers.json"
        self.packages_file = self.data_dir / "packages.jsonl"
        
        # Indica se está usando database ou JSON
        self.using_database = HAS_DATABASE
        if self.using_database:
            print("
" + "="*50)
            print("DataStore usando PostgreSQL")
            print("Entregadores serao salvos permanentemente")
            print("="*50 + "
")
        else:
            print("
" + "="*50)
            print("DataStore usando JSON local")
            print("AVISO: Dados em data/deliverers.json (temporario)")
            print("="*50 + "
")
    
    # ==================== ENTREGADORES ====================
    
    def save_deliverers(self, deliverers: List[Deliverer]):
        """Salva lista de entregadores"""
        if self.using_database:
            # Salva no PostgreSQL
            try:
                print(f"Salvando {len(deliverers)} entregadores no PostgreSQL...")
                with db_manager.get_session() as session:
                    saved_count = 0
                    updated_count = 0
                    for d in deliverers:
                        deliverer_db = session.query(DelivererDB).filter_by(telegram_id=d.telegram_id).first()
                        if deliverer_db:
                            # Atualiza existente
                            deliverer_db.name = d.name
                            deliverer_db.is_partner = d.is_partner
                            deliverer_db.max_capacity = d.max_capacity
                            deliverer_db.cost_per_package = d.cost_per_package
                            deliverer_db.is_active = d.is_active
                            deliverer_db.total_deliveries = d.total_deliveries
                            deliverer_db.total_earnings = d.total_earnings
                            deliverer_db.success_rate = d.success_rate
                            deliverer_db.average_delivery_time = d.average_delivery_time
                            updated_count += 1
                        else:
                            # Cria novo
                            deliverer_db = DelivererDB(
                                telegram_id=d.telegram_id,
                                name=d.name,
                                is_partner=d.is_partner,
                                max_capacity=d.max_capacity,
                                cost_per_package=d.cost_per_package,
                                is_active=d.is_active,
                                total_deliveries=d.total_deliveries,
                                total_earnings=d.total_earnings,
                                success_rate=d.success_rate,
                                average_delivery_time=d.average_delivery_time,
                                joined_date=d.joined_date
                            )
                            session.add(deliverer_db)
                            saved_count += 1
                    print(f"PostgreSQL: {saved_count} novos, {updated_count} atualizados")
                return
            except Exception as e:
                print(f"Erro ao salvar no PostgreSQL: {e}")
                import traceback
                traceback.print_exc()
                print("📁 Usando fallback JSON")
        
        # Fallback: JSON
        data = [{
            'telegram_id': d.telegram_id,
            'name': d.name,
            'is_partner': d.is_partner,
            'max_capacity': d.max_capacity,
            'cost_per_package': d.cost_per_package,
            'is_active': d.is_active,
            'total_deliveries': d.total_deliveries,
            'total_earnings': d.total_earnings,
            'success_rate': d.success_rate,
            'average_delivery_time': d.average_delivery_time,
            'joined_date': d.joined_date.isoformat()
        } for d in deliverers]
        
        with open(self.deliverers_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_deliverers(self) -> List[Deliverer]:
        """Carrega lista de entregadores"""
        if self.using_database:
            # Carrega do PostgreSQL
            try:
                print("Carregando entregadores do PostgreSQL...")
                with db_manager.get_session() as session:
                    deliverers_db = session.query(DelivererDB).all()
                    deliverers = [Deliverer(
                        telegram_id=d.telegram_id,
                        name=d.name,
                        is_partner=d.is_partner,
                        max_capacity=d.max_capacity,
                        cost_per_package=d.cost_per_package,
                        is_active=d.is_active,
                        total_deliveries=d.total_deliveries,
                        total_earnings=d.total_earnings,
                        success_rate=d.success_rate,
                        average_delivery_time=d.average_delivery_time,
                        joined_date=d.joined_date
                    ) for d in deliverers_db]
                    print(f"{len(deliverers)} entregadores carregados do PostgreSQL")
                    return deliverers
            except Exception as e:
                print(f"Erro ao carregar do PostgreSQL: {e}")
                import traceback
                traceback.print_exc()
                print("📁 Usando fallback JSON")
        
        # Fallback: JSON
        if not self.deliverers_file.exists():
            return []
        
        with open(self.deliverers_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return [Deliverer(
            telegram_id=d['telegram_id'],
            name=d['name'],
            is_partner=d['is_partner'],
            max_capacity=d.get('max_capacity', 50),
            cost_per_package=d.get('cost_per_package', 1.0),
            is_active=d.get('is_active', True),
            total_deliveries=d.get('total_deliveries', 0),
            total_earnings=d.get('total_earnings', 0.0),
            success_rate=d.get('success_rate', 100.0),
            average_delivery_time=d.get('average_delivery_time', 0.0),
            joined_date=datetime.fromisoformat(d.get('joined_date', datetime.now().isoformat()))
        ) for d in data]
    
    def add_deliverer(self, deliverer: Deliverer):
        """Adiciona novo entregador"""
        deliverers = self.load_deliverers()
        
        # Verifica se já existe
        if any(d.telegram_id == deliverer.telegram_id for d in deliverers):
            # Atualiza existente
            deliverers = [d if d.telegram_id != deliverer.telegram_id else deliverer 
                         for d in deliverers]
        else:
            deliverers.append(deliverer)
        
        self.save_deliverers(deliverers)
        

    def delete_deliverer(self, telegram_id: int):
        """Remove um entregador permanentemente"""
        if self.using_database:
            try:
                print(f"Removendo entregador {telegram_id} do PostgreSQL...")
                with db_manager.get_session() as session:
                    # 1. Desvincular de Rotas Ativas/Passadas
                    session.query(RouteDB).filter_by(assigned_to_telegram_id=telegram_id).update({"assigned_to_telegram_id": None})
                    # 2. Desvincular de Pacotes
                    session.query(PackageDB).filter_by(assigned_to_telegram_id=telegram_id).update({"assigned_to_telegram_id": None})
                    
                    # 3. Deleta registro da tabela deliverers
                    rows = session.query(DelivererDB).filter_by(telegram_id=telegram_id).delete()
                    print(f"Entregador {telegram_id} removido ({rows} linhas afetadas)")
            except Exception as e:
                print(f"Erro ao remover do PostgreSQL: {e}")
                raise e
        else:
            # Fallback JSON
            deliverers = self.load_deliverers()
            new_list = [d for d in deliverers if d.telegram_id != telegram_id]
            if len(new_list) < len(deliverers):
                self.save_deliverers(new_list)

    
    def get_deliverer(self, telegram_id: int) -> Optional[Deliverer]:
        """Busca entregador por ID"""
        deliverers = self.load_deliverers()
        return next((d for d in deliverers if d.telegram_id == telegram_id), None)
    
    def update_deliverer_stats(self, telegram_id: int, **kwargs):
        """Atualiza estatísticas do entregador"""
        deliverers = self.load_deliverers()
        
        for d in deliverers:
            if d.telegram_id == telegram_id:
                for key, value in kwargs.items():
                    if hasattr(d, key):
                        setattr(d, key, value)
                break
        
        self.save_deliverers(deliverers)
    
    # ==================== PACOTES ====================
    
    def save_package(self, package: Package):
        """Salva pacote (append no JSONL)"""
        data = {
            'id': package.id,
            'address': package.address,
            'lat': package.lat,
            'lng': package.lng,
            'priority': package.priority.value,
            'status': package.status.value,
            'assigned_to': package.assigned_to,
            'delivered_at': package.delivered_at.isoformat() if package.delivered_at else None,
            'delivery_time_minutes': package.delivery_time_minutes,
            'notes': package.notes,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(self.packages_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '
')
    
    def get_packages_by_date(self, date: datetime) -> List[Package]:
        """Carrega pacotes de uma data específica"""
        if not self.packages_file.exists():
            return []
        
        packages = []
        target_date = date.date()
        
        with open(self.packages_file, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line)
                pkg_date = datetime.fromisoformat(data['timestamp']).date()
                
                if pkg_date == target_date:
                    from .models import PackagePriority, PackageStatus
                    packages.append(Package(
                        id=data['id'],
                        address=data['address'],
                        lat=data['lat'],
                        lng=data['lng'],
                        priority=PackagePriority(data['priority']),
                        status=PackageStatus(data['status']),
                        assigned_to=data.get('assigned_to'),
                        delivered_at=datetime.fromisoformat(data['delivered_at']) if data.get('delivered_at') else None,
                        delivery_time_minutes=data.get('delivery_time_minutes'),
                        notes=data.get('notes', '')
                    ))
        
        return packages
    
    def get_all_packages(self) -> List[dict]:
        """Retorna todos os pacotes como dicts (para gamification)"""
        if not self.packages_file.exists():
            return []
        
        packages = []
        with open(self.packages_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    packages.append(json.loads(line))
                except:
                    continue
        
        return packages

# Singleton
data_store = DataStore()
