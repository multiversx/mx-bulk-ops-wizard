from typing import Any

from collector.constants import ONE_QUINTILLION


def split_to_chunks(items: list[Any], chunk_size: int):
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]


def format_amount(amount: int) -> str:
    return f"{amount / ONE_QUINTILLION:.2f}"
