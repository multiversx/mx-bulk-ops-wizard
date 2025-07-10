from typing import Any

from multiversx_sdk import Address, Token, TokenTransfer
from multiversx_sdk.core.constants import \
    EGLD_IDENTIFIER_FOR_MULTI_ESDTNFT_TRANSFER

from wizard.utils import ICurrencyProvider, format_amount


class MyTransfer:
    def __init__(self, sender: Address, label: str, token_transfer: TokenTransfer) -> None:
        self.sender = sender
        self.label = label
        self.token_transfer = token_transfer

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        sender = Address.new_from_bech32(data["sender"])
        label = data["label"]
        amount = int(data["amount"])
        token_identifier = data.get("tokenIdentifier", EGLD_IDENTIFIER_FOR_MULTI_ESDTNFT_TRANSFER)
        token_nonce = data.get("tokenNonce", 0)

        token = Token(token_identifier, token_nonce)
        token_transfer = TokenTransfer(token, amount)
        return cls(sender, label, token_transfer)

    def to_dictionary(self, currency_provider: ICurrencyProvider) -> dict[str, Any]:
        amount = self.token_transfer.amount
        token_identifier = self.token_transfer.token.identifier
        token_nonce = self.token_transfer.token.nonce

        return {
            "sender": self.sender.to_bech32(),
            "label": self.label,
            "amount": amount,
            "amountFormatted": f"{format_amount(currency_provider, amount, token_identifier)}",
            "tokenIdentifier": token_identifier,
            "tokenNonce": token_nonce
        }
