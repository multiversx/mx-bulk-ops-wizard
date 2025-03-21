from typing import Any

from multiversx_sdk import Address

from collector.utils import format_amount


class Transfer:
    def __init__(self, sender: Address, label: str, amount: int) -> None:
        self.sender = sender
        self.label = label
        self.amount = amount

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        sender = Address.new_from_bech32(data["sender"])
        label = data["label"]
        amount = int(data["amount"])

        return cls(sender, label, amount)

    def to_dictionary(self) -> dict[str, Any]:
        return {
            "sender": self.sender.to_bech32(),
            "label": self.label,
            "amount": self.amount,
            "amountFormatted": f"{format_amount(self.amount, num_decimals=6)} EGLD"
        }
