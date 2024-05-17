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
from typing import Dict, List, Optional
import abc
import dataclasses
import datetime
import logging

from basana.backtesting import account_balances, config, errors, helpers as bt_helpers, prices, value_map
from basana.backtesting.value_map import ValueMapDict
from basana.core import dispatcher, logs
import basana.core.helpers as core_helpers


logger = logging.getLogger(__name__)


@dataclasses.dataclass
class LoanInfo:
    #: The loan id.
    id: str
    #: True if the loan is open, False otherwise.
    is_open: bool
    #: The symbol being borrowed.
    borrowed_symbol: str
    #: The amount being borrowed.
    borrowed_amount: Decimal


class Loan(metaclass=abc.ABCMeta):
    def __init__(
            self, id: str, borrowed_symbol: str,  borrowed_amount: Decimal, created_at: datetime.datetime
    ):
        assert borrowed_amount > Decimal(0), f"Invalid amount {borrowed_amount}"

        self._id = id
        self._borrowed_symbol = borrowed_symbol
        self._borrowed_amount = borrowed_amount
        self._is_open = True
        self._created_at = created_at

    def get_loan_info(self) -> LoanInfo:
        return LoanInfo(
            id=self._id, is_open=self._is_open, borrowed_symbol=self._borrowed_symbol,
            borrowed_amount=self._borrowed_amount
        )

    @property
    def id(self) -> str:
        return self._id

    @property
    def is_open(self) -> bool:
        return self._is_open

    @property
    def borrowed_symbol(self) -> str:
        return self._borrowed_symbol

    @property
    def borrowed_amount(self) -> Decimal:
        return self._borrowed_amount

    def close(self):
        assert self._is_open
        self._is_open = False

    @abc.abstractmethod
    def calculate_interest(self, at: datetime.datetime, prices: prices.Prices) -> ValueMapDict:
        raise NotImplementedError()

    @abc.abstractmethod
    def calculate_collateral(self, prices: prices.Prices) -> ValueMapDict:
        raise NotImplementedError()


@dataclasses.dataclass
class ExchangeContext:
    dispatcher: dispatcher.EventDispatcher
    account_balances: account_balances.AccountBalances
    prices: prices.Prices
    config: config.Config


class LendingStrategy(metaclass=abc.ABCMeta):
    """
    Base class for lending strategies.
    """

    def set_exchange_context(self, loan_mgr: "LoanManager", exchange_context: ExchangeContext):
        """
        This method will be called during exchange initialization to give lending strategies a chance to later
        use those services.
        """
        pass

    @abc.abstractmethod
    def create_loan(self, symbol: str, amount: Decimal, created_at: datetime.datetime) -> Loan:
        raise NotImplementedError()


class NoLoans(LendingStrategy):
    """
    Lending not supported.
    """

    def create_loan(self, symbol: str, amount: Decimal, created_at: datetime.datetime) -> Loan:
        raise errors.Error("Lending is not supported")


class LoanManager:
    def __init__(
            self, lending_strategy: LendingStrategy, exchange_ctx: ExchangeContext
    ):
        self._loans = bt_helpers.ExchangeObjectContainer[Loan]()
        self._exchange_ctx = exchange_ctx
        self._lending_strategy = lending_strategy
        self._collateral_by_loan: Dict[str, value_map.ValueMap] = {}
        self._lending_strategy.set_exchange_context(self, exchange_ctx)

    def create_loan(
            self, symbol: str, amount: Decimal, now: datetime.datetime
    ) -> LoanInfo:
        if amount <= 0:
            raise errors.Error("Invalid amount")

        # Create the loan and update balances.
        loan = self._lending_strategy.create_loan(symbol, amount, now)
        required_collateral = loan.calculate_collateral(self._exchange_ctx.prices)
        self._exchange_ctx.account_balances.update(
            balance_updates={loan.borrowed_symbol: loan.borrowed_amount},
            borrowed_updates={loan.borrowed_symbol: loan.borrowed_amount},
            hold_updates=required_collateral
        )

        # Save the loan now that balance updates succeeded.
        self._loans.add(loan)
        self._collateral_by_loan[loan.id] = value_map.ValueMap(required_collateral)

        return loan.get_loan_info()

    def get_open_loans(self) -> List[LoanInfo]:
        return list(map(lambda loan: loan.get_loan_info(), self._loans.get_open()))

    def get_loan(self, loan_id: str) -> Optional[LoanInfo]:
        loan = self._loans.get(loan_id)
        return None if loan is None else loan.get_loan_info()

    def repay_loan(self, loan_id: str, now: datetime.datetime):
        loan = self._loans.get(loan_id)
        if not loan:
            raise errors.Error("Loan not found")
        if not loan.is_open:
            raise errors.Error("Loan is not open")

        interest = loan.calculate_interest(now, self._exchange_ctx.prices)
        for symbol, amount in interest.items():
            interest[symbol] = core_helpers.truncate_decimal(
                amount, self._exchange_ctx.config.get_symbol_info(symbol).precision
            )
        collateral = self._collateral_by_loan[loan_id]

        try:
            # Update balances.
            balance_updates = value_map.ValueMap({loan.borrowed_symbol: -loan.borrowed_amount})
            balance_updates -= interest
            self._exchange_ctx.account_balances.update(
                balance_updates=balance_updates,
                borrowed_updates={loan.borrowed_symbol: -loan.borrowed_amount},
                hold_updates={symbol: -amount for symbol, amount in collateral.items()}
            )

            # Close the loan now that balance updates succeeded.
            loan.close()
            self._collateral_by_loan.pop(loan_id)

        except errors.NotEnoughBalance as e:
            logger.debug(logs.StructuredMessage("Failed to repay the loan", loan_id=loan_id, error=str(e)))
            raise
