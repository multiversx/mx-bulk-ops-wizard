from typing import Any


def split_to_chunks(items: list[Any], chunk_size: int):
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]
