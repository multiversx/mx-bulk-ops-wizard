from datetime import datetime, timezone
from typing import Any, Protocol

from collector.constants import ONE_QUINTILLION


class ICurrencyProvider(Protocol):
    def get_currency_name(self, token_identifier: str) -> str:
        ...

    def get_currency_num_decimals(self, token_identifier: str) -> int:
        ...


def split_to_chunks(items: list[Any], chunk_size: int):
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]


def format_amount(currency_provider: ICurrencyProvider, amount: int, token_identifier: str = "") -> str:
    num_decimals = currency_provider.get_currency_num_decimals(token_identifier)
    name = currency_provider.get_currency_name(token_identifier)

    return f"{amount / ONE_QUINTILLION:.{num_decimals}f} {name}"


def format_native_amount(amount: int) -> str:
    return f"{amount / ONE_QUINTILLION:.18f} EGLD"


def format_time(timestamp: int) -> str:
    time = datetime.fromtimestamp(timestamp, timezone.utc)
    return time.strftime("%Y-%m-%d %H:%M:%S")
