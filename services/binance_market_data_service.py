import logging
import pandas as pd
import time
from typing import Dict, List, Optional, Union, Generator
from env.keys import BINANCE_API_KEY, BINANCE_API_SECRET
from binance.client import Client
from binance.enums import *
from config import MAX_RETRIES, RETRY_DELAY

logger = logging.getLogger(__name__)


class BinanceMarketService:
    """
    Serviço responsável por requisições e transformação de dados de mercado na API Binance.
    
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
        Inicializa o serviço de dados de mercado.
        
        Raises:
            RuntimeError: Se não conseguir conectar à API Binance
        """
        try:
            self.api_key: str = BINANCE_API_KEY
            self.api_secret: str = BINANCE_API_SECRET
            self.client: Client = Client(self.api_key, self.api_secret, testnet=True)
            logger.info("BinanceMarketService inicializado com sucesso")
        except Exception as e:
            logger.error(f"Falha crítica ao conectar na API: {e}")
            raise RuntimeError(f"Falha crítica: Não foi possível conectar à API. Erro: {e}")

    def ping(self) -> str:
        """
        Verifica conectividade com a API Binance.
        
        Returns:
            Mensagem indicando status da conexão
        """
        try:
            resultado = self.client.ping()
            if resultado == {}:
                logger.debug("API Binance está acessível")
                return "Binance API is reachable."
            else:
                logger.warning(f"Erro ao fazer ping: {resultado}")
                return resultado
        except Exception as e:
            logger.error(f"Erro ao fazer ping na API: {e}")
            return f"Error pinging Binance API: {e}"

    def server_time(self) -> dict:
        """
        Obtém o horário atual do servidor Binance.
        
        Returns:
            Dict com timestamp ou mensagem de erro
        """
        try:
            result = self.client.get_server_time()
            return result
        except Exception as e:
            logger.error(f"Erro ao obter tempo do servidor: {e}")
            return f"Error getting server time: {e}"

    def system_status(self) -> dict:
        """
        Obtém status do sistema Binance.
        
        Returns:
            Dict com status ou mensagem de erro
        """
        try:
            result = self.client.get_system_status()
            return result
        except Exception as e:
            logger.error(f"Erro ao obter status do sistema: {e}")
            return f"Error getting system status: {e}"

    def get_tickers(self) -> pd.DataFrame:
        """
        Obtém lista de todos os tickers com pares USDT, ordenados por preço.
        
        Returns:
            DataFrame com tickers USDT ordenados ou DataFrame vazio se falhar
        """
        for attempt in range(MAX_RETRIES):
            try:
                data = self.client.get_all_tickers()
                if isinstance(data, list) and len(data) > 0:
                    df = pd.DataFrame(data)
                    usdt_tickers = df[df['symbol'].str.endswith('USDT')].copy()
                    usdt_tickers['price'] = usdt_tickers['price'].astype(float, errors='ignore').round(2).dropna()
                    usdt_tickers = usdt_tickers.sort_values(by='price', ascending=False).reset_index(drop=True)
                    logger.info(f"Obtidos {len(usdt_tickers)} tickers USDT")
                    return usdt_tickers
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error("Erro de permissão ao obter tickers")
                    raise PermissionError(f"Failed to retrieve tickers, user doesn't have permission to do this request.")
                logger.warning(f"[Tentativa {attempt + 1}/{MAX_RETRIES}] {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Aguardando {RETRY_DELAY}s para retry...")
                    time.sleep(RETRY_DELAY)

        logger.error("Falha ao obter tickers após todas as tentativas")
        return pd.DataFrame()

    def get_ticker_24hr(self) -> pd.DataFrame:
        """
        Obtém dados de 24h dos pares USDT.
        
        Returns:
            DataFrame com dados 24h ou DataFrame vazio se falhar
        """
        for attempt in range(MAX_RETRIES):
            try:
                df_tickers = self.get_tickers()
                if df_tickers.empty:
                    logger.error("Não foi possível obter a lista de símbolos base.")
                    return pd.DataFrame()
                
                symbols = df_tickers['symbol'].tolist()
                data_list = []
                
                for symbol in symbols:
                    try:
                        data = self.client.get_ticker(symbol=symbol)
                        if isinstance(data, dict):
                            data_list.append(data)
                    except Exception as e:
                        error_msg = str(e)
                        if "APIError(code=-2015)" in error_msg:
                            logger.error(f"Erro de permissão para {symbol}")
                            raise PermissionError(f"Failed to retrieve last 24hrs ticker for {symbol}, user doesn't have permission to do this request.")
                        if "APIError(code=-1100)" in error_msg or "APIError(code=-1121)" in error_msg:
                            logger.error(f"Símbolo inválido: {symbol}")
                            raise KeyError(f"Failed to get ticker 24hr for {symbol}, invalid symbol provided.")
                        logger.warning(f"Erro para {symbol}: {error_msg}")
                
                if data_list:
                    df = pd.DataFrame(data_list)
                    ignorar_colunas = ['symbol', 'openTime', 'closeTime', 'firstId', 'lastId', 'count']
                    cols_to_numeric = [col for col in df.columns if col not in ignorar_colunas]
                    df[cols_to_numeric] = df[cols_to_numeric].astype(float, errors='ignore').round(8).dropna()
                    df['openTime'] = pd.to_datetime(df['openTime'], unit='ms')
                    df['closeTime'] = pd.to_datetime(df['closeTime'], unit='ms')
                    df[['symbol', 'firstId', 'lastId']] = df[['symbol', 'firstId', 'lastId']].astype(str)
                    df['count'] = df['count'].astype(int)
                    logger.info(f"Dados 24h obtidos para {len(symbols)} símbolos")
                    return df
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"[Tentativa {attempt + 1}/{MAX_RETRIES}] Erro: {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        logger.error("Falha ao obter dados 24h após todas as tentativas")
        return pd.DataFrame()

    def get_orderbook_tickers(self, symbol: str) -> pd.DataFrame:
        """
        Obtém informações de order book de um par.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
        
        Returns:
            DataFrame com dados de order book ou DataFrame vazio se falhar
        """
        for attempt in range(MAX_RETRIES):
            try:
                data = self.client.get_orderbook_tickers(symbol=symbol)
                if isinstance(data, dict):
                    df = pd.DataFrame([data])
                    df['symbol'] = df['symbol'].astype(str)
                    df[['bidPrice', 'bidQty', 'askPrice', 'askQty']] = df[['bidPrice', 'bidQty', 'askPrice', 'askQty']].astype(float, errors='ignore').round(8).dropna()
                    logger.info(f"Order book obtido para {symbol}")
                    return df
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(f"Failed to retrieve orderbook tickers for {symbol}, user doesn't have permission to do this request.")
                if "APIError(code=-1100)" in error_msg or "APIError(code=-1121)" in error_msg:
                    logger.error(f"Símbolo inválido: {symbol}")
                    raise KeyError(f"Failed to retrieve orderbook tickers for {symbol}, invalid symbol provided.")
                logger.warning(f"[Tentativa {attempt + 1}/{MAX_RETRIES}] {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        logger.error(f"Falha ao obter order book para {symbol}")
        return pd.DataFrame()

    def get_klines(self, symbol: str, interval: str) -> pd.DataFrame:
        """
        Obtém K-lines (velas) em tempo real de um par.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
            interval: Intervalo (ex: '1m', '1h', '1d')
        
        Returns:
            DataFrame com OHLCV ou DataFrame vazio se falhar
        """
        for attempt in range(MAX_RETRIES):
            try:
                data = self.client.get_klines(symbol=symbol, interval=interval)
                if isinstance(data, list) and len(data) > 0:
                    columns = ['Open_Time', 'Open', 'High', 'Low', 'Close', 'Volume',
                              'Close_Time', 'Quote_Asset_Volume', 'Number_of_Trades',
                              'Taker_Buy_Base_Asset_Volume', 'Taker_Buy_Quote_Asset_Volume', 'Ignore']
                    df = pd.DataFrame(data=data, columns=columns)
                    df = df.drop(columns=['Ignore'])
                    df['Open_Time'] = pd.to_datetime(df['Open_Time'], unit='ms')
                    df['Close_Time'] = pd.to_datetime(df['Close_Time'], unit='ms')
                    df['Number_of_Trades'] = df['Number_of_Trades'].astype(int)
                    df[['Open', 'High', 'Low', 'Close', 'Volume', 'Quote_Asset_Volume',
                        'Taker_Buy_Base_Asset_Volume', 'Taker_Buy_Quote_Asset_Volume']] = df[['Open', 'High', 'Low', 'Close', 'Volume', 'Quote_Asset_Volume',
                            'Taker_Buy_Base_Asset_Volume', 'Taker_Buy_Quote_Asset_Volume']].apply(
                                pd.to_numeric, errors='coerce').round(8).dropna()
                    logger.info(f"Obtidas {len(df)} k-lines para {symbol} ({interval})")
                    return df
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(f"Failed to retrieve last klines for {symbol}, user doesn't have permission to do this request.")
                if "APIError(code=-1100)" in error_msg or "APIError(code=-1121)" in error_msg:
                    logger.error(f"Parâmetro inválido para {symbol}")
                    raise KeyError(f"Failed to retrieve klines for {symbol}, invalid parameter provided.")
                logger.warning(f"[Tentativa {attempt + 1}/{MAX_RETRIES}] {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        logger.error(f"Falha ao obter k-lines para {symbol}")
        return pd.DataFrame()

    def get_historical_klines(self, symbol: str, interval: str, start_str: str,
                             end_str: Optional[str] = None, limit: int = 1000) -> pd.DataFrame:
        """
        Obtém K-lines históricas de um período específico.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
            interval: Intervalo (ex: '1h', '1d')
            start_str: Data inicial (ex: '10 days ago UTC')
            end_str: Data final (opcional)
            limit: Número máximo de registros
        
        Returns:
            DataFrame com k-lines históricas ou DataFrame vazio se falhar
        """
        for attempt in range(MAX_RETRIES):
            try:
                data = self.client.get_historical_klines(symbol=symbol, interval=interval,
                                                    start_str=start_str, end_str=end_str, limit=limit)
                if isinstance(data, list) and len(data) > 0:
                    columns = ['Open_Time', 'Open', 'High', 'Low', 'Close', 'Volume',
                              'Close_Time', 'Quote_Asset_Volume', 'Number_of_Trades',
                              'Taker_Buy_Base_Asset_Volume', 'Taker_Buy_Quote_Asset_Volume', 'Ignore']
                    df = pd.DataFrame(data=data, columns=columns)
                    df = df.drop(columns=['Ignore'])
                    df['Open_Time'] = pd.to_datetime(df['Open_Time'], unit='ms').dt.strftime('%d/%m/%Y %H:%M:%S')
                    df['Close_Time'] = pd.to_datetime(df['Close_Time'], unit='ms').dt.strftime('%d/%m/%Y %H:%M:%S')
                    df['Number_of_Trades'] = df['Number_of_Trades'].astype(int)
                    df[['Open', 'High', 'Low', 'Close', 'Volume', 'Quote_Asset_Volume',
                        'Taker_Buy_Base_Asset_Volume', 'Taker_Buy_Quote_Asset_Volume']] = \
                        df[['Open', 'High', 'Low', 'Close', 'Volume', 'Quote_Asset_Volume',
                            'Taker_Buy_Base_Asset_Volume', 'Taker_Buy_Quote_Asset_Volume']].astype(
                                float, errors='ignore').round(8).dropna()
                    logger.info(f"Obtidas {len(df)} k-lines históricas para {symbol}")
                    return df
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(f"Failed to retrieve historical klines for {symbol}, user doesn't have permission to do this request.")
                if "APIError(code=-1100)" in error_msg or "APIError(code=-1121)" in error_msg:
                    logger.error("Parâmetro inválido em k-lines históricas")
                    raise KeyError("Failed to retrieve historical klines, invalid parameter provided.")
                logger.warning(f"[Tentativa {attempt + 1}/{MAX_RETRIES}] {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        logger.error(f"Falha ao obter k-lines históricas para {symbol}")
        return pd.DataFrame()

    def get_historical_klines_generator(self, symbol: str, interval: str, timestamp: str) -> pd.DataFrame:
        """
        Obtém K-lines históricas usando generator (eficiente para grandes volumes).
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
            interval: Intervalo (ex: '1h', '1d')
            timestamp: Data inicial (ex: '100 days ago UTC')
        
        Returns:
            DataFrame com k-lines geradas ou DataFrame vazio se falhar
        """
        for attempt in range(MAX_RETRIES):
            try:
                data = list(self.client.get_historical_klines_generator(symbol=symbol, interval=interval,
                                                                       start_str=timestamp))
                if isinstance(data, list) and len(data) > 0:
                    columns = ['Open_Time', 'Open', 'High', 'Low', 'Close', 'Volume',
                              'Close_Time', 'Quote_Asset_Volume', 'Number_of_Trades',
                              'Taker_Buy_Base_Asset_Volume', 'Taker_Buy_Quote_Asset_Volume', 'Ignore']
                    df = pd.DataFrame(data=data, columns=columns)
                    df = df.drop(columns=['Ignore'])
                    df['Open_Time'] = pd.to_datetime(df['Open_Time'], unit="ms").dt.strftime('%d/%m/%Y %H:%M:%S')
                    df['Close_Time'] = pd.to_datetime(df['Close_Time'], unit="ms").dt.strftime('%d/%m/%Y %H:%M:%S')
                    df['Number_of_Trades'] = df['Number_of_Trades'].astype(int)
                    df[['Open', 'High', 'Low', 'Close', 'Volume', 'Quote_Asset_Volume',
                        'Taker_Buy_Base_Asset_Volume', 'Taker_Buy_Quote_Asset_Volume']] = \
                        df[['Open', 'High', 'Low', 'Close', 'Volume', 'Quote_Asset_Volume',
                            'Taker_Buy_Base_Asset_Volume', 'Taker_Buy_Quote_Asset_Volume']].astype(
                                float, errors='ignore').round(8).dropna()
                    logger.info(f"Geradas {len(df)} k-lines históricas para {symbol} via generator")
                    return df
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(f"Failed to retrieve historical klines generator for {symbol}, user doesn't have permission to do this request.")
                if "APIError(code=-1100)" in error_msg or "APIError(code=-1121)" in error_msg:
                    logger.error("Parâmetro inválido em generator de k-lines")
                    raise KeyError("Failed to retrieve historical klines generator, invalid parameter provided.")
                logger.warning(f"[Tentativa {attempt + 1}/{MAX_RETRIES}] {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        logger.error(f"Falha ao gerar k-lines históricas para {symbol}")
        return pd.DataFrame()

    def get_avg_price(self, symbol: str) -> pd.DataFrame:
        """
        Obtém preço médio de um par.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
        
        Returns:
            DataFrame com preço médio ou DataFrame vazio se falhar
        """
        for attempt in range(MAX_RETRIES):
            try:
                data = self.client.get_avg_price(symbol=symbol)
                if isinstance(data, dict):
                    df = pd.DataFrame([data])
                    df['mins'] = df['mins'].astype(str)
                    df["price"] = df["price"].astype(float, errors='ignore').round(2).dropna()
                    df['closeTime'] = pd.to_datetime(df['closeTime'], unit="ms").dt.strftime('%d/%m/%Y %H:%M:%S')
                    logger.info(f"Preço médio obtido para {symbol}")
                    return df
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(f"Failed to retrieve average prices {symbol}, user doesn't have permission to do this request.")
                if "APIError(code=-1100)" in error_msg or "APIError(code=-1121)" in error_msg:
                    logger.error(f"Símbolo inválido: {symbol}")
                    raise KeyError(f"Failed to retrieve average prices for {symbol}, invalid symbol provided.")
                logger.warning(f"[Tentativa {attempt + 1}/{MAX_RETRIES}] {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        logger.error(f"Falha ao obter preço médio para {symbol}")
        return pd.DataFrame()

    def get_recent_trades(self, symbol: str, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Obtém trades recentes de um par.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
            limit: Número máximo de trades a retornar
        
        Returns:
            DataFrame com trades recentes ou DataFrame vazio se falhar
        """
        for attempt in range(MAX_RETRIES):
            try:
                data = self.client.get_recent_trades(symbol=symbol, limit=limit)
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                    df['id'] = df['id'].astype(int)
                    df["price"] = df["price"].astype(float, errors='ignore').round(2).dropna()
                    df[['qty', 'quoteQty']] = df[['qty', 'quoteQty']].astype(float, errors='ignore').round(8).dropna()
                    df['time'] = pd.to_datetime(df['time'], unit="ms").dt.strftime('%d/%m/%Y %H:%M:%S')
                    df[['isBuyerMaker', 'isBestMatch']] = df[['isBuyerMaker', 'isBestMatch']].astype(bool, errors='ignore')
                    logger.info(f"Obtidos {len(df)} trades recentes para {symbol}")
                    return df
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(f"Failed to retrieve recent trades for {symbol}, user doesn't have permission to do this request.")
                if "APIError(code=-1100)" in error_msg or "APIError(code=-1121)" in error_msg:
                    logger.error(f"Símbolo inválido: {symbol}")
                    raise KeyError(f"Failed to retrieve recent trades for {symbol}, invalid symbol provided.")
                logger.warning(f"[Tentativa {attempt + 1}/{MAX_RETRIES}] {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        logger.error(f"Falha ao obter trades recentes para {symbol}")
        return pd.DataFrame()

    def get_historical_trades(self, symbol: str) -> pd.DataFrame:
        """
        Obtém histórico de trades de um par.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
        
        Returns:
            DataFrame com trades históricos ou DataFrame vazio se falhar
        """
        for attempt in range(MAX_RETRIES):
            try:
                data = self.client.get_historical_trades(symbol=symbol)
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                    df['id'] = df['id'].astype(int)
                    df = df.drop_duplicates(subset=['id']).reset_index(drop=True).set_index('id')
                    df["price"] = df["price"].astype(float, errors='ignore').round(2).dropna()
                    df[['qty', 'quoteQty']] = df[['qty', 'quoteQty']].astype(float, errors='ignore').round(8).dropna()
                    df['time'] = pd.to_datetime(df['time'], unit="ms").dt.strftime('%d/%m/%Y %H:%M:%S')
                    df[['isBuyerMaker', 'isBestMatch']] = df[['isBuyerMaker', 'isBestMatch']].astype(bool, errors='ignore')
                    logger.info(f"Obtidos {len(df)} trades históricos para {symbol}")
                    return df
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(f"Failed to retrieve historical trades for {symbol}, user doesn't have permission to do this request.")
                if "APIError(code=-1100)" in error_msg or "APIError(code=-1121)" in error_msg:
                    logger.error(f"Símbolo inválido: {symbol}")
                    raise KeyError(f"Failed to retrieve historical trades for {symbol}, invalid symbol provided.")
                logger.warning(f"[Tentativa {attempt + 1}/{MAX_RETRIES}] {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        logger.error(f"Falha ao obter trades históricos para {symbol}")
        return pd.DataFrame()

    def get_aggregate_trades(self, symbol: str) -> pd.DataFrame:
        """
        Obtém agregação de trades de um par.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
        
        Returns:
            DataFrame com trades agregados ou DataFrame vazio se falhar
        """
        for attempt in range(MAX_RETRIES):
            try:
                data = self.client.get_aggregate_trades(symbol=symbol)
                if isinstance(data, list):
                    df = pd.DataFrame(data)
                    df = df.rename(columns={"a":"Aggregate_Trade_Id", "p": "price", "q": "Quantity",
                                       "f":"First_Trade_Id", "l": "Last_Trade_Id","T":
                                       "TimeStamp", "m": "isBuyerMaker", "M":"isBestMatch"})
                    df['Aggregate_Trade_Id'] = df['Aggregate_Trade_Id'].astype(int)
                    df = df.drop_duplicates(subset=['Aggregate_Trade_Id']).reset_index(drop=True).set_index('Aggregate_Trade_Id')
                    df["price"] = df["price"].astype(float, errors='ignore').round(2).dropna()
                    df['Quantity'] = df['Quantity'].astype(float, errors='ignore').round(8).dropna()
                    df[['First_Trade_Id','Last_Trade_Id']] = df[['First_Trade_Id','Last_Trade_Id']].astype(int)
                    df['TimeStamp'] = pd.to_datetime(df['TimeStamp'], unit="ms").dt.strftime('%d/%m/%Y %H:%M:%S')
                    df[['isBuyerMaker', 'isBestMatch']] = df[['isBuyerMaker', 'isBestMatch']].astype(bool, errors='ignore')
                    logger.info(f"Obtidos {len(df)} trades agregados para {symbol}")
                    return df
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(f"Failed to retrieve aggregate trades for {symbol}, user doesn't have permission to do this request.")
                if "APIError(code=-1100)" in error_msg or "APIError(code=-1121)" in error_msg:
                    logger.error(f"Símbolo inválido: {symbol}")
                    raise KeyError(f"Failed to retrieve aggregate trades for {symbol}, invalid symbol provided.")
                logger.warning(f"[Tentativa {attempt + 1}/{MAX_RETRIES}] {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        logger.error(f"Falha ao obter trades agregados para {symbol}")
        return pd.DataFrame()

    def get_depth(self, symbol: str) -> pd.DataFrame:
        """
        Obtém profundidade de mercado (order book depth) de um par.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
        
        Returns:
            DataFrame com profundidade ou DataFrame vazio se falhar
        """
        for attempt in range(MAX_RETRIES):
            try:
                data = self.client.get_order_book(symbol=symbol)
                if isinstance(data, dict):
                    update_id = data.get('lastUpdateId')
                    df_bids = pd.DataFrame(data['bids'], columns=['price', 'quantity'])
                    df_bids['side'] = 'bid'
                    df_asks = pd.DataFrame(data['asks'], columns=['price', 'quantity'])
                    df_asks['side'] = 'ask'
                    df_full = pd.concat([df_bids, df_asks], ignore_index=True)
                    df_full['lastUpdateId'] = update_id
                    df_full[['price', 'quantity']] = df_full[['price', 'quantity']].astype(float)
                    logger.info(f"Profundidade de mercado obtida para {symbol}")
                    return df_full
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(f"Failed to get depth for {symbol}, user doesn't have permission to do this request.")
                if "APIError(code=-1100)" in error_msg or "APIError(code=-1121)" in error_msg:
                    logger.error(f"Símbolo inválido: {symbol}")
                    raise KeyError(f"Failed to get depth for {symbol}, invalid symbol provided.")
                logger.warning(f"[Tentativa {attempt + 1}/{MAX_RETRIES}] {error_msg}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)

        logger.error(f"Falha ao obter profundidade de mercado para {symbol}")
        return pd.DataFrame()
