"""
🌱 SEED - Popula entregadores iniciais
Roda isso APENAS UMA VEZ para inicializar
"""
from bot_multidelivery.services import deliverer_service

def seed():
    """Cadastra entregadores iniciais"""
    initial_deliverers = [
        {"telegram_id": 123456789, "name": "João (Sócio)", "is_partner": True, "max_capacity": 60, "cost": 0},
        {"telegram_id": 987654321, "name": "Maria (Sócio)", "is_partner": True, "max_capacity": 55, "cost": 0},
        {"telegram_id": 111222333, "name": "Carlos", "is_partner": False, "max_capacity": 40, "cost": 1.0},
        {"telegram_id": 444555666, "name": "Ana", "is_partner": False, "max_capacity": 35, "cost": 1.0},
    ]
    
    for d in initial_deliverers:
        cost = d.pop("cost", 0)
        success = deliverer_service.add_deliverer(**d)
        
        # Se adicionou, atualiza o custo manualmente
        if success and not d["is_partner"]:
            deliverer_service.update_deliverer(d["telegram_id"], cost_per_package=cost)
        
        status = "✅" if success else "⚠️ (já existe)"
        print(f"{status} {d['name']} - ID {d['telegram_id']}")
    
    print("\n🎉 Seed concluído!")
    
    # Lista todos
    print("\n👥 Entregadores cadastrados:")
    for deliverer in deliverer_service.get_all_deliverers():
        tipo = "🤝 Parceiro" if deliverer.is_partner else "💼 Terceiro"
        print(f"  {tipo} {deliverer.name} (Cap: {deliverer.max_capacity})")

if __name__ == "__main__":
    seed()
