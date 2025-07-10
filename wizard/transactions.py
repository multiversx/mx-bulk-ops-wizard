from multiversx_sdk import Transaction, TransactionComputer


class TransactionWrapper:
    def __init__(self, transaction: Transaction, label: str) -> None:
        self.transaction = transaction
        self.label = label

    def get_hash(self) -> str:
        return TransactionComputer().compute_transaction_hash(self.transaction).hex()
