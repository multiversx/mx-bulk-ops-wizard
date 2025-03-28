import time
from multiprocessing.dummy import Pool
from typing import Any, Callable

from multiversx_sdk import (Account, AccountOnNetwork, Address,
                            ApiNetworkProvider, AwaitingOptions, GenericError,
                            NetworkEntrypoint, NetworkProviderConfig,
                            ProxyNetworkProvider, Transaction,
                            TransactionOnNetwork)
from multiversx_sdk.abi import BigUIntValue, BytesValue, U64Value
from multiversx_sdk.core.interfaces import IAccount
from rich import print

from collector import ux
from collector.configuration import Configuration
from collector.constants import (
    ACCOUNT_AWAITING_PATIENCE_IN_MILLISECONDS,
    ACCOUNT_AWAITING_POLLING_TIMEOUT_IN_MILLISECONDS,
    CONTRACT_RESULTS_CODE_OK_ENCODED, DEFAULT_CHUNK_SIZE_OF_SEND_TRANSACTIONS,
    MAX_NUM_TRANSACTIONS_TO_FETCH_OF_TYPE_CLAIM_REWARDS,
    MAX_NUM_TRANSACTIONS_TO_FETCH_OF_TYPE_REWARDS, METACHAIN_ID,
    NETWORK_PROVIDER_NUM_RETRIES, NETWORK_PROVIDER_TIMEOUT_SECONDS,
    NETWORK_PROVIDERS_RETRY_DELAY_IN_SECONDS, NUM_PARALLEL_GET_NONCE_REQUESTS,
    NUM_PARALLEL_GET_TRANSACTION_REQUESTS)
from collector.errors import KnownError, TransientError
from collector.rewards import ClaimableRewards, ReceivedRewards, RewardsType
from collector.transactions import TransactionWrapper
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

    def get_start_of_epoch_timestamp(self, epoch: int) -> int:
        url = f"network/epoch-start/{METACHAIN_ID}/by-epoch/{epoch}"
        data = self.proxy_network_provider.do_get_generic(url)
        timestamp = data.get("epochStart", {}).get("timestamp", 0)
        return timestamp

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

    def recall_nonces(self, accounts: list[IAccount]):
        def recall_nonce(account: Any):
            account.nonce = self.network_entrypoint.recall_account_nonce(account.address)

        Pool(NUM_PARALLEL_GET_NONCE_REQUESTS).map(recall_nonce, accounts)

    def claim_rewards(self, delegator: IAccount, staking_provider: Address, gas_price: int) -> Transaction:
        delegator_as_any: Any = delegator
        controller = self.network_entrypoint.create_delegation_controller()

        transaction = controller.create_transaction_for_claiming_rewards(
            sender=delegator,
            nonce=delegator_as_any.get_nonce_then_increment(),
            delegation_contract=staking_provider,
            gas_price=gas_price
        )

        return transaction

    def claim_rewards_legacy(self, delegator: IAccount, gas_price: int) -> Transaction:
        delegator_as_any: Any = delegator
        legacy_delegation_contract = Address.new_from_bech32(self.configuration.legacy_delegation_contract)

        controller = self.network_entrypoint.create_smart_contract_controller()
        transaction = controller.create_transaction_for_execute(
            sender=delegator,
            nonce=delegator_as_any.get_nonce_then_increment(),
            contract=legacy_delegation_contract,
            gas_limit=20_000_000,
            function="claimRewards",
            gas_price=gas_price
        )

        return transaction

    def get_claimed_rewards(self, delegator: Address, after_timestamp: int) -> list[ReceivedRewards]:
        url = f"accounts/{delegator.to_bech32()}/transactions"
        size = MAX_NUM_TRANSACTIONS_TO_FETCH_OF_TYPE_CLAIM_REWARDS
        transactions = self._api_do_get(url, {
            "status": "success",
            "function": "claimRewards",
            "withScResults": "true",
            "receiverShard": METACHAIN_ID,
            "after": after_timestamp,
            "size": size
        })

        if len(transactions) == size:
            print(f"\tRetrieved {size} transactions. [red]There could be more![/red]")

        rewards: list[ReceivedRewards] = []

        for transaction in transactions:
            transaction_hash = transaction.get("txHash")
            timestamp = transaction.get("timestamp")
            results = transaction.get("results", [])
            reward_result = next((item for item in results if item.get("data") != CONTRACT_RESULTS_CODE_OK_ENCODED), None)
            amount = int(reward_result.get("value", 0)) if reward_result else 0

            if amount:
                rewards.append(ReceivedRewards(RewardsType.Delegation, transaction_hash, timestamp, amount))

        return rewards

    def get_claimed_rewards_legacy(self, delegator: Address, after_timestamp: int) -> list[ReceivedRewards]:
        url = f"accounts/{delegator.to_bech32()}/transactions"
        size = MAX_NUM_TRANSACTIONS_TO_FETCH_OF_TYPE_CLAIM_REWARDS
        transactions = self._api_do_get(url, {
            "status": "success",
            "function": "claimRewards",
            "withScResults": "true",
            "receiver": self.configuration.legacy_delegation_contract,
            "after": after_timestamp,
            "size": size
        })

        if len(transactions) == size:
            print(f"\tRetrieved {size} transactions. [red]There could be more![/red]")

        rewards: list[ReceivedRewards] = []

        for transaction in transactions:
            transaction_hash = transaction.get("txHash")
            timestamp = transaction.get("timestamp")
            results = transaction.get("results", [])
            reward_result = next((item for item in results if item.get("data") != CONTRACT_RESULTS_CODE_OK_ENCODED), None)
            amount = int(reward_result.get("value", 0)) if reward_result else 0

            if amount:
                rewards.append(ReceivedRewards(RewardsType.DelegationLegacy, transaction_hash, timestamp, amount))

        return rewards

    def get_received_staking_rewards(self, node_owner: Address, after_timestamp: int) -> list[ReceivedRewards]:
        url = f"accounts/{node_owner.to_bech32()}/transactions"
        size = MAX_NUM_TRANSACTIONS_TO_FETCH_OF_TYPE_REWARDS
        transactions = self._api_do_get(url, {
            "senderShard": METACHAIN_ID,
            "function": "reward",
            "after": after_timestamp,
            "size": size
        })

        if len(transactions) == size:
            print(f"\tRetrieved {size} transactions. [red]There could be more![/red]")

        rewards: list[ReceivedRewards] = []

        for transaction in transactions:
            transaction_hash = transaction.get("txHash")
            timestamp = transaction.get("timestamp")
            amount = int(transaction.get("value", 0))

            if amount:
                rewards.append(ReceivedRewards(RewardsType.Staking, transaction_hash, timestamp, amount))

        return rewards

    def transfer_value(self, sender: IAccount, receiver: Address, amount: int) -> Transaction:
        sender_as_any: Any = sender

        controller = self.network_entrypoint.create_transfers_controller()
        transaction = controller.create_transaction_for_native_token_transfer(
            sender=sender,
            nonce=sender_as_any.get_nonce_then_increment(),
            receiver=receiver,
            native_transfer_amount=amount
        )

        return transaction

    def vote_on_governance(self, sender: IAccount, proposal: int, choice: int, power: int, proof: bytes, gas_price: int) -> Transaction:
        sender_as_any: Any = sender
        governance_contract = Address.new_from_bech32(self.configuration.governance_contract)

        controller = self.network_entrypoint.create_smart_contract_controller()
        transaction = controller.create_transaction_for_execute(
            sender=sender,
            nonce=sender_as_any.get_nonce_then_increment(),
            contract=governance_contract,
            gas_limit=50_000_000,
            function="vote",
            arguments=[
                U64Value(proposal),
                U64Value(choice),
                BigUIntValue(power),
                BytesValue(proof)
            ],
            gas_price=gas_price
        )

        return transaction

    def send_multiple(self, wrappers: list[TransactionWrapper], chunk_size: int = DEFAULT_CHUNK_SIZE_OF_SEND_TRANSACTIONS):
        print(f"Sending {len(wrappers)} transactions...")

        chunks: list[list[TransactionWrapper]] = list(split_to_chunks(wrappers, chunk_size))

        for index, chunk in enumerate(chunks):
            print(f"Chunk {index}:")

            for item in chunk:
                print(f"\t{item.hash} ([yellow]{item.label}[/yellow])")

            num_sent, _ = self.network_entrypoint.send_transactions([item.transaction for item in chunk])
            print(f"Chunk {index}: sent {num_sent} transactions.")

            if num_sent != len(chunk):
                raise KnownError(f"sent {num_sent} transactions, instead of {len(chunk)}")

            self.await_processing_started(chunk)

        self.await_completed(wrappers)

    def await_processing_started(self, wrappers: list[TransactionWrapper]) -> list[TransactionOnNetwork]:
        print(f"Await processing started for {len(wrappers)} transactions...")

        def await_processing_started_one(wrapper: TransactionWrapper) -> TransactionOnNetwork:
            condition: Callable[[AccountOnNetwork], bool] = lambda account: account.nonce > wrapper.transaction.nonce
            self.proxy_network_provider.await_account_on_condition(
                address=wrapper.transaction.sender,
                condition=condition,
                options=self.account_awaiting_options,
            )

            transaction_on_network = self.proxy_network_provider.get_transaction(wrapper.hash)

            print(f"Started: {self.configuration.explorer_url}/transactions/{wrapper.hash}")
            return transaction_on_network

        transactions_on_network = Pool(NUM_PARALLEL_GET_TRANSACTION_REQUESTS).map(
            await_processing_started_one,
            wrappers
        )

        return transactions_on_network

    def await_completed(self, wrappers: list[TransactionWrapper]) -> list[TransactionOnNetwork]:
        def await_completed_one(wrapper: TransactionWrapper) -> TransactionOnNetwork:
            transaction_on_network = self.api_network_provider.await_transaction_completed(
                transaction_hash=wrapper.hash,
                options=self.transaction_awaiting_options
            )

            print(f"Completed: {self.configuration.explorer_url}/transactions/{wrapper.hash}")
            return transaction_on_network

        ux.show_message(f"Transactions sent. Waiting for their completion...")

        transactions_on_network = Pool(NUM_PARALLEL_GET_TRANSACTION_REQUESTS).map(
            await_completed_one,
            wrappers
        )

        return transactions_on_network

    def _api_do_get(self, url: str, url_parameters: dict[str, Any]):
        latest_error = None

        for attempt in range(NETWORK_PROVIDER_NUM_RETRIES):
            try:
                return self.api_network_provider.do_get_generic(url, url_parameters)
            except GenericError as error:
                latest_error = error

                print(f"Attempt #{attempt}, [red]failed to get {error.url}[/red]")

                is_last_attempt = attempt == NETWORK_PROVIDER_NUM_RETRIES - 1
                if not is_last_attempt:
                    time.sleep(NETWORK_PROVIDERS_RETRY_DELAY_IN_SECONDS)

        raise TransientError(f"cannot get from API", latest_error)
