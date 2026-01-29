"""
Script de teste para validar correções do /analisar_rota
"""
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot_multidelivery.parsers.shopee_parser import clean_destination_address


def test_clean_destination_address():
    """Testa a função de limpeza de endereços"""
    
    print("🧪 TESTANDO LIMPEZA DE ENDEREÇOS\n")
    print("=" * 70)
    
    test_cases = [
        # Formato: (input, expected_output)
        (
            "Rua Principado de Mônaco, 37, Apt 501(guarita tb pode deixar",
            "Rua Principado de Mônaco, 37"
        ),
        (
            "Rua Mena Barreto, 151, Portaria",
            "Rua Mena Barreto, 151"
        ),
        (
            "Rua Mena Barreto, 161, Apt.605 bl bloco 2",
            "Rua Mena Barreto, 161"
        ),
        (
            "Rua Mena Barreto, 161, Bloco 2 apt. 1002",
            "Rua Mena Barreto, 161"
        ),
        (
            "Rua Mena Barreto, 161, Loja BMRIO",
            "Rua Mena Barreto, 161"
        ),
        (
            "Rua Mena Barreto, 161, Bl 2 ap 206",
            "Rua Mena Barreto, 161"
        ),
        (
            "Rua Real Grandeza, 278, 601",
            "Rua Real Grandeza, 278"
        ),
        (
            "Rua Real Grandeza, 301, Consultora de oficina paula",
            "Rua Real Grandeza, 301"
        ),
        (
            "Rua General Polidoro, 322, 301",
            "Rua General Polidoro, 322"
        ),
        (
            "Rua Real Grandeza, 314, Unicesumar INTERFONE 28",
            "Rua Real Grandeza, 314"
        ),
        (
            "Rua Real Grandeza, 308, Loja c depósito bebida",
            "Rua Real Grandeza, 308"
        ),
        (
            "Rua General Polidoro, 322, Cobertura 95.",
            "Rua General Polidoro, 322"
        ),
        (
            "Rua Real Grandeza, 312",
            "Rua Real Grandeza, 312"
        ),
    ]
    
    passed = 0
    failed = 0
    
    for i, (input_addr, expected) in enumerate(test_cases, 1):
        result = clean_destination_address(input_addr)
        
        status = "✅" if result == expected else "❌"
        
        print(f"\nTeste {i}: {status}")
        print(f"  Input:    {input_addr}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {result}")
        
        if result == expected:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"\n📊 RESULTADOS:")
    print(f"   ✅ Passou: {passed}/{len(test_cases)}")
    print(f"   ❌ Falhou: {failed}/{len(test_cases)}")
    
    if failed == 0:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
    else:
        print("\n⚠️  ALGUNS TESTES FALHARAM")
    
    print()


def test_geocoding_service():
    """Testa o serviço de geocoding"""
    from bot_multidelivery.services.geocoding_service import GeocodingService
    
    print("\n🧪 TESTANDO SERVIÇO DE GEOCODING\n")
    print("=" * 70)
    
    # Cria serviço sem API key (usa OSM)
    service = GeocodingService(google_api_key=None)
    
    test_addresses = [
        {
            'address': 'Rua Mena Barreto, 151',
            'bairro': 'Botafogo',
            'expected_lat': -22.95,  # Aproximado
            'expected_lon': -43.18
        },
        {
            'address': 'Rua Real Grandeza, 278',
            'bairro': 'Botafogo',
            'expected_lat': -22.95,
            'expected_lon': -43.18
        }
    ]
    
    print("\n⚠️  NOTA: Testes de geocoding requerem conexão com internet")
    print("          e podem levar alguns segundos...\n")
    
    for i, test in enumerate(test_addresses, 1):
        full_address = f"{test['address']}, {test['bairro']}, Rio de Janeiro, RJ, Brasil"
        print(f"Teste {i}: {full_address}")
        
        try:
            coords = service.geocode(full_address, test['bairro'])
            
            if coords:
                lat, lon = coords
                print(f"  ✅ Geocodificado: ({lat:.6f}, {lon:.6f})")
                
                # Verifica se está próximo ao esperado (margem de 0.1 grau ~11km)
                lat_diff = abs(lat - test['expected_lat'])
                lon_diff = abs(lon - test['expected_lon'])
                
                if lat_diff < 0.1 and lon_diff < 0.1:
                    print(f"  ✅ Coordenadas dentro da região esperada")
                else:
                    print(f"  ⚠️  Coordenadas fora da região esperada")
            else:
                print(f"  ❌ Falhou ao geocodificar")
        except Exception as e:
            print(f"  ❌ Erro: {e}")
        
        print()


def main():
    """Executa todos os testes"""
    print("\n" + "=" * 70)
    print("  🧪 TESTES DE CORREÇÃO DO /analisar_rota")
    print("=" * 70 + "\n")
    
    # Teste 1: Limpeza de endereços
    test_clean_destination_address()
    
    # Teste 2: Geocoding (opcional, requer internet)
    try:
        response = input("\n❓ Deseja testar o serviço de geocoding? (requer internet) [s/N]: ")
        if response.lower() in ['s', 'sim', 'y', 'yes']:
            test_geocoding_service()
    except KeyboardInterrupt:
        print("\n\n⏹️  Testes interrompidos pelo usuário")
    
    print("\n" + "=" * 70)
    print("  ✅ TESTES CONCLUÍDOS")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
