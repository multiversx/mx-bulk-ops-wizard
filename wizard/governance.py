
import json
from pathlib import Path
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

    @classmethod
    def load_many_from_proofs_file(cls, proofs_file: Path):
        json_content = proofs_file.read_text()
        data = json.loads(json_content)
        records = [GovernanceRecord.new_from_dictionary(item) for item in data]

        records_by_adresses: dict[str, GovernanceRecord] = {
            item.address.to_bech32(): item for item in records
        }

        return records_by_adresses


class OnChainVote:
    def __init__(self, voter: str, proposal: int, contract: str, timestamp: int, vote_type: VoteType) -> None:
        self.voter = voter
        self.proposal = proposal
        self.contract = contract
        self.timestamp = timestamp
        self.vote_type = vote_type
