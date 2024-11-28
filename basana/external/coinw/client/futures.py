from basana.external.coinw.client.base import CoinWAPI


class CoinWFutures(CoinWAPI):
    def check_open_orders(self, positionType: str, instrument: str):
        endpoint = "/v1/perpum/orders/open"
        params = {"positionType": positionType, "instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def check_pending_order_quantity(self, instrument: str):
        endpoint = "/v1/perpum/orders/pending"
        params = {"instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def check_personal_transaction_history(
        self, instrument: str, startTime: int, endTime: int
    ):
        endpoint = "/v1/perpum/transactions/personal"
        params = {"instrument": instrument, "startTime": startTime, "endTime": endTime}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def check_product_information(self, instrument: str):
        endpoint = "/v1/perpum/products/info"
        params = {"instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def check_current_funding_rate(self, instrument: str):
        endpoint = "/v1/perpum/funding/rate"
        params = {"instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def check_server_time(self):
        endpoint = "/v1/perpum/time"
        return self._make_request("GET", endpoint, is_futures=True)

    def check_derivative_position_tiers(self, instrument: str):
        endpoint = "/v1/perpum/position/tiers"
        params = {"instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def switch_measure_unit(self, instrument: str, unit: str):
        endpoint = "/v1/perpum/measure/unit"
        params = {"instrument": instrument, "unit": unit}
        return self._make_request("POST", endpoint, params, is_futures=True)

    def check_position_information(self, instrument: str):
        endpoint = "/v1/perpum/position/info"
        params = {"instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def check_position_history(self, instrument: str, startTime: int, endTime: int):
        endpoint = "/v1/perpum/position/history"
        params = {"instrument": instrument, "startTime": startTime, "endTime": endTime}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def set_position_mode(self, instrument: str, mode: int):
        endpoint = "/v1/perpum/position/mode"
        params = {"instrument": instrument, "mode": mode}
        return self._make_request("POST", endpoint, params, is_futures=True)

    def check_position_mode(self, instrument: str):
        endpoint = "/v1/perpum/position/mode"
        params = {"instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def check_max_order_contracts(self, instrument: str):
        endpoint = "/v1/perpum/order/max"
        params = {"instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def check_max_available_contracts(self, instrument: str):
        endpoint = "/v1/perpum/contracts/max"
        params = {"instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def check_max_transfer(self, instrument: str):
        endpoint = "/v1/perpum/transfer/max"
        params = {"instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def adjust_margin_amount(self, instrument: str, amount: float):
        endpoint = "/v1/perpum/margin/adjust"
        params = {"instrument": instrument, "amount": amount}
        return self._make_request("POST", endpoint, params, is_futures=True)

    def check_leverage_multiplier(self, instrument: str):
        endpoint = "/v1/perpum/leverage/multiplier"
        params = {"instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def current_fee_rate(self, instrument: str):
        endpoint = "/v1/perpum/fee/rate"
        params = {"instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def place_order(
        self, instrument: str, side: str, type: str, quantity: float, price: float
    ):
        endpoint = "/v1/perpum/order/place"
        params = {
            "instrument": instrument,
            "side": side,
            "type": type,
            "quantity": quantity,
            "price": price,
        }
        return self._make_request("POST", endpoint, params, is_futures=True)

    def place_multiple_orders(self, orders: list):
        endpoint = "/v1/perpum/orders/place"
        params = {"orders": orders}
        return self._make_request("POST", endpoint, params, is_futures=True)

    def cancel_order(self, orderId: str):
        endpoint = "/v1/perpum/order/cancel"
        params = {"orderId": orderId}
        return self._make_request("POST", endpoint, params, is_futures=True)

    def bulk_cancel_order(self, instrument: str):
        endpoint = "/v1/perpum/orders/cancel"
        params = {"instrument": instrument}
        return self._make_request("POST", endpoint, params, is_futures=True)

    def modify_order(self, orderId: str, quantity: float, price: float):
        endpoint = "/v1/perpum/order/modify"
        params = {"orderId": orderId, "quantity": quantity, "price": price}
        return self._make_request("POST", endpoint, params, is_futures=True)

    def close_position(self, instrument: str, side: str):
        endpoint = "/v1/perpum/position/close"
        params = {"instrument": instrument, "side": side}
        return self._make_request("POST", endpoint, params, is_futures=True)

    def market_close_all_positions(self, instrument: str):
        endpoint = "/v1/perpum/positions/close/all"
        params = {"instrument": instrument}
        return self._make_request("POST", endpoint, params, is_futures=True)

    def reverse(self, instrument: str, side: str):
        endpoint = "/v1/perpum/position/reverse"
        params = {"instrument": instrument, "side": side}
        return self._make_request("POST", endpoint, params, is_futures=True)

    def get_order_information(self, orderId: str):
        endpoint = "/v1/perpum/order/info"
        params = {"orderId": orderId}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def check_order_history_last_7d(self, instrument: str):
        endpoint = "/v1/perpum/orders/history/7d"
        params = {"instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def check_order_history_last_3m(self, instrument: str):
        endpoint = "/v1/perpum/orders/history/3m"
        params = {"instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def check_transaction_details_last_3d(self, instrument: str):
        endpoint = "/v1/perpum/transactions/details/3d"
        params = {"instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def check_transaction_details_last_3m(self, instrument: str):
        endpoint = "/v1/perpum/transactions/details/3m"
        params = {"instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def check_position_margin_ratio(self, instrument: str):
        endpoint = "/v1/perpum/position/margin/ratio"
        params = {"instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def check_take_profit_stop_loss_info(self, instrument: str):
        endpoint = "/v1/perpum/position/takeprofit/stoploss/info"
        params = {"instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def set_take_profit_stop_loss(
        self, instrument: str, takeProfit: float, stopLoss: float
    ):
        endpoint = "/v1/perpum/position/takeprofit/stoploss/set"
        params = {
            "instrument": instrument,
            "takeProfit": takeProfit,
            "stopLoss": stopLoss,
        }
        return self._make_request("POST", endpoint, params, is_futures=True)

    def check_trailing_take_profit_stop_loss_info(self, instrument: str):
        endpoint = "/v1/perpum/position/trailing/takeprofit/stoploss/info"
        params = {"instrument": instrument}
        return self._make_request("GET", endpoint, params, is_futures=True)

    def set_trailing_take_profit_stop_loss(
        self, instrument: str, trailingTakeProfit: float, trailingStopLoss: float
    ):
        endpoint = "/v1/perpum/position/trailing/takeprofit/stoploss/set"
        params = {
            "instrument": instrument,
            "trailingTakeProfit": trailingTakeProfit,
            "trailingStopLoss": trailingStopLoss,
        }
        return self._make_request("POST", endpoint, params, is_futures=True)

    def check_futures_mega_coupon_info(self):
        endpoint = "/v1/perpum/mega/coupon/info"
        return self._make_request("GET", endpoint, is_futures=True)

    def set_futures_mega_coupon_status(self, status: int):
        endpoint = "/v1/perpum/mega/coupon/status"
        params = {"status": status}
        return self._make_request("POST", endpoint, params, is_futures=True)

    def get_assets(self):
        endpoint = "/v1/perpum/assets"
        return self._make_request("GET", endpoint, is_futures=True)
