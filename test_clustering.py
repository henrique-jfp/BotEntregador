"""
🧪 TESTE RÁPIDO - Divisão Territorial
Simula divisão de rotas sem precisar do bot rodando
"""
from bot_multidelivery.clustering import DeliveryPoint, TerritoryDivider

# Simula endereços de São Paulo
fake_addresses = [
    ("Av. Paulista, 1000", -23.5618, -46.6559),
    ("Rua Augusta, 500", -23.5565, -46.6612),
    ("Praça da Sé, 100", -23.5505, -46.6333),
    ("Av. Faria Lima, 2000", -23.5780, -46.6890),
    ("Rua Oscar Freire, 300", -23.5619, -46.6707),
    ("Av. Rebouças, 1500", -23.5576, -46.6708),
    ("Rua da Consolação, 800", -23.5505, -46.6500),
    ("Av. Ipiranga, 200", -23.5431, -46.6449),
    ("Rua Haddock Lobo, 600", -23.5568, -46.6644),
    ("Av. Brigadeiro Luís Antônio, 1000", -23.5594, -46.6528),
]

# Base (carro estacionado)
base_address = "Rua da Mooca, 1000"
base_lat, base_lng = -23.5489, -46.5982

print("🏠 BASE:", base_address)
print(f"📍 Coordenadas: {base_lat}, {base_lng}\n")

# Cria pontos de entrega
points = [
    DeliveryPoint(
        address=addr,
        lat=lat,
        lng=lng,
        romaneio_id=f"ROM{i//3}",
        package_id=f"PKG{i:03d}"
    )
    for i, (addr, lat, lng) in enumerate(fake_addresses)
]

print(f"📦 Total de pacotes: {len(points)}\n")

# Divide em clusters
divider = TerritoryDivider(base_lat, base_lng)
clusters = divider.divide_into_clusters(points, k=2)

print(f"🎯 Dividido em {len(clusters)} territórios:\n")

for cluster in clusters:
    print(f"{'='*60}")
    print(f"🗺️  CLUSTER {cluster.id + 1}")
    print(f"{'='*60}")
    print(f"📍 Centro: ({cluster.center_lat:.4f}, {cluster.center_lng:.4f})")
    print(f"📏 Distância da base: {cluster.distance_to_base(base_lat, base_lng):.2f} km")
    print(f"📦 Pacotes: {cluster.total_packages}")
    print(f"\n📋 Endereços:")
    
    for i, point in enumerate(cluster.points, 1):
        print(f"   {i}. {point.address}")
    
    # Otimiza ordem
    optimized = divider.optimize_cluster_route(cluster)
    print(f"\n✅ Ordem otimizada:")
    for i, point in enumerate(optimized, 1):
        print(f"   {i}. {point.address} (ID: {point.package_id})")
    
    print()

print("="*60)
print("💡 Interpretação:")
print("="*60)
print("• Cluster 0 = ROTA_1 (entregador 1)")
print("• Cluster 1 = ROTA_2 (entregador 2)")
print("• Ordem otimizada usa Greedy Nearest Neighbor")
print("• Cada entregador vai pra um lado, sem se cruzarem")
print("\n🔥 Sistema pronto pra rodar no Telegram!")
