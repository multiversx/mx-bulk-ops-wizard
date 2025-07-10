
from typing import Any

from multiversx_sdk import Address


class GovernanceRecord:
    def __init__(self, address: Address, power: int, proof: bytes) -> None:
        self.address = address
        self.power = power
        self.proof = proof

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        address = Address.new_from_bech32(data["address"])
        power = int(data["balance"])
        proof = bytes.fromhex(data["proof"])

        return cls(address, power, proof)
