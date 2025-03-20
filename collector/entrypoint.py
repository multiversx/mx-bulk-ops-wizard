import time
from multiprocessing.dummy import Pool
from typing import Callable

from multiversx_sdk import (Account, AccountOnNetwork, Address,
                            ApiNetworkProvider, AwaitingOptions,
                            NetworkEntrypoint, NetworkProviderConfig,
                            ProxyNetworkProvider, Transaction,
                            TransactionComputer, TransactionOnNetwork)

from collector.configuration import Configuration
from collector.constants import (
    ACCOUNT_AWAITING_PATIENCE_IN_MILLISECONDS,
    ACCOUNT_AWAITING_POLLING_TIMEOUT_IN_MILLISECONDS,
    DEFAULT_CHUNK_SIZE_OF_SEND_TRANSACTIONS, NETWORK_PROVIDER_TIMEOUT_SECONDS,
    NUM_PARALLEL_GET_NONCE_REQUESTS, NUM_PARALLEL_GET_TRANSACTION_REQUESTS)
from collector.delegation import ClaimableRewards
from collector.errors import KnownError
from collector.utils import split_to_chunks


class MyEntrypoint:
    def __init__(self, configuration: Configuration) -> None:
        self.configuration = configuration

        self.network_entrypoint = NetworkEntrypoint(
            network_provider_url=configuration.proxy_url,
            network_provider_kind="proxy",
            chain_id=configuration.chain_id,
        )

        self.api_network_provider = ApiNetworkProvider(
            url=configuration.api_url,
            config=NetworkProviderConfig(requests_options={"timeout": NETWORK_PROVIDER_TIMEOUT_SECONDS})
        )

        self.proxy_network_provider = ProxyNetworkProvider(
            url=configuration.proxy_url,
            config=NetworkProviderConfig(requests_options={"timeout": NETWORK_PROVIDER_TIMEOUT_SECONDS})
        )

        self.account_awaiting_options = AwaitingOptions(
            polling_interval_in_milliseconds=ACCOUNT_AWAITING_POLLING_TIMEOUT_IN_MILLISECONDS,
            patience_in_milliseconds=ACCOUNT_AWAITING_PATIENCE_IN_MILLISECONDS
        )

        self.transaction_awaiting_options = AwaitingOptions(
            polling_interval_in_milliseconds=ACCOUNT_AWAITING_POLLING_TIMEOUT_IN_MILLISECONDS,
            patience_in_milliseconds=ACCOUNT_AWAITING_PATIENCE_IN_MILLISECONDS
        )

        self.transaction_computer = TransactionComputer()

    def get_claimable_rewards(self, delegator: Address) -> list[ClaimableRewards]:
        data_records = self.api_network_provider.do_get_generic(url=f"accounts/{delegator.to_bech32()}/delegation")

        rewards: list[ClaimableRewards] = []

        for record in data_records:
            staking_provider = Address.new_from_bech32(record.get("contract"))
            amount = record.get("claimableRewards", 0)
            rewards.append(ClaimableRewards(staking_provider, int(amount)))

        return rewards

    def get_claimable_rewards_legacy(self, delegator: Address) -> int:
        data = self.api_network_provider.do_get_generic(url=f"accounts/{delegator.to_bech32()}/delegation-legacy")
        amount = data.get("claimableRewards", 0)
        return int(amount)

    def recall_nonces(self, accounts: list[Account]):
        def recall_nonce(account: Account):
            account.nonce = self.network_entrypoint.recall_account_nonce(account.address)

        Pool(NUM_PARALLEL_GET_NONCE_REQUESTS).map(recall_nonce, accounts)

    def claim_rewards(self, delegator: Account, staking_provider: Address, gas_price: int) -> Transaction:
        controller = self.network_entrypoint.create_delegation_controller()
        transaction = controller.create_transaction_for_claiming_rewards(
            sender=delegator,
            nonce=delegator.get_nonce_then_increment(),
            delegation_contract=staking_provider,
            gas_price=gas_price
        )

        return transaction

    def claim_rewards_legacy(self, delegator: Account, gas_price: int) -> Transaction:
        legacy_delegation_contract = Address.new_from_bech32(self.configuration.legacy_delegation_contract)

        controller = self.network_entrypoint.create_smart_contract_controller()
        transaction = controller.create_transaction_for_execute(
            sender=delegator,
            nonce=delegator.get_nonce_then_increment(),
            contract=legacy_delegation_contract,
            gas_limit=20_000_000,
            function="claimRewards",
            gas_price=gas_price
        )

        return transaction

    def send_multiple(self, transactions: list[Transaction], chunk_size: int = DEFAULT_CHUNK_SIZE_OF_SEND_TRANSACTIONS):
        print(f"Sending {len(transactions)} transactions...")

        chunks = list(split_to_chunks(transactions, chunk_size))

        for index, chunk in enumerate(chunks):
            num_sent, _ = self.network_entrypoint.send_transactions(chunk)
            print(f"Chunk {index}: sent {num_sent} transactions.")

            if num_sent != len(chunk):
                raise KnownError(f"sent {num_sent} transactions, instead of {len(chunk)}")

            self.await_processing_started(chunk)

        self.await_completed(transactions)

    def await_processing_started(self, transactions: list[Transaction]) -> list[TransactionOnNetwork]:
        def await_processing_started_one(transaction: Transaction) -> TransactionOnNetwork:
            condition: Callable[[AccountOnNetwork], bool] = lambda account: account.nonce > transaction.nonce
            self.proxy_network_provider.await_account_on_condition(
                address=transaction.sender,
                condition=condition,
                options=self.account_awaiting_options,
            )

            transaction_hash = self.transaction_computer.compute_transaction_hash(transaction).hex()
            transaction_on_network = self.proxy_network_provider.get_transaction(transaction_hash)

            print(f"Processing started: {self.configuration.explorer_url}/transactions/{hash}")
            return transaction_on_network

        transactions_on_network = Pool(NUM_PARALLEL_GET_TRANSACTION_REQUESTS).map(await_processing_started_one, transactions)
        return transactions_on_network

    def await_completed(self, transactions: list[Transaction]) -> list[TransactionOnNetwork]:
        def await_completed_one(transaction: Transaction) -> TransactionOnNetwork:
            transaction_hash = self.transaction_computer.compute_transaction_hash(transaction).hex()
            transaction_on_network = self.api_network_provider.await_transaction_completed(
                transaction_hash=transaction_hash,
                options=self.transaction_awaiting_options
            )

            print(f"Completed: {self.configuration.explorer_url}/transactions/{hash}")
            return transaction_on_network

        transactions_on_network = Pool(8).map(await_completed_one, transactions)
        return transactions_on_network
