# Basana
#
# Copyright 2022-2023 Gabriel Martin Becedillas Ruiz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from decimal import Decimal
from typing import cast, Any, Awaitable, Callable, Dict, Generator, Generic, Iterable, List, Optional, Protocol, \
    Sequence, Tuple, TypeVar
import copy
import dataclasses
import decimal
import logging
import uuid

from basana.backtesting import account_balances, config, errors, fees, lending, liquidity, orders, requests
from basana.backtesting import helpers as bt_helpers
from basana.core import bar, dispatcher, enums, event, logs
from basana.core import helpers as core_helpers
from basana.core.pair import Pair, PairInfo


logger = logging.getLogger(__name__)

BarEventHandler = Callable[[bar.BarEvent], Awaitable[Any]]
Error = errors.Error
LiquidityStrategyFactory = Callable[[], liquidity.LiquidityStrategy]
LoanInfo = lending.LoanInfo
OrderInfo = orders.OrderInfo
OrderOperation = enums.OrderOperation


def assert_has_value(balance_updates: Dict[str, Decimal], symbol: str, sign: Decimal):
    value = balance_updates.get(symbol)
    assert value is not None, f"{symbol} is missing"
    assert value != Decimal(0), f"{symbol} is zero"
    assert bt_helpers.get_sign(value) == sign, f"{symbol} sign is wrong. It should be {sign}"


class ExchangeObjectProto(Protocol):
    @property
    def id(self) -> str:
        ...

    @property
    def is_open(self) -> bool:
        ...


TExchangeObject = TypeVar('TExchangeObject', bound=ExchangeObjectProto)


class ExchangeObjectContainer(Generic[TExchangeObject]):
    def __init__(self):
        self._items: Dict[str, TExchangeObject] = {}  # Items by id.
        self._open_items: List[TExchangeObject] = []
        self._reindex_every = 50
        self._reindex_counter = 0

    def add(self, item: TExchangeObject):
        assert item.id not in self._items
        self._items[item.id] = item
        if item.is_open:
            self._open_items.append(item)

    def get(self, id: str) -> Optional[TExchangeObject]:
        return self._items.get(id)

    def get_open(self) -> Generator[TExchangeObject, None, None]:
        self._reindex_counter += 1
        new_open_items: Optional[List[TExchangeObject]] = None
        if self._reindex_counter % self._reindex_every == 0:
            new_open_items = []

        for item in self._open_items:
            if item.is_open:
                yield item
                if new_open_items is not None and item.is_open:
                    new_open_items.append(item)

        if new_open_items is not None:
            self._open_items = new_open_items

    def get_all(self) -> Iterable[TExchangeObject]:
        return self._items.values()


@dataclasses.dataclass
class Balance:
    #: The available balance (the total balance - hold).
    available: Decimal
    #: The total balance ((available + hold) - (borrowed + interest)).
    total: Decimal = dataclasses.field(init=False)
    #: The balance on hold (reserved for open sell orders).
    hold: Decimal
    #: The balance borrowed.
    borrowed: Decimal
    #: The interest.
    interest: Decimal

    def __post_init__(self):
        self.total = (self.available + self.hold) - (self.borrowed + self.interest)


@dataclasses.dataclass
class CreatedOrder:
    #: The order id.
    id: str


@dataclasses.dataclass
class CanceledOrder:
    #: The order id.
    id: str


@dataclasses.dataclass
class OpenOrder:
    #: The order id.
    id: str
    #: The operation.
    operation: OrderOperation
    #: The original amount.
    amount: Decimal
    #: The amount filled.
    amount_filled: Decimal


class Exchange:
    """This class implements a backtesting exchange.

    This backtesting exchange has support for Market, Limit, Stop and Stop Limit orders and it will simulate order
    execution based on summarized trading activity (:class:`basana.BarEvent`).

    :param dispatcher: The event dispatcher.
    :param initial_balances: The initial balance for each currency/symbol/etc.
    :param liquidity_strategy_factory: A callable that returns a new liquidity strategy.
    :param fee_strategy: The fee stragegy to use.
    :param default_pair_info: The default pair information if a specific one was not set using
        :meth:`Exchange.set_pair_info`.
    :param bid_ask_spread: The spread to use for :meth:`Exchange.get_bid_ask`.
    """
    def __init__(
            self,
            dispatcher: dispatcher.EventDispatcher,
            initial_balances: Dict[str, Decimal],
            liquidity_strategy_factory: LiquidityStrategyFactory = liquidity.VolumeShareImpact,
            fee_strategy: fees.FeeStrategy = fees.NoFee(),
            default_pair_info: Optional[PairInfo] = PairInfo(base_precision=0, quote_precision=2),
            bid_ask_spread: Decimal = Decimal("0.5"),
            lending_strategy: lending.LendingStrategy = lending.NoLoans()
    ):
        self._dispatcher = dispatcher
        self._balances = account_balances.AccountBalances(initial_balances)
        self._liquidity_strategy_factory = liquidity_strategy_factory
        self._liquidity_strategies: Dict[Pair, liquidity.LiquidityStrategy] = {}
        self._fee_strategy = fee_strategy
        self._lending_strategy = lending_strategy
        self._orders = ExchangeObjectContainer[orders.Order]()
        self._bar_event_source: Dict[Pair, event.FifoQueueEventSource] = {}
        self._last_bars: Dict[Pair, bar.Bar] = {}
        self._bid_ask_spread = bid_ask_spread
        self._loans = ExchangeObjectContainer[lending.Loan]()
        self._config = config.Config(None, default_pair_info)

    async def get_balance(self, symbol: str) -> Balance:
        """Returns the balance for a specific currency/symbol/etc..

        :param symbol: The currency/symbol/etc..
        """
        return self._get_balance(symbol)

    async def get_balances(self) -> Dict[str, Balance]:
        """Returns all balances."""
        ret = {}
        for symbol in self._balances.get_symbols():
            ret[symbol] = self._get_balance(symbol)
        return ret

    async def get_bid_ask(self, pair: Pair) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """Returns the current bid and ask price, if available.

        This is calculated using the closing price of the last bar, and the bid/ask spread specified during
        initialization.

        :param pair: The trading pair.
        """
        bid = ask = None
        last_price = await self._get_last_price(pair)
        if last_price:
            pair_info = await self.get_pair_info(pair)
            half_spread = core_helpers.truncate_decimal(
                (last_price * self._bid_ask_spread / Decimal("100")) / Decimal(2),
                pair_info.quote_precision
            )
            bid = last_price - half_spread
            ask = last_price + half_spread
        return bid, ask

    async def create_order(self, order_request: requests.ExchangeOrder) -> CreatedOrder:
        # Validate request parameters.
        pair_info = await self.get_pair_info(order_request.pair)
        order_request.validate(pair_info)

        # Check balances before accepting the order.
        required_balances = await self._estimate_required_balances(order_request)
        self._check_balance_requirements(required_balances, raise_if_short=True)

        # Create and accept the order.
        order = order_request.create_order(uuid.uuid4().hex)
        self._orders.add(order)
        logger.debug(logs.StructuredMessage("Request accepted", order_id=order.id))

        # Update/hold balances.
        self._balances.order_accepted(order, required_balances)

        return CreatedOrder(id=order.id)

    async def create_market_order(self, operation: OrderOperation, pair: Pair, amount: Decimal) -> CreatedOrder:
        """Creates a market order.

        A market order is an order to immediately buy or sell at the best available price.
        Generally, this type of order will be executed on the next bar using the open price as a reference, and
        according to the rules defined by the liquidity strategy.
        If the order is not filled on the next bar, due to lack of liquidity or funds, the order will be canceled.

        If the order can't be created an :class:`Error` will be raised.

        :param operation: The order operation.
        :param pair: The pair to trade.
        :param amount: The base amount to buy/sell.
        """
        return await self.create_order(requests.MarketOrder(operation, pair, amount))

    async def create_limit_order(
            self, operation: OrderOperation, pair: Pair, amount: Decimal, limit_price: Decimal
    ) -> CreatedOrder:
        """Creates a limit order.

        A limit order is an order to buy or sell at a specific price or better.
        A buy limit order can only be executed at the limit price or lower, and a sell limit order can only be executed
        at the limit price or higher.

        If the order can't be created an :class:`Error` will be raised.

        :param operation: The order operation.
        :param pair: The pair to trade.
        :param amount: The base amount to buy/sell.
        :param limit_price: The limit price.
        """
        return await self.create_order(requests.LimitOrder(operation, pair, amount, limit_price))

    async def create_stop_order(
            self, operation: OrderOperation, pair: Pair, amount: Decimal, stop_price: Decimal
    ) -> CreatedOrder:
        """Creates a stop order.

        A stop order, also referred to as a stop-loss order, is an order to buy or sell once the price reaches a
        specified price, known as the stop price.
        When the stop price is reached, a stop order becomes a market order.

        * A buy stop order is entered at a stop price above the current market price. Investors generally use a buy
          stop order to limit a loss or to protect a profit on an instrument that they have sold short.
        * A sell stop order is entered at a stop price below the current market price. Investors generally use a sell
          stop order to limit a loss or to protect a profit on an instrument that they own.

        If the order can't be created an :class:`Error` will be raised.

        :param operation: The order operation.
        :param pair: The pair to trade.
        :param amount: The base amount to buy/sell.
        :param stop_price: The stop price.
        """
        return await self.create_order(requests.StopOrder(operation, pair, amount, stop_price))

    async def create_stop_limit_order(
            self, operation: OrderOperation, pair: Pair, amount: Decimal, stop_price: Decimal, limit_price: Decimal
    ) -> CreatedOrder:
        """Creates a stop limit order.

        A stop-limit order is an order to buy or sell that combines the features of a stop order and a limit order.
        Once the stop price is reached, a stop-limit order becomes a limit order that will be executed at a specified
        price (or better).

        If the order can't be created an :class:`Error` will be raised.

        :param operation: The order operation.
        :param pair: The pair to trade.
        :param amount: The base amount to buy/sell.
        :param stop_price: The stop price.
        :param limit_price: The limit price.
        """
        return await self.create_order(requests.StopLimitOrder(operation, pair, amount, stop_price, limit_price))

    async def cancel_order(self, order_id: str) -> CanceledOrder:
        """Cancels an order.

        If the order doesn't exist, or its not open, an :class:`Error` will be raised.

        :param order_id: The order id.
        """
        order = self._orders.get(order_id)
        if order is None:
            raise Error("Order not found")
        if not order.is_open:
            raise Error("Order {} is in {} state and can't be canceled".format(order_id, order.state))
        order.cancel()
        # Update balances to release any pending hold.
        self._balances.order_updated(order, {})
        return CanceledOrder(id=order_id)

    async def get_order_info(self, order_id: str) -> OrderInfo:
        """Returns information about an order.

        If the order doesn't exist, or its not open, an :class:`Error` will be raised.

        :param order_id: The order id.
        """
        order = self._orders.get(order_id)
        if not order:
            raise Error("Order not found")
        return order.get_order_info()

    async def get_open_orders(self, pair: Optional[Pair] = None) -> List[OpenOrder]:
        """Returns open orders.

        :param pair: If set, only open orders matching this pair will be returned, otherwise all open orders will be
            returned.
        """
        return [
            OpenOrder(
                id=order.id,
                operation=order.operation,
                amount=order.amount,
                amount_filled=order.amount_filled
            )
            for order in self._orders.get_open()
            if pair is None or order.pair == pair
        ]

    def add_bar_source(self, bar_source: event.EventSource):
        """Adds an event source that produces :class:`basana.BarEvent` instances.

        These will be used to drive the backtest.

        :param bar_source: An event source that produces :class:`basana.BarEvent` instances.
        """
        self._dispatcher.subscribe(bar_source, self._on_bar_event)

    def subscribe_to_bar_events(self, pair: Pair, event_handler: BarEventHandler):
        """Registers an async callable that will be called when a new bar is available.

        :param pair: The trading pair.
        :param event_handler: An async callable that receives a basana.BarEvent.
        """
        # Get/create the event source for the given pair.
        event_source = self._bar_event_source.get(pair)
        if event_source is None:
            event_source = event.FifoQueueEventSource()
            self._bar_event_source[pair] = event_source
        self._dispatcher.subscribe(event_source, cast(dispatcher.EventHandler, event_handler))

    async def get_pair_info(self, pair: Pair) -> PairInfo:
        """Returns information about a trading pair.

        :param pair: The trading pair.
        """
        return self._get_pair_info(pair)

    def set_pair_info(self, pair: Pair, pair_info: PairInfo):
        """Set information about a trading pair.

        :param pair: The trading pair.
        :param pair_info: The pair information.
        """
        self._config.set_pair_info(pair, pair_info)

    def set_symbol_precision(self, symbol: str, precision: int):
        """Set precision for a symbol.

        This is used to round interest in loans.

        :param symbol: The symbol.
        :param precision: The precision.
        """
        self._config.set_symbol_info(symbol, config.SymbolInfo(precision=precision))

    async def create_loan(self, symbol: str, amount: Decimal) -> LoanInfo:
        if amount <= 0:
            raise Error("Invalid amount")

        # Create and save the loan.
        loan = self._lending_strategy.create_loan(symbol, amount, self._dispatcher.now())
        # Update balances.
        self._balances.accept_loan(loan)
        self._loans.add(loan)
        return loan.get_loan_info()

    async def get_open_loans(self) -> List[LoanInfo]:
        return list(map(lambda loan: loan.get_loan_info(), self._loans.get_open()))

    async def get_loan(self, loan_id: str) -> Optional[LoanInfo]:
        loan = self._loans.get(loan_id)
        return None if loan is None else loan.get_loan_info()

    async def repay_loan(self, loan_id: str):
        loan = self._loans.get(loan_id)
        if not loan:
            raise Error("Loan not found")
        if not loan.is_open:
            raise Error("Loan is not open")

        # Check balances.
        required_balances = {loan.borrowed_symbol: loan.borrowed_amount}
        self._check_balance_requirements(required_balances, log_context={"loan.id": loan_id}, raise_if_short=True)
        # Update balances.
        interest = loan.calculate_interest(self._dispatcher.now())
        for symbol, amount in interest.items():
            interest[symbol] = core_helpers.truncate_decimal(amount, self._config.get_symbol_info(symbol).precision)
        self._balances.repay_loan(loan, interest)
        # Close the loan.
        loan.close()

    def _get_pair_info(self, pair: Pair) -> PairInfo:
        return self._config.get_pair_info(pair)

    def _round_balance_updates(self, pair: Pair, balance_updates: Dict[str, Decimal]) -> Dict[str, Decimal]:
        ret = copy.copy(balance_updates)
        pair_info = self._get_pair_info(pair)

        # For the base amount we truncate instead of rounding to avoid exceeding available liquidity.
        base_amount = ret.get(pair.base_symbol)
        if base_amount:
            base_amount = core_helpers.truncate_decimal(base_amount, pair_info.base_precision)
            ret[pair.base_symbol] = base_amount

        # For the quote amount we simply round.
        quote_amount = ret.get(pair.quote_symbol)
        if quote_amount:
            quote_amount = core_helpers.round_decimal(quote_amount, pair_info.quote_precision)
            ret[pair.quote_symbol] = quote_amount

        return bt_helpers.remove_empty_amounts(ret)

    def _round_fees(self, pair: Pair, fees: Dict[str, Decimal]) -> Dict[str, Decimal]:
        ret = copy.copy(fees)
        pair_info = self._get_pair_info(pair)
        precisions = {
            pair.base_symbol: pair_info.base_precision,
            pair.quote_symbol: pair_info.quote_precision,
        }
        for symbol in ret.keys():
            amount = ret.get(symbol)
            # If there is a fee in a symbol other that base/quote we won't round it since we don't know the precision.
            if amount and (precision := precisions.get(symbol)) is not None:
                amount = core_helpers.round_decimal(amount, precision, rounding=decimal.ROUND_UP)
                ret[symbol] = amount

        return bt_helpers.remove_empty_amounts(ret)

    def _process_order(
            self, order: orders.Order, bar_event: bar.BarEvent, liquidity_strategy: liquidity.LiquidityStrategy
    ):
        def order_not_filled():
            order.not_filled()
            # Update balances to release any pending hold if the order is no longer open.
            if not order.is_open:
                self._balances.order_updated(order, {})
                logger.debug(logs.StructuredMessage("Order not filled", order_id=order.id, order_state=order.state))

        logger.debug(logs.StructuredMessage(
            "Processing order", order=order.get_debug_info(),
            bar={
                "open": bar_event.bar.open, "high": bar_event.bar.high, "low": bar_event.bar.low,
                "close": bar_event.bar.close, "volume": bar_event.bar.volume,
            }
        ))
        prev_state = order.state
        balance_updates = order.get_balance_updates(bar_event.bar, liquidity_strategy)
        assert order.state == prev_state, "The order state should not change inside get_balance_updates"

        # If there are no balance updates then there is nothing left to do.
        if not balance_updates:
            order_not_filled()
            return

        # Sanity checks. Base and quote amounts should be there.
        base_sign = bt_helpers.get_base_sign_for_operation(order.operation)
        assert_has_value(balance_updates, order.pair.base_symbol, base_sign)
        assert_has_value(balance_updates, order.pair.quote_symbol, -base_sign)

        # If base/quote amounts were removed after rounding then there is nothing left to do.
        balance_updates = self._round_balance_updates(order.pair, balance_updates)
        logger.debug(logs.StructuredMessage("Processing order", order_id=order.id, balance_updates=balance_updates))
        if order.pair.base_symbol not in balance_updates or order.pair.quote_symbol not in balance_updates:
            order_not_filled()
            return

        # Get fees, round them, and combine them with the balance updates.
        fees = self._fee_strategy.calculate_fees(order, balance_updates)
        fees = self._round_fees(order.pair, fees)
        logger.debug(logs.StructuredMessage("Processing order", order_id=order.id, fees=fees))
        final_updates = bt_helpers.add_amounts(balance_updates, fees)
        final_updates = bt_helpers.remove_empty_amounts(final_updates)

        # Check if we're short on any balance.
        required_balances = {symbol: -amount for symbol, amount in final_updates.items() if amount < 0}
        balance_ok = self._check_balance_requirements(
            required_balances, order=order, log_context={"order.id": order.id}
        )

        # Update, or fail.
        if balance_ok:
            # Update the liquidity strategy.
            liquidity_strategy.take_liquidity(abs(balance_updates[bar_event.bar.pair.base_symbol]))
            # Update the order.
            order.add_fill(bar_event.when, balance_updates, fees)
            # Update balances.
            self._balances.order_updated(order, final_updates)
            logger.debug(logs.StructuredMessage(
                "Order updated", order_id=order.id, final_updates=final_updates, order_state=order.state
            ))
        else:
            order_not_filled()

    def _process_orders(self, bar_event: bar.BarEvent):
        if (liquidity_strategy := self._liquidity_strategies.get(bar_event.bar.pair)) is None:
            liquidity_strategy = self._liquidity_strategy_factory()
        liquidity_strategy.on_bar(bar_event.bar)
        for order in filter(lambda o: o.pair == bar_event.bar.pair, self._orders.get_open()):
            self._process_order(order, bar_event, liquidity_strategy)

    async def _on_bar_event(self, event: event.Event):
        assert isinstance(event, bar.BarEvent), f"{event} is not an instance of bar.BarEvent"

        self._last_bars[event.bar.pair] = event.bar
        self._process_orders(event)
        # Forward the event to the right source, if any.
        event_source = self._bar_event_source.get(event.bar.pair)
        if event_source:
            event_source.push(event)

    def _check_balance_requirements(
            self, required_balances: Dict[str, Decimal], order: Optional[orders.Order] = None,
            log_context: Dict[str, Any] = {}, raise_if_short: bool = False
    ) -> bool:
        ret = True

        for symbol, required in required_balances.items():
            assert required > Decimal(0), f"Invalid required balance {required} for {symbol}"

            available_balance = self._balances.get_available_balance(symbol)
            if order:
                available_balance += self._balances.get_balance_on_hold_for_order(order.id, symbol)

            balance_short = max(required - available_balance, Decimal(0))
            if balance_short == Decimal(0):
                continue

            ret = False
            logger.debug(logs.StructuredMessage("Balance is short", symbol=symbol, short=balance_short, **log_context))

            # Fail if required.
            if raise_if_short:
                raise errors.Error("Not enough {} available. {} are required and {} are available".format(
                    symbol, required, available_balance
                ))

        return ret

    async def _get_last_price(self, pair: Pair) -> Optional[Decimal]:
        last_bar = self._last_bars.get(pair)
        return last_bar.close if last_bar else None

    async def _estimate_required_balances(self, order_request: requests.ExchangeOrder) -> Dict[str, Decimal]:
        # Build a dictionary of balance updates suitable for calculating fees.
        base_sign = bt_helpers.get_base_sign_for_operation(order_request.operation)
        estimated_balance_updates = {
            order_request.pair.base_symbol: order_request.amount * base_sign
        }
        estimated_fill_price = order_request.get_estimated_fill_price()
        if not estimated_fill_price:
            estimated_fill_price = await self._get_last_price(order_request.pair)
        if estimated_fill_price:
            estimated_balance_updates[order_request.pair.quote_symbol] = \
                order_request.amount * estimated_fill_price * -base_sign
        estimated_balance_updates = self._round_balance_updates(order_request.pair, estimated_balance_updates)

        # Calculate fees.
        fees = {}
        if len(estimated_balance_updates) == 2:
            order = order_request.create_order("temporary")
            fees = self._fee_strategy.calculate_fees(order, estimated_balance_updates)
            fees = self._round_fees(order_request.pair, fees)
        estimated_balance_updates = bt_helpers.add_amounts(estimated_balance_updates, fees)

        # Return only negative balance updates as required balances.
        return {symbol: -amount for symbol, amount in estimated_balance_updates.items() if amount < Decimal(0)}

    def _get_all_orders(self) -> Sequence[orders.Order]:
        return list(self._orders.get_all())

    def _get_dispatcher(self) -> dispatcher.EventDispatcher:
        return self._dispatcher

    def _get_balance(self, symbol: str) -> Balance:
        available = self._balances.get_available_balance(symbol)
        hold = self._balances.get_balance_on_hold(symbol)
        borrowed = self._balances.get_borrowed_balance(symbol)
        return Balance(
            available=available, hold=hold, borrowed=borrowed, interest=Decimal(0)
        )
