from datetime import datetime, timezone
from typing import Any

from collector.constants import ONE_QUINTILLION


def split_to_chunks(items: list[Any], chunk_size: int):
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]


def format_amount(amount: int, num_decimals=18) -> str:
    return f"{amount / ONE_QUINTILLION:.{num_decimals}f}"


def format_time(timestamp: int) -> str:
    time = datetime.fromtimestamp(timestamp, timezone.utc)
    return time.strftime("%Y-%m-%d %H:%M:%S")
