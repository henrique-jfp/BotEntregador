"""
Teste simples da função clean_destination_address
"""
import re


def clean_destination_address(raw_address: str) -> str:
    """
    Limpa endereço da Shopee extraindo APENAS:
    - Nome da rua (antes da primeira vírgula)
    - Número do prédio (após a primeira vírgula, até encontrar espaço/vírgula/parêntese)
    """
    if not raw_address:
        return ""
    
    # Remove espaços extras
    address = raw_address.strip()
    
    # Divide pela primeira vírgula
    parts = address.split(',', 2)  # Limita a 3 partes
    
    if len(parts) < 2:
        # Se não tem vírgula, retorna o endereço como está
        return address
    
    # Parte 1: Nome da rua
    street_name = parts[0].strip()
    
    # Parte 2: Número do prédio (extrai apenas dígitos do início)
    number_part = parts[1].strip()
    
    # Extrai apenas o número (remove tudo após espaços, parênteses, vírgulas)
    number_match = re.match(r'^(\d+[A-Za-z]?)', number_part)
    if number_match:
        building_number = number_match.group(1)
    else:
        # Se não encontrar número, usa a parte toda
        building_number = number_part.split()[0] if ' ' in number_part else number_part
    
    # Retorna apenas rua + número
    return f"{street_name}, {building_number}"


def main():
    """Testa a função de limpeza de endereços"""
    
    print("\n🧪 TESTANDO LIMPEZA DE ENDEREÇOS\n")
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
        return 0
    else:
        print("\n⚠️  ALGUNS TESTES FALHARAM")
        return 1


if __name__ == "__main__":
    exit(main())
