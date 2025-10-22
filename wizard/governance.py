
from typing import Any

from multiversx_sdk import Address, VoteType


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


class OnChainVote:
    def __init__(self, proposal: int, contract: str, timestamp: int, vote_type: VoteType) -> None:
        self.proposal = proposal
        self.contract = contract
        self.timestamp = timestamp
        self.vote_type = vote_type
