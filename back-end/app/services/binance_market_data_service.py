import logging
from typing import Optional

import pandas as pd
from app.clients.binance_client import BinanceClient

logger = logging.getLogger(__name__)


class BinanceMarketService:
    """
    Serviço responsável por requisições e transformação de dados de mercado na API Binance.

    Encapsula todas as transformações dos dados provenientes da API Binance, incluindo:
    - Retry logic com validação de conectividade
    - Transformação de dados brutos em DataFrames estruturados
    - Type casting apropriado (int, float, datetime)
    - Validação de dados e tratamento de erros específicos

    Attributes:
        client: Classe BinanceClient já autenticada para requisições de dados de mercado
    """

    def __init__(self) -> None:
        """
        Inicializa o serviço de dados de mercado.

        Raises:
            RuntimeError: Se não conseguir conectar à API Binance
        """
        try:
            self.client = BinanceClient()
            logger.info("BinanceMarketService inicializado com sucesso")
        except Exception as e:
            logger.error("Falha crítica ao iniciar cliente Binance")
            raise RuntimeError(f"{e}")

    def ping(self) -> str:
        """
        Verifica conectividade com a API Binance.

        Returns:
            Mensagem indicando status da conexão
        """
        resultado = self.client.ping()
        if resultado:
            return "Binance API is reachable."

        return "Error pinging Binance API"

    def server_time(self) -> dict:
        """
        Obtém o horário atual do servidor Binance.

        Returns:
            Dict com timestamp ou mensagem de erro
        """
        result = self.client.server_time()

        if result is None:
            return {
                "status": "error",
                "message": "Não foi possível obter o horário do servidor.",
            }

        return result

    def system_status(self) -> dict:
        """
        Obtém status do sistema Binance.

        Returns:
            Dict com status ou mensagem de erro
        """
        result = self.client.system_status()

        if result is None:
            return {
                "status": "error",
                "message": "Não foi possível obter o status do sistema.",
            }

        return result

    def get_tickers(self) -> pd.DataFrame:
        """
        Obtém lista de todos os tickers com pares USDT, ordenados por preço.

        Returns:
            DataFrame com tickers USDT ordenados ou DataFrame vazio se falhar
        """
        data = self.client.get_tickers()
        if data:
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                usdt_tickers = df[df["symbol"].str.endswith("USDT")].copy()
                usdt_tickers["price"] = pd.to_numeric(
                    usdt_tickers["price"], errors="coerce"
                )
                usdt_tickers["price"] = usdt_tickers["price"].round(2)
                usdt_tickers = usdt_tickers.dropna(subset=["price"])
                usdt_tickers = usdt_tickers.sort_values(
                    by="price", ascending=False
                ).reset_index(drop=True)
                logger.info(f"Obtidos {len(usdt_tickers)} tickers USDT")
                return usdt_tickers
        else:
            logger.error("Falha ao transformar tickers")
            return pd.DataFrame()

    def get_ticker_24hr(self) -> pd.DataFrame:
        """
        Obtém dados de 24h dos pares USDT.

        Returns:
            DataFrame com dados 24h ou DataFrame vazio se falhar
        """
        df_tickers = self.get_tickers()
        symbols = df_tickers["symbol"].tolist()
        data_list = []

        if not df_tickers.empty:
            for symbol in symbols:
                data = self.client.get_ticker_24hr(symbol=symbol)
                if isinstance(data, dict) and data:
                    data_list.append(data)

            if data_list:
                df = pd.DataFrame(data_list)
                ignorar_colunas = [
                    "symbol",
                    "openTime",
                    "closeTime",
                    "firstId",
                    "lastId",
                    "count",
                ]
                cols_to_numeric = [
                    col for col in df.columns if col not in ignorar_colunas
                ]
                df[cols_to_numeric] = df[cols_to_numeric].apply(
                    pd.to_numeric, errors="coerce"
                )
                df[cols_to_numeric] = df[cols_to_numeric].round(8)
                df = df.dropna(subset=cols_to_numeric)
                df["openTime"] = pd.to_datetime(df["openTime"], unit="ms")
                df["closeTime"] = pd.to_datetime(df["closeTime"], unit="ms")
                df[["symbol", "firstId", "lastId"]] = df[
                    ["symbol", "firstId", "lastId"]
                ].astype(str)
                df["count"] = df["count"].astype(int)
                logger.info(f"Dados 24h obtidos para {len(symbols)} símbolos")
                return df
            else:
                logger.error("Falha ao obter dados 24h para os tickers USDT")
                return pd.DataFrame()
        else:
            logger.error("Falha ao obter lista de tickers USDT")
            return pd.DataFrame()

    def get_orderbook_tickers(self, symbol: str) -> pd.DataFrame:
        """
        Obtém informações de order book de um par.

        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')

        Returns:
            DataFrame com dados de order book ou DataFrame vazio se falhar
        """
        data = self.client.get_orderbook_tickers(symbol=symbol)

        if data:
            if isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                df = pd.DataFrame(data)

            df["symbol"] = df["symbol"].astype(str)
            cols = ["bidPrice", "bidQty", "askPrice", "askQty"]
            # CORREÇÃO GLOBAL: Substituído astype por apply(pd.to_numeric) + dropna seguro
            df[cols] = df[cols].apply(pd.to_numeric, errors="coerce")
            df[cols] = df[cols].round(8)
            df = df.dropna(subset=cols)

            logger.info(f"Order book obtido para {symbol}")
            return df
        else:
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
        data = self.client.get_klines(symbol=symbol, interval=interval)
        if data:
            columns = [
                "Open_Time",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
                "Close_Time",
                "Quote_Asset_Volume",
                "Number_of_Trades",
                "Taker_Buy_Base_Asset_Volume",
                "Taker_Buy_Quote_Asset_Volume",
                "Ignore",
            ]
            df = pd.DataFrame(data=data, columns=columns)
            df = df.drop(columns=["Ignore"])
            df["Open_Time"] = pd.to_datetime(df["Open_Time"], unit="ms")
            df["Close_Time"] = pd.to_datetime(df["Close_Time"], unit="ms")
            df["Number_of_Trades"] = df["Number_of_Trades"].astype(int)

            numeric_cols = [
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
                "Quote_Asset_Volume",
                "Taker_Buy_Base_Asset_Volume",
                "Taker_Buy_Quote_Asset_Volume",
            ]
            # CORREÇÃO GLOBAL: Separação do dropna para evitar desalinhamento de linhas
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
            df[numeric_cols] = df[numeric_cols].round(8)
            df = df.dropna(subset=numeric_cols)

            logger.info(f"Obtidas {len(df)} k-lines para {symbol} ({interval})")
            return df
        else:
            logger.error(f"Falha ao obter k-lines para {symbol}")
            return pd.DataFrame()

    def get_historical_klines(
        self,
        symbol: str,
        interval: str,
        start_str: str,
        end_str: Optional[str] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
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
        data = self.client.get_historical_klines(
            symbol=symbol,
            interval=interval,
            start_str=start_str,
            end_str=end_str,
            limit=limit,
        )
        if data:
            columns = [
                "Open_Time",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
                "Close_Time",
                "Quote_Asset_Volume",
                "Number_of_Trades",
                "Taker_Buy_Base_Asset_Volume",
                "Taker_Buy_Quote_Asset_Volume",
                "Ignore",
            ]
            df = pd.DataFrame(data=data, columns=columns)
            df = df.drop(columns=["Ignore"])
            df["Open_Time"] = pd.to_datetime(df["Open_Time"], unit="ms").dt.strftime(
                "%d/%m/%Y %H:%M:%S"
            )
            df["Close_Time"] = pd.to_datetime(df["Close_Time"], unit="ms").dt.strftime(
                "%d/%m/%Y %H:%M:%S"
            )
            df["Number_of_Trades"] = df["Number_of_Trades"].astype(int)

            numeric_cols = [
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
                "Quote_Asset_Volume",
                "Taker_Buy_Base_Asset_Volume",
                "Taker_Buy_Quote_Asset_Volume",
            ]
            # CORREÇÃO GLOBAL: Substituído astype por apply(pd.to_numeric) e dropna seguro
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
            df[numeric_cols] = df[numeric_cols].round(8)
            df = df.dropna(subset=numeric_cols)

            logger.info(f"Obtidas {len(df)} k-lines históricas para {symbol}")
            return df
        else:
            logger.error(f"Falha ao obter k-lines históricas para {symbol}")
            return pd.DataFrame()

    def get_historical_klines_generator(
        self, symbol: str, interval: str, timestamp: str
    ) -> pd.DataFrame:
        """
        Obtém K-lines históricas usando generator (eficiente para grandes volumes).

        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
            interval: Intervalo (ex: '1h', '1d')
            timestamp: Data inicial (ex: '100 days ago UTC')

        Returns:
            DataFrame com k-lines geradas ou DataFrame vazio se falhar
        """
        data = list(
            self.client.get_historical_klines_generator(
                symbol=symbol, interval=interval, start_str=timestamp
            )
        )
        if data:
            columns = [
                "Open_Time",
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
                "Close_Time",
                "Quote_Asset_Volume",
                "Number_of_Trades",
                "Taker_Buy_Base_Asset_Volume",
                "Taker_Buy_Quote_Asset_Volume",
                "Ignore",
            ]
            df = pd.DataFrame(data=data, columns=columns)
            df = df.drop(columns=["Ignore"])
            df["Open_Time"] = pd.to_datetime(df["Open_Time"], unit="ms").dt.strftime(
                "%d/%m/%Y %H:%M:%S"
            )
            df["Close_Time"] = pd.to_datetime(df["Close_Time"], unit="ms").dt.strftime(
                "%d/%m/%Y %H:%M:%S"
            )
            df["Number_of_Trades"] = df["Number_of_Trades"].astype(int)

            numeric_cols = [
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
                "Quote_Asset_Volume",
                "Taker_Buy_Base_Asset_Volume",
                "Taker_Buy_Quote_Asset_Volume",
            ]
            # CORREÇÃO GLOBAL: Substituído astype por apply(pd.to_numeric) e dropna seguro
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
            df[numeric_cols] = df[numeric_cols].round(8)
            df = df.dropna(subset=numeric_cols)

            logger.info(
                f"Geradas {len(df)} k-lines históricas para {symbol} via generator"
            )
            return df
        else:
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
        data = self.client.get_avg_price(symbol=symbol)
        if data:
            df = pd.DataFrame([data])
            df["mins"] = df["mins"].astype(str)

            # CORREÇÃO GLOBAL: Uso correto do pd.to_numeric
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
            df["price"] = df["price"].round(2)
            df = df.dropna(subset=["price"])

            df["closeTime"] = pd.to_datetime(df["closeTime"], unit="ms").dt.strftime(
                "%d/%m/%Y %H:%M:%S"
            )
            logger.info(f"Preço médio obtido para {symbol}")
            return df
        else:
            logger.error(f"Falha ao obter preço médio para {symbol}")
            return pd.DataFrame()

    def get_recent_trades(
        self, symbol: str, limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Obtém trades recentes de um par.

        Args:
            symbol: Par de moedas (ex: 'BTCUSDT')
            limit: Número máximo de trades a retornar

        Returns:
            DataFrame com trades recentes ou DataFrame vazio se falhar
        """
        data = self.client.get_recent_trades(symbol=symbol, limit=limit)
        if data:
            df = pd.DataFrame(data)
            df["id"] = df["id"].astype(int)

            # CORREÇÃO GLOBAL: Substituído astype por casting correto e dropna combinado
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
            df["price"] = df["price"].round(2)

            df[["qty", "quoteQty"]] = df[["qty", "quoteQty"]].apply(
                pd.to_numeric, errors="coerce"
            )
            df[["qty", "quoteQty"]] = df[["qty", "quoteQty"]].round(8)
            df = df.dropna(subset=["price", "qty", "quoteQty"])

            df["time"] = pd.to_datetime(df["time"], unit="ms").dt.strftime(
                "%d/%m/%Y %H:%M:%S"
            )
            df[["isBuyerMaker", "isBestMatch"]] = df[
                ["isBuyerMaker", "isBestMatch"]
            ].astype(bool)

            logger.info(f"Obtidos {len(df)} trades recentes para {symbol}")
            return df
        else:
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
        data = self.client.get_historical_trades(symbol=symbol)
        if data:
            df = pd.DataFrame(data)
            df["id"] = df["id"].astype(int)
            df = (
                df.drop_duplicates(subset=["id"]).reset_index(drop=True).set_index("id")
            )

            # CORREÇÃO GLOBAL: Substituído astype por casting correto e dropna combinado
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
            df["price"] = df["price"].round(2)

            df[["qty", "quoteQty"]] = df[["qty", "quoteQty"]].apply(
                pd.to_numeric, errors="coerce"
            )
            df[["qty", "quoteQty"]] = df[["qty", "quoteQty"]].round(8)
            df = df.dropna(subset=["price", "qty", "quoteQty"])

            df["time"] = pd.to_datetime(df["time"], unit="ms").dt.strftime(
                "%d/%m/%Y %H:%M:%S"
            )
            df[["isBuyerMaker", "isBestMatch"]] = df[
                ["isBuyerMaker", "isBestMatch"]
            ].astype(bool)

            logger.info(f"Obtidos {len(df)} trades históricos para {symbol}")
            return df
        else:
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
        data = self.client.get_aggregate_trades(symbol=symbol)
        if data:
            df = pd.DataFrame(data)
            df = df.rename(
                columns={
                    "a": "Aggregate_Trade_Id",
                    "p": "price",
                    "q": "Quantity",
                    "f": "First_Trade_Id",
                    "l": "Last_Trade_Id",
                    "T": "TimeStamp",
                    "m": "isBuyerMaker",
                    "M": "isBestMatch",
                }
            )
            df["Aggregate_Trade_Id"] = df["Aggregate_Trade_Id"].astype(int)
            df = (
                df.drop_duplicates(subset=["Aggregate_Trade_Id"])
                .reset_index(drop=True)
                .set_index("Aggregate_Trade_Id")
            )

            # CORREÇÃO GLOBAL: Substituído astype por casting correto e dropna combinado
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
            df["price"] = df["price"].round(2)

            df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
            df["Quantity"] = df["Quantity"].round(8)
            df = df.dropna(subset=["price", "Quantity"])

            df[["First_Trade_Id", "Last_Trade_Id"]] = df[
                ["First_Trade_Id", "Last_Trade_Id"]
            ].astype(int)
            df["TimeStamp"] = pd.to_datetime(df["TimeStamp"], unit="ms").dt.strftime(
                "%d/%m/%Y %H:%M:%S"
            )
            df[["isBuyerMaker", "isBestMatch"]] = df[
                ["isBuyerMaker", "isBestMatch"]
            ].astype(bool)

            logger.info(f"Obtidos {len(df)} trades agregados para {symbol}")
            return df
        else:
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
        data = self.client.get_depth(symbol=symbol)
        if data:
            update_id = data.get("lastUpdateId")
            df_bids = pd.DataFrame(data["bids"], columns=["price", "quantity"])
            df_bids["side"] = "bid"
            df_asks = pd.DataFrame(data["asks"], columns=["price", "quantity"])
            df_asks["side"] = "ask"
            df_full = pd.concat([df_bids, df_asks], ignore_index=True)
            df_full["lastUpdateId"] = update_id

            # CORREÇÃO: Casting seguro de tipos numéricos usando apply(pd.to_numeric)
            df_full[["price", "quantity"]] = df_full[["price", "quantity"]].apply(
                pd.to_numeric, errors="coerce"
            )
            logger.info(f"Profundidade de mercado obtida para {symbol}")
            return df_full
        else:
            logger.error(f"Falha ao obter profundidade de mercado para {symbol}")
            return pd.DataFrame()
