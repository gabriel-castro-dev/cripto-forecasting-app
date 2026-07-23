import logging
import time
from typing import Optional

from binance.client import Client
from config import settings

logger = logging.getLogger(__name__)


class BinanceClient:
    """
    Cliente responsável por requisições de dados de mercado na API Binance.

    Encapsula todas as chamadas HTTP à Binance REST API, incluindo:
    - Retry logic com validação de conectividade

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
            self.api_key: str = settings.BINANCE_API_KEY
            self.api_secret: str = settings.BINANCE_API_SECRET
            self.test_net: bool = settings.USE_TESTNET

            requests_params = None
            if settings.BINANCE_PROXY:
                requests_params = {
                    "proxies": {
                        "http": settings.BINANCE_PROXY,
                        "https": settings.BINANCE_PROXY,
                    }
                }

            self.client: Client = Client(
                self.api_key,
                self.api_secret,
                testnet=self.test_net,
                requests_params=requests_params,
            )
            self.MAX_RETRIES = settings.MAX_RETRIES
            self.RETRY_DELAY = settings.RETRY_DELAY
            logger.info("BinanceClient inicializado com sucesso")
        except Exception as e:
            logger.error(f"Falha crítica ao conectar na API: {e}")
            raise RuntimeError(
                f"Falha crítica: Não foi possível conectar à API. Erro: {e}"
            )

    def ping(self) -> bool:
        """
        Verifica conectividade com a API Binance.

        Returns:
            Bool indicando status da conexão
        """
        try:
            resultado = self.client.ping()
            if resultado == {}:
                logger.debug("API Binance está acessível")
                return True

            logger.warning(f"Erro inesperado ao fazer ping: {resultado}")
            return False

        except Exception as e:
            logger.error(f"Erro ao fazer ping na API: {e}")
            return False

    def server_time(self) -> dict | None:
        """
        Obtém o horário atual do servidor Binance.

        Returns:
            Dict com timestamp ou None se falhar
        """
        try:
            data = self.client.get_server_time()
            return data
        except Exception as e:
            logger.error(f"Erro ao obter tempo do servidor: {e}")
            return None

    def system_status(self) -> dict | None:
        """
        Obtém status do sistema Binance.

        Returns:
            Dict com status ou None se falhar
        """
        try:
            data = self.client.get_system_status()
            return data
        except Exception as e:
            logger.error(f"Erro ao obter status do sistema: {e}")
            return None

    def get_tickers(self) -> list:
        """
        Obtém lista de todos os tickers do mercado, ordenados por preço.

        Returns:
            Lista com tickers do mercado ou lista vazia se falhar
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                data = self.client.get_all_tickers()
                if isinstance(data, list) and len(data) > 0:
                    return data
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error("Erro de permissão ao obter tickers")
                    raise PermissionError(
                        "Failed to retrieve tickers, user doesn't have permission to do this request."
                    )
                logger.warning(
                    f"[Tentativa {attempt + 1}/{self.MAX_RETRIES}] {error_msg}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(f"Aguardando {self.RETRY_DELAY}s para retry...")
                    time.sleep(self.RETRY_DELAY)

        logger.error("Falha ao obter tickers após todas as tentativas")
        return []

    def get_ticker_24hr(self, symbol: str) -> dict:
        """
        Obtém dados de 24h do par USDT.

        Returns:
            Dicionário com dados 24h ou dicionário vazio se falhar
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                data = self.client.get_ticker(symbol=symbol)
                if isinstance(data, dict):
                    return data
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(
                        f"Failed to retrieve last 24hrs ticker for {symbol}, user doesn't have permission to do this request."
                    )
                if (
                    "APIError(code=-1100)" in error_msg
                    or "APIError(code=-1121)" in error_msg
                ):
                    logger.error(f"Símbolo inválido: {symbol}")
                    raise KeyError(
                        f"Failed to get ticker 24hr for {symbol}, invalid symbol provided."
                    )

                logger.warning(
                    f"[Tentativa {attempt + 1}/{self.MAX_RETRIES}] Erro para {symbol}: {error_msg}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)

        logger.error("Falha ao obter dados 24h após todas as tentativas")
        return {}

    def get_orderbook_tickers(self, symbol: str | list) -> list | dict:
        """
        Obtém informações de order book de um par.

        Args:
            symbol: Par de moedas (ex: 'BTCUSDT') ou lista de pares (ex: ['BTCUSDT', 'ETHUSDT'])

        Returns:
            Lista ou dicionário com dados de order book ou estrutura vazia se falhar
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                data = self.client.get_orderbook_tickers(symbol=symbol)
                if isinstance(data, (list, dict)):
                    return data
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(
                        f"Failed to retrieve orderbook tickers for {symbol}, user doesn't have permission to do this request."
                    )
                if (
                    "APIError(code=-1100)" in error_msg
                    or "APIError(code=-1121)" in error_msg
                ):
                    logger.error(f"Símbolo inválido: {symbol}")
                    raise KeyError(
                        f"Failed to retrieve orderbook tickers for {symbol}, invalid symbol provided."
                    )
                logger.warning(
                    f"[Tentativa {attempt + 1}/{self.MAX_RETRIES}] {error_msg}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)

        logger.error(f"Falha ao obter order book para {symbol}")
        return []

    def get_klines(self, symbol: str, interval: str) -> list:
        """
        Obtém K-lines (velas) em tempo real de um par.

        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
            interval: Intervalo (ex: '1m', '1h', '1d')

        Returns:
            Lista com K-lines ou lista vazia se falhar
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                data = self.client.get_klines(symbol=symbol, interval=interval)
                if isinstance(data, list) and len(data) > 0:
                    return data
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(
                        f"Failed to retrieve last klines for {symbol}, user doesn't have permission to do this request."
                    )
                if (
                    "APIError(code=-1100)" in error_msg
                    or "APIError(code=-1121)" in error_msg
                ):
                    logger.error(f"Parâmetro inválido para {symbol}")
                    raise KeyError(
                        f"Failed to retrieve klines for {symbol}, invalid parameter provided."
                    )
                logger.warning(
                    f"[Tentativa {attempt + 1}/{self.MAX_RETRIES}] {error_msg}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)

        logger.error(f"Falha ao obter k-lines para {symbol}")
        return []

    def get_historical_klines(
        self,
        symbol: str,
        interval: str,
        start_str: str,
        end_str: Optional[str] = None,
        limit: int = 1000,
    ) -> list:
        """
        Obtém K-lines históricas de um período específico.

        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
            interval: Intervalo (ex: '1h', '1d')
            start_str: Data inicial (ex: '10 days ago UTC')
            end_str: Data final (opcional)
            limit: Número máximo de registros

        Returns:
            Lista com k-lines históricas ou lista vazia se falhar
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                data = self.client.get_historical_klines(
                    symbol=symbol,
                    interval=interval,
                    start_str=start_str,
                    end_str=end_str,
                    limit=limit,
                )
                if isinstance(data, list) and len(data) > 0:
                    return data
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(
                        f"Failed to retrieve historical klines for {symbol}, user doesn't have permission to do this request."
                    )
                if (
                    "APIError(code=-1100)" in error_msg
                    or "APIError(code=-1121)" in error_msg
                ):
                    logger.error("Parâmetro inválido em k-lines históricas")
                    raise KeyError(
                        "Failed to retrieve historical klines, invalid parameter provided."
                    )
                logger.warning(
                    f"[Tentativa {attempt + 1}/{self.MAX_RETRIES}] {error_msg}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)

        logger.error(f"Falha ao obter k-lines históricas para {symbol}")
        return []

    def get_historical_klines_generator(
        self, symbol: str, interval: str, timestamp: str
    ) -> list:
        """
        Obtém K-lines históricas usando generator (eficiente para grandes volumes).

        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
            interval: Intervalo (ex: '1h', '1d')
            timestamp: Data inicial (ex: '100 days ago UTC')

        Returns:
            Lista com k-lines geradas ou lista vazia se falhar
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                data = list(
                    self.client.get_historical_klines_generator(
                        symbol=symbol, interval=interval, start_str=timestamp
                    )
                )
                if isinstance(data, list) and len(data) > 0:
                    return data
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(
                        f"Failed to retrieve historical klines generator for {symbol}, user doesn't have permission to do this request."
                    )
                if (
                    "APIError(code=-1100)" in error_msg
                    or "APIError(code=-1121)" in error_msg
                ):
                    logger.error("Parâmetro inválido em generator de k-lines")
                    raise KeyError(
                        "Failed to retrieve historical klines generator, invalid parameter provided."
                    )
                logger.warning(
                    f"[Tentativa {attempt + 1}/{self.MAX_RETRIES}] {error_msg}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)

        logger.error(f"Falha ao gerar k-lines históricas para {symbol}")
        return []

    def get_avg_price(self, symbol: str) -> dict:
        """
        Obtém preço médio de um par.

        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')

        Returns:
            Dicionário com preço médio ou dicionário vazio se falhar
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                data = self.client.get_avg_price(symbol=symbol)
                if isinstance(data, dict):
                    return data
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(
                        f"Failed to retrieve average prices {symbol}, user doesn't have permission to do this request."
                    )
                if (
                    "APIError(code=-1100)" in error_msg
                    or "APIError(code=-1121)" in error_msg
                ):
                    logger.error(f"Símbolo inválido: {symbol}")
                    raise KeyError(
                        f"Failed to retrieve average prices for {symbol}, invalid symbol provided."
                    )
                logger.warning(
                    f"[Tentativa {attempt + 1}/{self.MAX_RETRIES}] {error_msg}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)

        logger.error(f"Falha ao obter preço médio para {symbol}")
        return {}

    def get_recent_trades(
        self, symbol: str, limit: Optional[int] = None
    ) -> list | dict:
        """
        Obtém trades recentes de um par.

        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
            limit: Número máximo de trades a retornar

        Returns:
            Lista com trades recentes ou lista vazia se falhar
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                data = self.client.get_recent_trades(symbol=symbol, limit=limit)
                if isinstance(data, (list, dict)):
                    return data
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(
                        f"Failed to retrieve recent trades for {symbol}, user doesn't have permission to do this request."
                    )
                if (
                    "APIError(code=-1100)" in error_msg
                    or "APIError(code=-1121)" in error_msg
                ):
                    logger.error(f"Símbolo inválido: {symbol}")
                    raise KeyError(
                        f"Failed to retrieve recent trades for {symbol}, invalid symbol provided."
                    )
                logger.warning(
                    f"[Tentativa {attempt + 1}/{self.MAX_RETRIES}] {error_msg}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)

        logger.error(f"Falha ao obter trades recentes para {symbol}")
        return []

    def get_historical_trades(self, symbol: str) -> list | dict:
        """
        Obtém histórico de trades de um par.

        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')

        Returns:
            Lista com trades históricos ou lista vazia se falhar
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                data = self.client.get_historical_trades(symbol=symbol)
                if isinstance(data, (list, dict)):
                    return data
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(
                        f"Failed to retrieve historical trades for {symbol}, user doesn't have permission to do this request."
                    )
                if (
                    "APIError(code=-1100)" in error_msg
                    or "APIError(code=-1121)" in error_msg
                ):
                    logger.error(f"Símbolo inválido: {symbol}")
                    raise KeyError(
                        f"Failed to retrieve historical trades for {symbol}, invalid symbol provided."
                    )
                logger.warning(
                    f"[Tentativa {attempt + 1}/{self.MAX_RETRIES}] {error_msg}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)

        logger.error(f"Falha ao obter trades históricos para {symbol}")
        return []

    def get_aggregate_trades(self, symbol: str) -> list:
        """
        Obtém agregação de trades de um par.

        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')

        Returns:
            Lista com trades agregados ou lista vazia se falhar
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                data = self.client.get_aggregate_trades(symbol=symbol)
                if isinstance(data, list):
                    return data
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(
                        f"Failed to retrieve aggregate trades for {symbol}, user doesn't have permission to do this request."
                    )
                if (
                    "APIError(code=-1100)" in error_msg
                    or "APIError(code=-1121)" in error_msg
                ):
                    logger.error(f"Símbolo inválido: {symbol}")
                    raise KeyError(
                        f"Failed to retrieve aggregate trades for {symbol}, invalid symbol provided."
                    )
                logger.warning(
                    f"[Tentativa {attempt + 1}/{self.MAX_RETRIES}] {error_msg}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)

        logger.error(f"Falha ao obter trades agregados para {symbol}")
        return []

    def get_depth(self, symbol: str) -> dict:
        """
        Obtém profundidade de mercado (order book depth) de um par.

        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')

        Returns:
            Dicionário com profundidade ou dicionário vazio se falhar
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                data = self.client.get_order_book(symbol=symbol)
                if isinstance(data, dict):
                    return data
            except Exception as e:
                error_msg = str(e)
                if "APIError(code=-2015)" in error_msg:
                    logger.error(f"Erro de permissão para {symbol}")
                    raise PermissionError(
                        f"Failed to get depth for {symbol}, user doesn't have permission to do this request."
                    )
                if (
                    "APIError(code=-1100)" in error_msg
                    or "APIError(code=-1121)" in error_msg
                ):
                    logger.error(f"Símbolo inválido: {symbol}")
                    raise KeyError(
                        f"Failed to get depth for {symbol}, invalid symbol provided."
                    )
                logger.warning(
                    f"[Tentativa {attempt + 1}/{self.MAX_RETRIES}] {error_msg}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAY)

        logger.error(f"Falha ao obter profundidade de mercado para {symbol}")
        return {}
