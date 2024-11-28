from basana.external.coinw.client.base import CoinWAPI


class CoinWBalance(CoinWAPI):
    def get_available_balance(self):
        endpoint = "/api/v1/private?command=returnBalances"

        return self._make_request("POST", endpoint)

    def get_all_balances(self):
        endpoint = "/api/v1/private?command=returnCompleteBalances"
        return self._make_request("POST", endpoint)

    def get_deposit_withdrawal_records(self, symbol: str, depositNumber: str = None):
        endpoint = "/api/v1/private?command=returnDepositsWithdrawals"
        params = {"symbol": symbol}
        if depositNumber:
            params["depositNumber"] = depositNumber
        return self._make_request("POST", endpoint, params)

    def get_deposit_address(self, symbolId: str, chain: str):
        endpoint = "/api/v1/private?command=getDepositAddress"
        params = {"symbolId": symbolId, "chain": chain}
        return self._make_request("POST", endpoint, params)

    def withdraw(
        self,
        amount: str,
        currency: str,
        address: str,
        chain: str = None,
        memo: str = None,
    ):
        endpoint = "/api/v1/private?command=doWithdraw"
        params = {"amount": amount, "currency": currency, "address": address}
        if chain:
            params["chain"] = chain
        if memo:
            params["memo"] = memo
        return self._make_request("POST", endpoint, params)

    def cancel_withdrawal(self, id: str):
        endpoint = "/api/v1/private?command=cancelWithdraw"
        params = {"id": id}
        return self._make_request("POST", endpoint, params)


class CoinWSpot(CoinWAPI):
    def get_open_orders(self, currency_pair: str):
        endpoint = "/api/v1/private?command=returnOpenOrders"
        params = {"currencyPair": currency_pair}

        return self._make_request("POST", endpoint, params)

    def get_order_details(self, order_number: str):
        endpoint = "/api/v1/private?command=returnOrderTrades"
        params = {"orderNumber": order_number}

        return self._make_request("POST", endpoint, params)

    def get_single_order(self, order_id: str):
        endpoint = "/api/v1/private?command=getOrder"
        params = {"id": order_id}

        return self._make_request("POST", endpoint, params)

    def get_order_status(self, order_number: str):
        endpoint = "/api/v1/private?command=returnOrderStatus"
        params = {"orderNumber": order_number}

        return self._make_request("POST", endpoint, params)

    def get_trade_history(self, currency_pair: str, start_at: str, end_at: str):
        endpoint = "/api/v1/private?command=returnUTradeHistory"
        params = {"currencyPair": currency_pair, "startAt": start_at, "endAt": end_at}

        return self._make_request("POST", endpoint, params)

    def place_order(self, symbol, order_type, amount, rate, out_trade_no):
        endpoint = "/api/v1/private?command=doTrade"
        if order_type.upper() == "BUY":
            order_type_ = "0"
        elif order_type.upper() == "SELL":
            order_type_ = "1"
        else:
            raise ValueError("Invalid order type. Please specify 'BUY' or 'SELL'.")
        params = {
            "symbol": symbol,
            "type": order_type_,
            "amount": amount,
            "rate": rate,
            "out_trade_no": out_trade_no,
        }

        return self._make_request("POST", endpoint, params)

    def place_market_order(
        self, symbol, order_type, funds=None, amount=None, is_market=True
    ):
        endpoint = "/api/v1/private?command=doTrade"
        params = {"symbol": symbol, "type": order_type, "isMarket": is_market}
        if funds:
            params["funds"] = funds
        if amount:
            params["amount"] = amount

        return self._make_request("POST", endpoint, params)

    def cancel_order(self, order_number: str):
        endpoint = "/api/v1/private?command=cancelOrder"
        params = {"orderNumber": order_number}

        return self._make_request("POST", endpoint, params)

    def cancel_all_orders(self, symbol: str):
        endpoint = "/api/v1/private?command=cancelAll"
        params = {"symbol": symbol}

        return self._make_request("POST", endpoint, params)


class CoinWPublic(CoinWAPI):
    def get_market_ticker(self):
        endpoint = "/api/v1/public?command=returnTicker"

        return self._make_request("GET", endpoint)

    def get_timestamp(self):
        endpoint = "/api/v1/public?command=timestamp"

        return self._make_request("GET", endpoint)

    def get_symbol_info(self):
        endpoint = "/api/v1/public?command=returnSymbol"

        return self._make_request("GET", endpoint)

    def get_kline_data(self, currency_pair: str, period: int):
        endpoint = "/api/v1/public?command=returnChartData"
        params = {"currencyPair": currency_pair, "period": period}

        return self._make_request("GET", endpoint, params)

    def get_depth(self, currency_pair: str):
        endpoint = "/api/v1/public?command=returnOrderBook"
        params = {"currencyPair": currency_pair}

        return self._make_request("GET", endpoint, params)

    def get_hot_coins_trading_volume(self):
        endpoint = "/api/v1/public?command=return24hVolume"

        return self._make_request("GET", endpoint)
