from multiversx_sdk import Address


class ClaimableRewards:
    def __init__(self, staking_provider: Address, amount: int) -> None:
        self.staking_provider = staking_provider
        self.amount = amount
