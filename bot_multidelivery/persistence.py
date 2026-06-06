"""
💾 PERSISTÊNCIA DE DADOS - Sistema Multi-Entregador
Armazena dados em PostgreSQL (quando disponível) ou arquivos JSON/JSONL
Versão Logística: Removidas métricas financeiras.
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from pathlib import Path
from .models import Package, Deliverer

try:
    from .database import db_manager, DelivererDB, RouteDB, PackageDB
    HAS_DATABASE = True
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
        self.using_database = HAS_DATABASE and db_manager.is_connected
        if self.using_database:
            print("DataStore: Usando persistência via PostgreSQL.")
        else:
            print("DataStore: Usando persistência via arquivos JSON.")
    
    def _check_db(self):
        """Atualiza estado da conexão"""
        self.using_database = HAS_DATABASE and db_manager.is_connected

    # ==================== ENTREGADORES ====================
    
    def save_deliverers(self, deliverers: List[Deliverer]):
        """Salva lista de entregadores"""
        self._check_db()
        if self.using_database:
            try:
                with db_manager.get_session() as session:
                    for d in deliverers:
                        deliverer_db = session.query(DelivererDB).filter_by(telegram_id=d.telegram_id).first()
                        if deliverer_db:
                            deliverer_db.name = d.name
                            deliverer_db.is_partner = d.is_partner
                            deliverer_db.max_capacity = d.max_capacity
                            deliverer_db.is_active = d.is_active
                            deliverer_db.total_deliveries = d.total_deliveries
                            deliverer_db.success_rate = d.success_rate
                            deliverer_db.average_delivery_time = d.average_delivery_time
                        else:
                            deliverer_db = DelivererDB(
                                telegram_id=d.telegram_id,
                                name=d.name,
                                is_partner=d.is_partner,
                                max_capacity=d.max_capacity,
                                is_active=d.is_active,
                                total_deliveries=d.total_deliveries,
                                success_rate=d.success_rate,
                                average_delivery_time=d.average_delivery_time,
                                joined_date=d.joined_date
                            )
                            session.add(deliverer_db)
                return
            except Exception as e:
                print(f"Erro ao salvar no PostgreSQL: {e}")
        
        # Fallback JSON
        data = [{
            'telegram_id': d.telegram_id,
            'name': d.name,
            'is_partner': d.is_partner,
            'max_capacity': d.max_capacity,
            'is_active': d.is_active,
            'total_deliveries': d.total_deliveries,
            'success_rate': d.success_rate,
            'average_delivery_time': d.average_delivery_time,
            'joined_date': d.joined_date.isoformat()
        } for d in deliverers]
        
        with open(self.deliverers_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_deliverers(self) -> List[Deliverer]:
        """Carrega lista de entregadores"""
        self._check_db()
        if self.using_database:
            try:
                with db_manager.get_session() as session:
                    deliverers_db = session.query(DelivererDB).all()
                    return [Deliverer(
                        telegram_id=d.telegram_id,
                        name=d.name,
                        is_partner=d.is_partner,
                        max_capacity=d.max_capacity,
                        is_active=d.is_active,
                        total_deliveries=d.total_deliveries,
                        success_rate=d.success_rate,
                        average_delivery_time=d.average_delivery_time,
                        joined_date=d.joined_date
                    ) for d in deliverers_db]
            except Exception as e:
                print(f"Erro ao carregar do PostgreSQL: {e}")
        
        if not self.deliverers_file.exists():
            return []
        
        with open(self.deliverers_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return [Deliverer(
            telegram_id=d['telegram_id'],
            name=d['name'],
            is_partner=d['is_partner'],
            max_capacity=d.get('max_capacity', 50),
            is_active=d.get('is_active', True),
            total_deliveries=d.get('total_deliveries', 0),
            success_rate=d.get('success_rate', 100.0),
            average_delivery_time=d.get('average_delivery_time', 0.0),
            joined_date=datetime.fromisoformat(d.get('joined_date', datetime.now().isoformat()))
        ) for d in data]
    
    def add_deliverer(self, deliverer: Deliverer):
        deliverers = self.load_deliverers()
        if any(d.telegram_id == deliverer.telegram_id for d in deliverers):
            deliverers = [d if d.telegram_id != deliverer.telegram_id else deliverer for d in deliverers]
        else:
            deliverers.append(deliverer)
        self.save_deliverers(deliverers)
        
    def delete_deliverer(self, telegram_id: int):
        self._check_db()
        if self.using_database:
            try:
                with db_manager.get_session() as session:
                    session.query(RouteDB).filter_by(assigned_to_telegram_id=telegram_id).update({"assigned_to_telegram_id": None})
                    session.query(PackageDB).filter_by(assigned_to_telegram_id=telegram_id).update({"assigned_to_telegram_id": None})
                    session.query(DelivererDB).filter_by(telegram_id=telegram_id).delete()
            except Exception as e:
                raise e
        else:
            deliverers = self.load_deliverers()
            new_list = [d for d in deliverers if d.telegram_id != telegram_id]
            if len(new_list) < len(deliverers):
                self.save_deliverers(new_list)

    def get_deliverer(self, telegram_id: int) -> Optional[Deliverer]:
        deliverers = self.load_deliverers()
        return next((d for d in deliverers if d.telegram_id == telegram_id), None)

# Instância global
data_store = DataStore()
