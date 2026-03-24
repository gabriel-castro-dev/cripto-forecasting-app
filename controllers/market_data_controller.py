import logging
from typing import Optional
import pandas as pd
from services.binance_market_data_service import BinanceMarketService

logger = logging.getLogger(__name__)


class MarketDataController:
    """
    Controlador responsavel por orquestracao de dados de mercado.
    
    Delega toda a logica de transformacao, retry e validacao para o servico.
    O controller apenas orquestra as chamadas aos servicos.
    
    Attributes:
        market_data_service: Instancia de BinanceMarketService (injetada)
    """
    
    def __init__(self, market_data_service: BinanceMarketService) -> None:
        """
        Inicializa o controller com dependencia injetada.
        
        Args:
            market_data_service: Servico de dados de mercado (DI)
        
        Raises:
            Exception: Se falhar na inicializacao
        """
        try:
            self.market_data_service: BinanceMarketService = market_data_service
            logger.info("MarketDataController inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar MarketDataController: {e}")
            raise

    def ping(self) -> str:
        """
        Verifica conectividade com a API Binance.
        
        Returns:
            Mensagem indicando status da conexao
        """
        return self.market_data_service.ping()
            
    def server_time(self) -> dict:
        """
        Obtem o tempo do servidor Binance.
        
        Returns:
            Dict com informacoes de tempo ou erro
        """
        return self.market_data_service.server_time()

    def system_status(self) -> dict:
        """
        Obtem status do sistema Binance.
        
        Returns:
            Dict com informacoes de status ou erro
        """
        return self.market_data_service.system_status()

    def get_tickers(self) -> pd.DataFrame:
        """
        Obtem lista de todos os tickers com pares USDT, ordenados por preco.
        
        Returns:
            DataFrame com tickers USDT ordenados ou DataFrame vazio se falhar
        """
        return self.market_data_service.get_tickers()
            
    def get_ticker_24hr(self) -> pd.DataFrame:
        """
        Obtem dados de 24h dos pares USDT.
        
        Returns:
            DataFrame com dados 24h ou DataFrame vazio se falhar
        """
        return self.market_data_service.get_ticker_24hr()
    
    def get_orderbook_tickers(self, symbol: str) -> pd.DataFrame:
        """
        Obtem informacoes de order book de um par.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
        
        Returns:
            DataFrame com dados de order book ou DataFrame vazio se falhar
        """
        return self.market_data_service.get_orderbook_tickers(symbol=symbol)
    
    def get_klines(self, symbol: str, interval: str) -> pd.DataFrame:
        """
        Obtem K-lines (velas) em tempo real de um par.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
            interval: Intervalo (ex: '1m', '1h', '1d')
        
        Returns:
            DataFrame com OHLCV ou DataFrame vazio se falhar
        """
        return self.market_data_service.get_klines(symbol=symbol, interval=interval)
    
    def get_historical_klines(self, symbol: str, interval: str, start_str: str, 
                             end_str: Optional[str] = None, limit: int = 1000) -> pd.DataFrame:
        """
        Obtem K-lines historicas de um periodo especifico.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
            interval: Intervalo (ex: '1h', '1d')
            start_str: Data inicial (ex: '10 days ago UTC')
            end_str: Data final (opcional)
            limit: Numero maximo de registros
        
        Returns:
            DataFrame com k-lines historicas ou DataFrame vazio se falhar
        """
        return self.market_data_service.get_historical_klines(symbol=symbol, interval=interval,
                                                              start_str=start_str, end_str=end_str, limit=limit)

    def get_historical_klines_generator(self, symbol: str, interval: str, timestamp: str) -> pd.DataFrame:
        """
        Obtem K-lines historicas usando generator (eficiente para grandes volumes).
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
            interval: Intervalo (ex: '1h', '1d')
            timestamp: Data inicial (ex: '100 days ago UTC')
        
        Returns:
            DataFrame com k-lines geradas ou DataFrame vazio se falhar
        """
        return self.market_data_service.get_historical_klines_generator(symbol=symbol, interval=interval,
                                                                        timestamp=timestamp)

    def get_avg_price(self, symbol: str) -> pd.DataFrame:
        """
        Obtem preco medio de um par.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
        
        Returns:
            DataFrame com preco medio ou DataFrame vazio se falhar
        """
        return self.market_data_service.get_avg_price(symbol=symbol)
    
    def get_recent_trades(self, symbol: str, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Obtem trades recentes de um par.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
            limit: Numero maximo de trades
        
        Returns:
            DataFrame com trades recentes ou DataFrame vazio se falhar
        """
        return self.market_data_service.get_recent_trades(symbol=symbol, limit=limit)
    
    def get_historical_trades(self, symbol: str) -> pd.DataFrame:
        """
        Obtem historico de trades de um par.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
        
        Returns:
            DataFrame com trades historicos ou DataFrame vazio se falhar
        """
        return self.market_data_service.get_historical_trades(symbol=symbol)
    
    def get_aggregate_trades(self, symbol: str) -> pd.DataFrame:
        """
        Obtem agregacao de trades de um par.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
        
        Returns:
            DataFrame com trades agregados ou DataFrame vazio se falhar
        """
        return self.market_data_service.get_aggregate_trades(symbol=symbol)
    
    def get_depth(self, symbol: str) -> pd.DataFrame:
        """
        Obtem profundidade de mercado (order book depth) de um par.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
        
        Returns:
            DataFrame com profundidade ou DataFrame vazio se falhar
        """
        return self.market_data_service.get_depth(symbol=symbol)
