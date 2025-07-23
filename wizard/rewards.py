from enum import Enum
from typing import Any

from multiversx_sdk import Address

from wizard.utils import format_native_amount, format_time


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

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        type = RewardsType(data["type"])
        transaction_hash = data["transaction"]
        timestamp = data["timestamp"]
        amount = int(data["amount"])

        return cls(type, transaction_hash, timestamp, amount)

    def to_dictionary(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "transaction": self.transaction_hash,
            "timestamp": self.timestamp,
            "timestampFormatted": format_time(self.timestamp),
            "amount": self.amount,
            "amountFormatted": f"{format_native_amount(self.amount)}"
        }


class ReceivedRewardsOfAccount:
    def __init__(self, address: Address, label: str, rewards: list[ReceivedRewards]) -> None:
        self.address = address
        self.label = label
        self.rewards = rewards

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        address = Address.new_from_bech32(data["address"])
        label = data["label"]
        rewards_raw = data["rewards"]
        rewards = [ReceivedRewards.new_from_dictionary(item) for item in rewards_raw]

        return cls(address, label, rewards)

    def sort_rewards(self):
        self.rewards.sort(key=lambda item: item.timestamp, reverse=True)

    def to_dictionary(self) -> dict[str, Any]:
        num_rewards = len(self.rewards)
        total_amount = sum([item.amount for item in self.rewards])

        return {
            "address": self.address.to_bech32(),
            "label": self.label,
            "numRewards": num_rewards,
            "totalAmountFormatted": f"{format_native_amount(total_amount)}",
            "rewards": [item.to_dictionary() for item in self.rewards]
        }
