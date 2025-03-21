from enum import Enum
from typing import Any

from multiversx_sdk import Address

from collector.utils import format_amount, format_time


class RewardsType(str, Enum):
    Unknown = "unknown"
    Delegation = "delegation"
    DelegationLegacy = "delegation-legacy"
    Staking = "staking"


class ClaimableRewards:
    def __init__(self, staking_provider: Address, amount: int) -> None:
        self.staking_provider = staking_provider
        self.amount = amount


class ReceivedRewards:
    def __init__(self, type: RewardsType, transaction_hash: str, timestamp: int, amount: int) -> None:
        self.type = type
        self.transaction_hash = transaction_hash
        self.timestamp = timestamp
        self.amount = amount

    def to_dictionary(self) -> dict[str, Any]:
        return {
            "type": self.type.name,
            "transaction": self.transaction_hash,
            "time": format_time(self.timestamp),
            "amount": self.amount,
            "amountFormatted": f"{format_amount(self.amount, num_decimals=6)} EGLD"
        }


class ReceivedRewardsOfAccount:
    def __init__(self, address: Address, label: str, rewards: list[ReceivedRewards]) -> None:
        self.address = address
        self.label = label
        self.rewards = rewards

    def sort_rewards(self):
        self.rewards.sort(key=lambda item: item.timestamp, reverse=True)

    def to_dictionary(self) -> dict[str, Any]:
        return {
            "address": self.address.to_bech32(),
            "label": self.label,
            "rewards": [item.to_dictionary() for item in self.rewards]
        }
