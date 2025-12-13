"""
💾 PERSISTÊNCIA DE DADOS - Sistema Multi-Entregador
Armazena dados em arquivos JSON/JSONL
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from pathlib import Path
from .models import Package, Deliverer, FinancialReport, PerformanceMetrics, PaymentRecord


class DataStore:
    """Gerenciador de persistência de dados"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Diretórios específicos
        self.deliverers_file = self.data_dir / "deliverers.json"
        self.packages_file = self.data_dir / "packages.jsonl"
        self.reports_dir = self.data_dir / "reports"
        self.payments_dir = self.data_dir / "payments"
        
        self.reports_dir.mkdir(exist_ok=True)
        self.payments_dir.mkdir(exist_ok=True)
    
    # ==================== ENTREGADORES ====================
    
    def save_deliverers(self, deliverers: List[Deliverer]):
        """Salva lista de entregadores"""
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
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    
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
    
    # ==================== RELATÓRIOS ====================
    
    def save_financial_report(self, report: FinancialReport):
        """Salva relatório financeiro"""
        filename = f"financial_{report.date.strftime('%Y-%m-%d')}.json"
        filepath = self.reports_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
    
    def get_financial_reports(self, start_date: datetime, end_date: datetime) -> List[FinancialReport]:
        """Carrega relatórios financeiros de um período"""
        reports = []
        
        for file in self.reports_dir.glob("financial_*.json"):
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                report_date = datetime.fromisoformat(data['date'])
                
                if start_date <= report_date <= end_date:
                    reports.append(FinancialReport(**data))
        
        return sorted(reports, key=lambda r: r.date)
    
    # ==================== PAGAMENTOS ====================
    
    def export_payment_file(self, payments: List[PaymentRecord], filename: str = None):
        """Exporta arquivo CSV de pagamentos"""
        if filename is None:
            filename = f"pagamentos_{datetime.now().strftime('%Y%m%d')}.csv"
        
        filepath = self.payments_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # Header
            f.write("ID,Nome,Pacotes,Valor,Início,Fim\n")
            
            # Data
            for payment in payments:
                f.write(payment.to_payment_file_line() + '\n')
        
        return filepath
    
    def save_payment_record(self, payment: PaymentRecord):
        """Salva registro de pagamento"""
        filename = f"payment_{payment.deliverer_id}_{datetime.now().strftime('%Y%m%d')}.json"
        filepath = self.payments_dir / filename
        
        data = {
            'deliverer_id': payment.deliverer_id,
            'deliverer_name': payment.deliverer_name,
            'period_start': payment.period_start.isoformat(),
            'period_end': payment.period_end.isoformat(),
            'packages_delivered': payment.packages_delivered,
            'amount_due': payment.amount_due,
            'paid': payment.paid,
            'paid_at': payment.paid_at.isoformat() if payment.paid_at else None,
            'payment_method': payment.payment_method
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# Singleton
data_store = DataStore()
