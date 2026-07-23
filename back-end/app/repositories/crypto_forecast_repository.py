import pandas as pd
from app.clients.supabase_client import get_supabase_client
from app.services.binance_market_data_service import BinanceMarketService


class CryptoForecastRepository:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.binance_service = BinanceMarketService()

    def save_ticker_24hr(self):
        df = self.binance_service.get_ticker_24hr()
        if df.empty:
            return
        else:
            df_prep = df.copy()
            df_prep = df_prep.rename(
                columns={
                    "symbol": "symbol",
                    "priceChange": "price_change",
                    "priceChangePercent": "price_change_percent",
                    "weightedAvgPrice": "weighted_avg_price",
                    "prevClosePrice": "prev_close_price",
                    "lastPrice": "last_price",
                    "lastQty": "last_qty",
                    "bidPrice": "bid_price",
                    "bidQty": "bid_qty",
                    "askPrice": "ask_price",
                    "askQty": "ask_qty",
                    "openPrice": "open_price",
                    "highPrice": "high_price",
                    "lowPrice": "low_price",
                    "volume": "volume",
                    "quoteVolume": "quote_volume",
                    "openTime": "open_time",
                    "closeTime": "close_time",
                    "firstId": "first_id",
                    "lastId": "last_id",
                    "count": "count",
                }
            )

            if "open_time" in df_prep.columns:
                df_prep["open_time"] = df_prep["open_time"].dt.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            if "close_time" in df_prep.columns:
                df_prep["close_time"] = df_prep["close_time"].dt.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            dados_para_salvar = df_prep.to_dict(orient="records")
            try:
                response = (
                    self.supabase.table("ticker_24hr_history")
                    .upsert(dados_para_salvar, on_conflict="symbol,open_time")
                    .execute()
                )
                print(
                    f"Sucesso! {len(dados_para_salvar)} registros de tickers salvos/atualizados no Supabase."
                )
                return response

            except Exception as e:
                print(f"Erro ao salvar os tickers de 24h no Supabase: {e}")
                return None

    def save_orderbook_tickers(self):
        df = self.binance_service.get_orderbook_tickers()
        if df.empty:
            return
        else:
            df_prep = df.copy()
            df_prep = df_prep.rename(
                columns={
                    "symbol": "symbol",
                    "bidPrice": "bid_price",
                    "bidQty": "bid_qty",
                    "askPrice": "ask_price",
                    "askQty": "ask_qty",
                }
            )
            df_prep["fetched_at"] = pd.Timestamp.now(tz="UTC").strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            dados_para_salvar = df_prep.to_dict(orient="records")
            try:
                response = (
                    self.supabase.table("orderbook_tickers")
                    .upsert(dados_para_salvar, on_conflict="symbol,fetched_at")
                    .execute()
                )
                print(
                    f"Sucesso! {len(dados_para_salvar)} registros de orderbook salvos/atualizados no Supabase."
                )
                return response
            except Exception as e:
                print(f"Erro ao salvar os orderbook no Supabase: {e}")
                return None
