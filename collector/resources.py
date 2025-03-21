from enum import Enum

from multiversx_sdk import Address


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
    def __init__(self, type: RewardsType, transaction_hash: str, amount: int) -> None:
        self.type = type
        self.transaction_hash = transaction_hash
        self.amount = amount
