"""
🏦 INTEGRAÇÃO BANCO INTER
API para buscar extratos e transações automaticamente
"""
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import logging
from pathlib import Path
import base64

logger = logging.getLogger(__name__)


class BankInterService:
    """Serviço de integração com API do Banco Inter"""
    
    def __init__(self, credentials_file: str = "data/bank_inter_credentials.json"):
        self.credentials_file = Path(credentials_file)
        self.base_url = "https://cdpj.partners.bancointer.com.br"
        self.access_token = None
        self.token_expires_at = None
        
        self._load_credentials()
    
    def _load_credentials(self):
        """Carrega credenciais salvas"""
        if self.credentials_file.exists():
            with open(self.credentials_file, 'r', encoding='utf-8') as f:
                self.credentials = json.load(f)
        else:
            self.credentials = {
                'client_id': '',
                'client_secret': '',
                'cert_path': '',
                'key_path': '',
                'conta_corrente': ''
            }
            self._save_credentials()
    
    def _save_credentials(self):
        """Salva credenciais"""
        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.credentials_file, 'w', encoding='utf-8') as f:
            json.dump(self.credentials, f, indent=2, ensure_ascii=False)
    
    def configure_credentials(
        self,
        client_id: str,
        client_secret: str,
        cert_path: str,
        key_path: str,
        conta_corrente: str
    ):
        """
        Configura credenciais da API do Banco Inter
        
        Args:
            client_id: Client ID da aplicação
            client_secret: Client Secret da aplicação
            cert_path: Caminho do certificado (.crt)
            key_path: Caminho da chave privada (.key)
            conta_corrente: Número da conta corrente
        """
        self.credentials = {
            'client_id': client_id,
            'client_secret': client_secret,
            'cert_path': cert_path,
            'key_path': key_path,
            'conta_corrente': conta_corrente
        }
        self._save_credentials()
        logger.info("Credenciais do Banco Inter configuradas")
    
    def is_configured(self) -> bool:
        """Verifica se está configurado"""
        return bool(
            self.credentials.get('client_id') and
            self.credentials.get('client_secret') and
            self.credentials.get('conta_corrente')
        )
    
    def _get_access_token(self) -> str:
        """
        Obtém access token via OAuth2
        
        Returns:
            Access token válido
        """
        # Se token ainda é válido, retorna
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return self.access_token
        
        # Requisita novo token
        url = f"{self.base_url}/oauth/v2/token"
        
        # Credenciais em Base64
        credentials = f"{self.credentials['client_id']}:{self.credentials['client_secret']}"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'client_credentials',
            'scope': 'extrato.read'
        }
        
        try:
            # Se tiver certificado, usa
            cert_config = None
            if self.credentials.get('cert_path') and self.credentials.get('key_path'):
                cert_config = (
                    self.credentials['cert_path'],
                    self.credentials['key_path']
                )
            
            response = requests.post(url, headers=headers, data=data, cert=cert_config, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            # Calcula expiração (geralmente 3600 segundos)
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
            
            logger.info("Access token obtido com sucesso")
            return self.access_token
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao obter token: {e}")
            raise Exception(f"Falha na autenticação com Banco Inter: {e}")
    
    def get_extrato(
        self,
        data_inicio: datetime,
        data_fim: datetime
    ) -> List[Dict]:
        """
        Busca extrato bancário do período
        
        Args:
            data_inicio: Data inicial
            data_fim: Data final
        
        Returns:
            Lista de transações
        """
        if not self.is_configured():
            raise Exception("Credenciais do Banco Inter não configuradas. Use /config_banco_inter")
        
        token = self._get_access_token()
        
        url = f"{self.base_url}/banking/v2/extrato"
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        params = {
            'dataInicio': data_inicio.strftime('%Y-%m-%d'),
            'dataFim': data_fim.strftime('%Y-%m-%d'),
            'conta': self.credentials['conta_corrente']
        }
        
        try:
            cert_config = None
            if self.credentials.get('cert_path') and self.credentials.get('key_path'):
                cert_config = (
                    self.credentials['cert_path'],
                    self.credentials['key_path']
                )
            
            response = requests.get(url, headers=headers, params=params, cert=cert_config, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            transacoes = data.get('transacoes', [])
            
            logger.info(f"Extrato obtido: {len(transacoes)} transações")
            return transacoes
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao buscar extrato: {e}")
            raise Exception(f"Falha ao buscar extrato: {e}")
    
    def calcular_receita_do_dia(
        self,
        date: datetime,
        tipos_transacao: Optional[List[str]] = None
    ) -> float:
        """
        Calcula receita do dia baseada em transações de entrada
        
        Args:
            date: Data para calcular
            tipos_transacao: Lista de tipos de transação a considerar
                            (default: ['PIX', 'TED', 'DOC'])
        
        Returns:
            Receita total do dia
        """
        if tipos_transacao is None:
            tipos_transacao = ['PIX', 'TED', 'DOC', 'DEPOSITO']
        
        # Busca extrato do dia
        transacoes = self.get_extrato(date, date)
        
        receita = 0.0
        
        for t in transacoes:
            # Considera apenas entradas (crédito)
            if t.get('tipoTransacao') == 'CREDITO':
                tipo = t.get('titulo', '').upper()
                
                # Verifica se é tipo de receita válido
                if any(tipo_valido in tipo for tipo_valido in tipos_transacao):
                    valor = float(t.get('valor', 0))
                    receita += valor
                    logger.debug(f"Receita identificada: {tipo} - R$ {valor:.2f}")
        
        logger.info(f"Receita calculada para {date.strftime('%Y-%m-%d')}: R$ {receita:.2f}")
        return receita
    
    def get_saldo_atual(self) -> Dict:
        """
        Busca saldo atual da conta
        
        Returns:
            Dicionário com informações de saldo
        """
        if not self.is_configured():
            raise Exception("Credenciais do Banco Inter não configuradas")
        
        token = self._get_access_token()
        
        url = f"{self.base_url}/banking/v2/saldo"
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        params = {
            'conta': self.credentials['conta_corrente']
        }
        
        try:
            cert_config = None
            if self.credentials.get('cert_path') and self.credentials.get('key_path'):
                cert_config = (
                    self.credentials['cert_path'],
                    self.credentials['key_path']
                )
            
            response = requests.get(url, headers=headers, params=params, cert=cert_config, timeout=30)
            response.raise_for_status()
            
            saldo_data = response.json()
            logger.info(f"Saldo obtido: R$ {saldo_data.get('disponivel', 0):.2f}")
            
            return saldo_data
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao buscar saldo: {e}")
            raise Exception(f"Falha ao buscar saldo: {e}")


# Instância global
bank_inter_service = BankInterService()
