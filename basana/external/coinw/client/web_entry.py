from dataclasses import dataclass
from typing import ClassVar, Dict, Set
from enum import Enum


class Button(Enum):
    MARKETS = '//*[@id="app"]/div[1]/header/div/ul/li[2]'
    FUTURES = '//*[@id="app"]/div[1]/header/div/ul/li[3]'


class MarketType(Enum):
    SPOT = 'spot'
    FUTURES = 'futures'


class URLManager:
    BASE_URL: ClassVar[str] = "https://www.coinw.com"
    valid_tokens: Set[str] = set([
        'btc', 'eth', 'sol', 'bnb', 'arb', 'trx', 'ton'
        ])

    @classmethod
    def get_url(cls, symbol: str, market_type: MarketType) -> str:
        """
        Returns the URL for the given crypto symbol and market type.

        :param symbol: The crypto symbol, e.g., 'btc', 'eth', 'sol'.
        :param market_type: The market type, e.g., MarketType.SPOT or MarketType.FUTURES.
        :return: The constructed URL as a string.
        :raises ValueError: If the symbol is empty or market_type is invalid.
        """
        if not symbol:
            raise ValueError("Symbol cannot be empty.")

        symbol = symbol.lower()
        if symbol not in cls.valid_tokens:
            raise RuntimeError(f'The token [{symbol}] is not supported !')

        if market_type == MarketType.SPOT:
            # For spot market, the URL is /spot/{symbol}usdt
            url = f"{cls.BASE_URL}/spot/{symbol}usdt"
        elif market_type == MarketType.FUTURES:
            # For futures market, the URL is /futures/usdt/{symbol}usdt
            url = f"{cls.BASE_URL}/futures/usdt/{symbol}usdt"
        else:
            # If an invalid market type is provided
            raise ValueError(f"Unknown market type: {market_type}")

        return url


if __name__ == "__main__":
    # Examples of getting URLs
    btc_spot_url = URLManager.get_url("btc", MarketType.SPOT)
    print(f"BTC Spot URL: {btc_spot_url}")
    # Output: BTC Spot URL: https://www.coinw.com/spot/btcusdt

    eth_futures_url = URLManager.get_url("eth", MarketType.FUTURES)
    print(f"ETH Futures URL: {eth_futures_url}")
    # Output: ETH Futures URL: https://www.coinw.com/futures/usdt/ethusdt

    sol_spot_url = URLManager.get_url("sol", MarketType.SPOT)
    print(f"SOL Spot URL: {sol_spot_url}")
    # Output: SOL Spot URL: https://www.coinw.com/spot/solusdt

    try:
        jup_spot_url = URLManager.get_url("jup", MarketType.SPOT)
    except RuntimeError as e:
        print(f'Error: {e}')
        # Output: Error: The token [jup] is not supported !

    # Handle invalid symbol
    try:
        invalid_symbol_url = URLManager.get_url("", MarketType.SPOT)
    except ValueError as e:
        print(f"Error: {e}")
        # Output: Error: Symbol cannot be empty.

    # Handle invalid market type
    try:
        invalid_market_url = URLManager.get_url("btc", "invalid_market_type")
    except ValueError as e:
        print(f"Error: {e}")
        # Output: Error: Unknown market type: invalid_market_type
