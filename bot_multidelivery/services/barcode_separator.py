"""
🎨 SEPARAÇÃO POR COR - Sistema de marcação visual
Bipa pacote → Identifica rota → Mostra cor DO ENTREGADOR
"""
from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class PackageAssignment:
    """Atribuição de pacote a rota colorida"""
    package_id: str
    route_id: str
    deliverer_name: str
    color: str  # Hex color da rota (ex: '#FF4444')
    color_name: str  # Nome amigável (ex: '🔴 VERMELHO')
    address: str
    position: int  # Posição na rota (ex: 23/45)
    total_in_route: int


class BarcodeSeparator:
    """Gerencia separação física por código de barras"""
    
    def __init__(self):
        self.active = False
        self.assignments: Dict[str, PackageAssignment] = {}  # package_id -> assignment
        self.scanned = set()  # IDs já escaneados
        self.session_id: Optional[str] = None
    
    def start_separation_mode(self, session) -> str:
        """
        Inicia modo separação usando sessão ativa
        
        Args:
            session: DailySession com rotas já atribuídas
        """
        if not session or not session.routes:
            return "❌ Nenhuma sessão ativa com rotas definidas!"
        
        self.active = True
        self.session_id = session.session_id
        self.assignments.clear()
        self.scanned.clear()
        
        # Importa função de cores
        try:
            from ..colors import get_color_name
        except:
            get_color_name = lambda x: x  # Fallback
        
        # Mapeia todos os pacotes das rotas
        for route in session.routes:
            if not route.assigned_to_name:
                continue  # Pula rotas não atribuídas
            
            deliverer = route.assigned_to_name
            color = route.color  # Hex color tipo '#FF4444'
            color_name = get_color_name(color)  # '🔴 VERMELHO'
            packages = route.optimized_order
            total = len(packages)
            
            for idx, pkg in enumerate(packages, 1):
                # Usa ID do DeliveryPoint
                pkg_id = pkg.id.strip().upper()
                
                self.assignments[pkg_id] = PackageAssignment(
                    package_id=pkg_id,
                    route_id=route.id,
                    deliverer_name=deliverer,
                    color=color,
                    color_name=color_name,
                    address=pkg.address[:60],
                    position=idx,
                    total_in_route=total
                )
        
        return f"✅ Modo separação ativado!\n\n📦 {len(self.assignments)} pacotes mapeados\n🎨 Bipe os códigos de barras para identificar"
    
    def scan_package(self, barcode: str) -> Optional[str]:
        """
        Processa código de barras escaneado
        
        Returns:
            Mensagem formatada com cor/entregador ou None se não encontrado
        """
        if not self.active:
            return "⚠️ Modo separação não está ativo. Use /modo_separacao primeiro."
        
        # Limpa código (remove espaços, quebras de linha)
        barcode = barcode.strip().upper()
        
        # Busca no mapa
        assignment = self.assignments.get(barcode)
        
        if not assignment:
            return f"❌ Pacote não encontrado: {barcode}\n\n💡 Verifique se o código está correto"
        
        # Marca como escaneado
        self.scanned.add(barcode)
        
        # Extrai emoji da cor (primeiro caractere do color_name)
        emoji = assignment.color_name.split()[0]
        
        # Formata número pra pistola (8 dígitos)
        numero_pistola = f"{assignment.position:08d}"
        
        response = (
            f"{emoji} {emoji} {emoji}\n"
            f"<b>{assignment.color_name}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>{assignment.deliverer_name}</b>\n"
            f"📍 {assignment.address[:50]}...\n"
            f"🎯 <b>ENTREGA #{assignment.position} de {assignment.total_in_route}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔢 <b>Configure pistola: {numero_pistola}</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ {len(self.scanned)}/{len(self.assignments)} separados"
        )
        
        return response
    
    def end_separation(self) -> str:
        """Finaliza modo separação e gera relatório"""
        if not self.active:
            return "⚠️ Modo separação não está ativo."
        
        # Conta por cor
        color_counts = {}
        for assignment in self.assignments.values():
            color_name = assignment.color_name
            color_counts[color_name] = color_counts.get(color_name, 0) + 1
        
        report = "📊 <b>SEPARAÇÃO CONCLUÍDA</b>\n\n"
        
        for color_name, count in color_counts.items():
            emoji = color_name.split()[0]
            report += f"{emoji} <b>{color_name}</b>: {count} pacotes\n"
        
        report += f"\n✅ Total separado: {len(self.scanned)}/{len(self.assignments)}"
        
        # Reseta
        self.active = False
        self.assignments.clear()
        self.scanned.clear()
        self.session_id = None
        
        return report
    
    def get_status(self) -> str:
        """Status atual da separação"""
        if not self.active:
            return "⚠️ Modo separação inativo"
        
        return (
            f"🎨 <b>MODO SEPARAÇÃO ATIVO</b>\n\n"
            f"📦 Total: {len(self.assignments)} pacotes\n"
            f"✅ Separados: {len(self.scanned)}\n"
            f"⏳ Faltam: {len(self.assignments) - len(self.scanned)}"
        )
    
    def _extract_package_id(self, package: dict) -> str:
        """
        Extrai ID do pacote que corresponde ao código de barras
        
        Shopee: geralmente "order_id" ou "tracking_code"
        Mercado Livre: "shipment_id"
        """
        # Tenta várias chaves possíveis
        for key in ["tracking_code", "order_id", "shipment_id", "barcode", "id"]:
            if key in package and package[key]:
                return str(package[key]).strip().upper()
        
        # Fallback: usa endereço completo como ID (não ideal)
        return package.get("address", "UNKNOWN").strip().upper()


# Instância global
barcode_separator = BarcodeSeparator()
