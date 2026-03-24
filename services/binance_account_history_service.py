import logging
import pandas as pd
import time
from typing import Dict, List, Union, Optional
from env.keys import BINANCE_API_KEY, BINANCE_API_SECRET
from binance.client import Client
from binance.enums import *
from config import MAX_RETRIES, RETRY_DELAY

logger = logging.getLogger(__name__)


class BinanceAccountService:
    """
    Serviço responsável por requisições e transformação de dados de conta na API Binance.
    
    Encapsula todas as chamadas HTTP à Binance REST API e transformações:
    - Retry logic com validação de conectividade
    - Transformação de dados brutos em DataFrames estruturados
    - Type casting apropriado (int, float, datetime)
    - Validação de dados e tratamento de erros específicos
    
    Attributes:
        client: Cliente Binance já autenticado
        api_key: Chave de API Binance
        api_secret: Secret da API Binance
    """
    
    def __init__(self) -> None:
        """
        Inicializa o serviço de dados de conta.
        
        Raises:
            RuntimeError: Se não conseguir conectar à API Binance
        """
        try:
            self.api_key: str = BINANCE_API_KEY
            self.api_secret: str = BINANCE_API_SECRET
            self.client: Client = Client(self.api_key, self.api_secret, testnet=True)
            logger.info("BinanceAccountService inicializado com sucesso")
        except Exception as e:
            logger.error(f"Falha crítica ao conectar na API: {e}")
            raise RuntimeError(f"Falha crítica: Não foi possível conectar à API. Erro: {e}")

    def account_info(self) -> Union[pd.DataFrame, str]:
        """
        Obtém informações de saldo dos ativos da conta.
        
        Returns:
            DataFrame com ativos com saldo > 0 ou mensagem de erro
        """
        for attempt in range(MAX_RETRIES):
            try:
                data = self.client.get_account()
                if isinstance(data, dict):
                    df = pd.DataFrame(data['balances'])
                    df[['free', 'locked']] = df[['free', 'locked']].astype(float).round(4)
                    df = df[(df['free'] > 0) | (df['locked'] > 0)].reset_index(drop=True)
                    df['asset'] = df['asset'].astype(str)
                    logger.info(f"Obtidas informações de conta com {len(df)} ativos com saldo")
                    return df
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error("Erro de permissão ao obter informações de conta")
                    raise PermissionError(f"Failed to retrieve account info, user doesn't have permission to do this request.")
                logger.warning(f"[Tentativa {attempt + 1}/{MAX_RETRIES}] {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        logger.error("Falha ao obter informações de conta")
        return "failed to get account info, error:"

    def account_status(self) -> str:
        """
        Obtém estado atual da conta (Normal, Locked, etc).
        
        Returns:
            String com status ou mensagem de erro/orientação
        """
        url = 'https://www.binance.com/pt-BR/my/dashboard'
        for attempt in range(MAX_RETRIES):
            try:
                data = self.client.get_account_status()
                if isinstance(data, dict):
                    if 'Normal' in data.values():
                        logger.info("Status de conta: Normal")
                        return 'Account is ok!'
                    if data != 'Normal':
                        msg = f'Please check account status on binance, possible pendencies.{url}'
                        logger.warning(f"Conta com status pendente: {msg}")
                        return msg
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error("Erro de permissão ao obter status de conta")
                    raise PermissionError(f"Failed to retrieve account status, user doesn't have permission to do this request.")
                logger.warning(f"[Tentativa {attempt + 1}/{MAX_RETRIES}] {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        logger.error("Falha ao obter status de conta")
        return "failed to get account status"

    def api_trading_status(self) -> Union[tuple, str]:
        """
        Obtém status de trading da API (se está bloqueada para trading).
        
        Returns:
            Tupla (UFR, IFER, GCR) se desbloqueada, ou mensagem de erro
        """
        for attempt in range(MAX_RETRIES):
            try:
                data = self.client.get_account_api_trading_status()
                if isinstance(data, dict):
                    if data['data']['isLocked'] == False:
                        UFR = data['data']['triggerCondition']['UFR']
                        IFER = data['data']['triggerCondition']['IFER']
                        GCR = data['data']['triggerCondition']['GCR']
                        updateTime = data['data']['updateTime']
                        msg = f"Trading status ok for now, please be careful if trigger conditions: Unfilled Order Ratio = {UFR}, Immediate Fill or Kill Ratio {IFER}, GTC Cancel Ratio{GCR}, conditions will be updated in: {updateTime}"
                        logger.info("Status de trading desbloqueado")
                        logger.info(msg)
                        return UFR, IFER, GCR
                    elif data['data']['isLocked'] == True:
                        recoverTime = data['data']['plannedRecoverTime']
                        msg = f"Account is locked for trading, will be recovered in: {recoverTime}"
                        logger.warning(msg)
                        return msg
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error("Erro de permissão ao obter status de trading")
                    return f"Failed to retrieve account status, user doesn't have permission to do this request."
                logger.warning(f"[Tentativa {attempt + 1}/{MAX_RETRIES}] {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        logger.error("Falha ao obter status de trading")
        return "failed to get trading status"
    
    def get_trades(self, symbol: str) -> pd.DataFrame:
        """
        Obtém histórico de trades executados da conta para um par.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
        
        Returns:
            DataFrame com trades executados ou DataFrame vazio se falhar
        """
        for attempt in range(MAX_RETRIES):
            try:
                data = self.client.get_my_trades(symbol=symbol)
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                    df[['symbol', 'commissionAsset']] = df[['symbol', 'commissionAsset']].astype(str)
                    df[['id', 'orderId', 'orderListId']] = df[['id', 'orderId', 'orderListId']].astype(int)
                    df = df.drop_duplicates(subset=['id']).reset_index(drop=True).set_index('id')
                    df[['price', 'qty', 'quoteQty', 'commission']] = df[['price', 'qty', 'quoteQty', 'commission']].astype(float)
                    df['price'] = df['price'].round(2).dropna()
                    df['time'] = pd.to_datetime(df['time'], unit='ms').dt.strftime('%d/%m/%Y %H:%M:%S')
                    df[['isBuyer', 'isMaker', 'isBestMatch']] = df[['isBuyer', 'isMaker', 'isBestMatch']].astype(bool, errors='ignore')
                    logger.info(f"Obtidos {len(df)} trades para {symbol}")
                    return df
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(f"Failed to get trades for {symbol}, user doesn't have permission to do this request.")
                if "APIError(code=-1100)" in error_msg or "APIError(code=-1121)" in error_msg:
                    logger.error(f"Símbolo inválido: {symbol}")
                    raise KeyError(f"Failed to get trades for {symbol}, invalid symbol provided.")
                logger.warning(f"[Tentativa {attempt + 1}/{MAX_RETRIES}] {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        logger.error(f"Falha ao obter trades para {symbol}")
        return pd.DataFrame()
    
    def get_asset_dividend_history(self, asset: Optional[str] = None) -> pd.DataFrame:
        """
        Obtém histórico de dividendos de ativos da conta.
        
        Args:
            asset: Ativo específico (ex: 'BNB') ou None para todos
        
        Returns:
            DataFrame com histórico de dividendos ou DataFrame vazio se não houver
        """
        for attempt in range(MAX_RETRIES):
            try:
                data = self.client.get_asset_dividend_history(asset=asset)
                if isinstance(data, dict) and data.get('total', 0) != 0:
                    logger.info(f"Histórico de dividendos encontrado: {data['total']} registros")
                    df = pd.DataFrame(data['rows'])
                    df[['id', 'tranId']] = df[['id', 'tranId']].astype(int)
                    df = df.drop_duplicates(subset=['id']).reset_index(drop=True).set_index('id')
                    df['amount'] = df['amount'].astype(float).round(8)
                    df['divTime'] = pd.to_datetime(df['divTime'], unit='ms').dt.strftime('%d/%m/%Y %H:%M:%S')
                    df[['asset', 'enInfo']] = df[['asset', 'enInfo']].astype(str)
                    return df
                elif isinstance(data, dict) and data.get('total', 0) == 0:
                    logger.info(f"Nenhum histórico de dividendos encontrado para {asset}")
                    return pd.DataFrame()
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error("Erro de permissão ao obter histórico de dividendos")
                    raise PermissionError(f"Failed to get asset dividend history, user doesn't have permission to do this request.")
                if "APIError(code=-1100)" in error_msg or "APIError(code=-1121)" in error_msg:
                    logger.error("Parâmetro inválido no histórico de dividendos")
                    raise KeyError(f"Failed to get asset dividend history, invalid parameters provided.")
                logger.warning(f"[Tentativa {attempt + 1}/{MAX_RETRIES}] {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        logger.error("Falha ao obter histórico de dividendos")
        return pd.DataFrame()
    
    def get_all_orders(self, symbol: str, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Obtém todas as ordens (abertas, executadas, canceladas) de um par.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
            limit: Limite de ordens a retornar (None = todas)
        
        Returns:
            DataFrame com ordens ou DataFrame vazio se falhar/vazia
        """
        for attempt in range(MAX_RETRIES):
            try:
                data = self.client.get_all_orders(symbol=symbol, limit=limit)
                if isinstance(data, list) and len(data) > 0:
                    df = pd.DataFrame(data)
                    df = df[["symbol", "orderId", "orderListId", "clientOrderId", "price",
                             "origQty", "executedQty", "cummulativeQuoteQty", "status", "timeInForce",
                             "type", "side", "stopPrice", "icebergQty", "time", "updateTime"]]
                    df[['orderId', 'orderListId']] = df[['orderId', 'orderListId']].astype(int)
                    df = df.drop_duplicates(subset=['orderId']).reset_index(drop=True).set_index('orderId')
                    df[["symbol", "clientOrderId", "status", "timeInForce", "type", "side"]] = \
                        df[["symbol", "clientOrderId", "status", "timeInForce", "type", "side"]].astype(str).fillna(
                            "Field not avaliable for this type of operation")
                    df[['price', 'origQty', 'executedQty', 'cummulativeQuoteQty',
                        'stopPrice', 'icebergQty']] = df[['price', 'origQty', 'executedQty',
                                                          'cummulativeQuoteQty', 'stopPrice', 'icebergQty']].astype(float, errors='ignore').fillna(0.00)
                    df['price'] = df['price'].round(2)
                    for col in ['time', 'updateTime']:
                        df[col] = pd.to_datetime(df[col], unit="ms").dt.strftime('%d/%m/%Y %H:%M:%S')
                    logger.info(f"Obtidas {len(df)} ordens para {symbol}")
                    return df
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error("Erro de permissão ao obter ordens")
                    raise PermissionError(f"Failed to get all orders, user doesn't have permission to do this request.")
                if "APIError(code=-1100)" in error_msg or "APIError(code=-1121)" in error_msg:
                    logger.error("Parâmetro inválido em ordens")
                    raise KeyError(f"Failed to get asset dividend history, invalid parameters provided.")
                logger.warning(f"[Tentativa {attempt + 1}/{MAX_RETRIES}] {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        logger.error(f"Falha ao obter ordens para {symbol}")
        return pd.DataFrame()
    
    def get_asset_balance(self, asset: str) -> pd.DataFrame:
        """
        Obtém saldo de um ativo específico.
        
        Args:
            asset: Símbolo do ativo (ex: 'BTC', 'USDT')
        
        Returns:
            DataFrame com saldo (free e locked) ou DataFrame vazio se falhar
        """
        for attempt in range(MAX_RETRIES):
            try:
                data = self.client.get_asset_balance(asset=asset)
                if isinstance(data, dict):
                    df = pd.DataFrame([data])
                    df['asset'] = df['asset'].astype(str)
                    df[['free', 'locked']] = df[['free', 'locked']].astype(float, errors='ignore').round(6)
                    logger.info(f"Saldo obtido para {asset}")
                    return df
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {asset}")
                    raise PermissionError(f"Failed to get asset dividend history, user doesn't have permission to do this request.")
                if "APIError(code=-1100)" in error_msg or "APIError(code=-1121)" in error_msg:
                    logger.error(f"Símbolo inválido: {asset}")
                    raise KeyError(f"Failed to get asset dividend history, invalid parameters provided.")
                logger.warning(f"[Tentativa {attempt + 1}/{MAX_RETRIES}] {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        logger.error(f"Falha ao obter saldo para {asset}")
        return pd.DataFrame()
