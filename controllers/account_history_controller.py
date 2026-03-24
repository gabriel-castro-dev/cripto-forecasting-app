import logging
from typing import Optional, Tuple, Union
import pandas as pd
from services.binance_account_history_service import BinanceAccountService
from controllers.market_data_controller import MarketDataController

logger = logging.getLogger(__name__)


class AccountHistoryController:
    """
    Controlador responsavel por orquestracao de dados de conta.
    
    Delega toda a logica de transformacao, retry e validacao para o servico.
    O controller apenas orquestra as chamadas aos servicos.
    
    Attributes:
        account_history_service: Instancia de BinanceAccountService (injetada)
        market_data: Instancia de MarketDataController para validacao de conectividade
    """
    
    def __init__(self, account_history_service: BinanceAccountService, 
                 market_data: MarketDataController) -> None:
        """
        Inicializa o controller com dependencias injetadas.
        
        Args:
            account_history_service: Servico de dados de conta (DI)
            market_data: Controller de dados de mercado para health checks
        
        Raises:
            Exception: Se falhar na inicializacao
        """
        try:
            self.account_history_service: BinanceAccountService = account_history_service
            self.market_data: MarketDataController = market_data
            logger.info("AccountHistoryController inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar AccountHistoryController: {e}")
            raise
    
    def account_info(self) -> Union[pd.DataFrame, str]:
        """
        Obtem informacoes de saldo dos ativos da conta.
        
        Returns:
            DataFrame com ativos com saldo > 0 ou mensagem de erro
        """
        return self.account_history_service.account_info()

    def account_status(self) -> str:
        """
        Obtem estado atual da conta (Normal, Locked, etc).
        
        Returns:
            String com status ou mensagem de erro/orientacao
        """
        return self.account_history_service.account_status()

    def api_trading_status(self) -> Union[Tuple, str]:
        """
        Obtem status de trading da API (se esta bloqueada para trading).
        
        Returns:
            Tupla (UFR, IFER, GCR) se desbloqueada, ou mensagem de erro
        """
        return self.account_history_service.api_trading_status()
    
    def get_trades(self, symbol: str) -> pd.DataFrame:
        """
        Obtem historico de trades executados da conta para um par.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
        
        Returns:
            DataFrame com trades executados ou DataFrame vazio se falhar
        """
        return self.account_history_service.get_trades(symbol=symbol)
    
    def get_asset_dividend_history(self, asset: Optional[str] = None) -> pd.DataFrame:
        """
        Obtem historico de dividendos de ativos da conta.
        
        Args:
            asset: Ativo especifico (ex: 'BNB') ou None para todos
        
        Returns:
            DataFrame com historico de dividendos ou DataFrame vazio se nao houver
        """
        return self.account_history_service.get_asset_dividend_history(asset=asset)
    
    def get_all_orders(self, symbol: str, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Obtem todas as ordens (abertas, executadas, canceladas) de um par.
        
        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
            limit: Limite de ordens a retornar (None = todas)
        
        Returns:
            DataFrame com ordens ou DataFrame vazio se falhar/vazia
        """
        return self.account_history_service.get_all_orders(symbol=symbol, limit=limit)
    
    def get_asset_balance(self, asset: str) -> pd.DataFrame:
        """
        Obtem saldo de um ativo especifico.
        
        Args:
            asset: Simbolo do ativo (ex: 'BTC', 'USDT')
        
        Returns:
            DataFrame com saldo (free e locked) ou DataFrame vazio se falhar
        """
        return self.account_history_service.get_asset_balance(asset=asset)
