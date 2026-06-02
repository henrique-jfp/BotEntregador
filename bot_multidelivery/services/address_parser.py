"""
PARSER DE ENDEREÇOS - Extrai informações de endereços brasileiros
Identifica tipo (comercial/residencial), extrai rua, número, complemento
"""

import re
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ParsedAddress:
    """Resultado do parse de um endereço"""
    street: str  # Nome da rua (normalizado)
    number: Optional[str]  # Número do imóvel
    complement: str  # Complemento (Apt, Sala, Bloco, etc)
    is_commercial: bool  # True se parecer comercial
    is_vertical: bool  # True se for apartamento/condomínio
    raw_address: str  # Endereço original
    

class AddressParser:
    """Parse de endereços brasileiros com detecção de tipo"""
    
    # Keywords que indicam endereço comercial
    COMMERCIAL_KEYWORDS = [
        'loja', 'ltda', 'me', 'eireli', 'comercio', 'sala', 'shopping', 'center',
        'plaza', 'mall', 'edificio', 'ed.', 'empresarial', 'office', 'restaurante',
        'farmacia', 'mercado', 'padaria', 'supermercado', 'academia', 'banco',
        'clinica', 'hospital', 'escola', 'consultorio', 'consultora', 'oficina',
        'garagem', 'deposito', 'armazem', 'unicesumar', 'interfone'
    ]
    
    # Keywords que indicam endereço vertical (apartamentos/condomínios)
    VERTICAL_KEYWORDS = [
        'apto', 'apt', 'ap', 'bloco', 'bl', 'b.', 'cond', 'condominio',
        'residencial', 'tower', 'torres', 'predio', 'edificio', 'ed.'
    ]
    
    def parse(self, address_text: str) -> ParsedAddress:
        """
        Parse de um endereço em texto livre
        
        Exemplos:
        - "Rua Principado de Mônaco, 37, Apt 501(guarita tb pode deixar"
        - "Rua Mena Barreto, 161, Loja BMRIO"
        - "Rua Real Grandeza, 308, Loja c depósito bebida"
        """
        
        original = address_text.strip()
        normalized = original.lower()
        
        # Extrai rua e número
        street, number, complement = self._extract_street_number(original, normalized)
        
        # Detecta tipo
        is_commercial = self._is_commercial(normalized)
        is_vertical = self._is_vertical(normalized)
        
        return ParsedAddress(
            street=street,
            number=number,
            complement=complement,
            is_commercial=is_commercial,
            is_vertical=is_vertical,
            raw_address=original
        )
    
    def _extract_street_number(self, original: str, normalized: str) -> Tuple[str, Optional[str], str]:
        """Extrai rua, número e complemento"""
        
        # Padrão: "Rua/Avenida/etc NOME, NÚMERO, COMPLEMENTO"
        # Separa por vírgula primeiro
        parts = [p.strip() for p in original.split(',')]
        
        street = ""
        number = ""
        complement = ""
        
        if len(parts) >= 1:
            street = parts[0].strip()
        
        if len(parts) >= 2:
            # Segundo parte é normalmente número ou número + complemento
            second = parts[1].strip()
            
            # Tenta extrair número (primeiras palavras/números)
            num_match = re.match(r'^(\d+\s?[a-z]*)', second, re.IGNORECASE)
            if num_match:
                number = num_match.group(1).strip()
                # Resto é complemento
                complement = second[len(num_match.group(1)):].strip()
            else:
                complement = second
        
        if len(parts) >= 3:
            # Terceira parte e depois é complemento
            complement += ", " + ", ".join(parts[2:])
        
        # Normaliza rua (tira números e "de" extras)
        street = re.sub(r'\s+', ' ', street).strip()
        
        return street, number if number else None, complement.strip()
    
    def _is_commercial(self, normalized_addr: str) -> bool:
        """Verifica se é endereço comercial"""
        # Retira vários tipos de "lixo" do texto
        cleaned = re.sub(r'[()[\]{}<>]', '', normalized_addr)
        
        for keyword in self.COMMERCIAL_KEYWORDS:
            if keyword in cleaned:
                return True
        
        return False
    
    def _is_vertical(self, normalized_addr: str) -> bool:
        """Verifica se é vertical (apartamento/condomínio)"""
        cleaned = re.sub(r'[()[\]{}<>]', '', normalized_addr)
        
        for keyword in self.VERTICAL_KEYWORDS:
            # Mais rigoroso - procura em limite de palavra
            if re.search(rf'\b{keyword}\b', cleaned):
                return True
        
        return False
    
    def extract_street_name(self, address_text: str) -> str:
        """Extrai apenas o nome da rua (para agrupar)"""
        parsed = self.parse(address_text)
        return parsed.street


# Teste rápido
if __name__ == "__main__":
    parser = AddressParser()
    
    test_addresses = [
        "Rua Principado de Mônaco, 37, Apt 501(guarita tb pode deixar",
        "Rua Mena Barreto, 151, Portaria",
        "Rua Mena Barreto, 161, Loja BMRIO",
        "Rua General Polidoro, 322, 301",
        "Rua Real Grandeza, 308, Loja c depósito bebida",
    ]
    
    for addr in test_addresses:
        parsed = parser.parse(addr)
        print(f"{addr}")
        print(f"  → Rua: {parsed.street}, Nº: {parsed.number}, Compl: {parsed.complement}")
        print(f"  → Comercial: {parsed.is_commercial}, Vertical: {parsed.is_vertical}\n")
