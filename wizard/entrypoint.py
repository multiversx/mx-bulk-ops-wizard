import time
from multiprocessing.dummy import Pool
from typing import Any, Callable

from multiversx_sdk import (AccountOnNetwork, Address, ApiNetworkProvider,
                            AwaitingOptions, Message, NativeAuthClient,
                            NativeAuthClientConfig, NetworkEntrypoint,
                            NetworkProviderConfig, NetworkProviderError,
                            ProxyNetworkProvider, Token, TokenTransfer,
                            Transaction, TransactionOnNetwork)
from multiversx_sdk.abi import BigUIntValue, BytesValue, U64Value
from rich import print

from wizard import ux
from wizard.accounts import AccountWrapper, IMyAccount
from wizard.configuration import Configuration
from wizard.constants import (
    ACCOUNT_AWAITING_PATIENCE_IN_MILLISECONDS,
    ACCOUNT_AWAITING_POLLING_TIMEOUT_IN_MILLISECONDS,
    CONTRACT_RESULTS_CODE_OK_ENCODED, COSIGNER_SERVICE_ID,
    COSIGNER_SIGN_TRANSACTIONS_RETRY_DELAY_IN_SECONDS,
    DEFAULT_CHUNK_SIZE_OF_SEND_TRANSACTIONS, MAX_NUM_CUSTOM_TOKENS_TO_FETCH,
    MAX_NUM_TRANSACTIONS_TO_FETCH_OF_TYPE_CLAIM_REWARDS,
    MAX_NUM_TRANSACTIONS_TO_FETCH_OF_TYPE_REWARDS, METACHAIN_ID,
    NETWORK_PROVIDER_NUM_RETRIES, NETWORK_PROVIDER_TIMEOUT_SECONDS,
    NETWORK_PROVIDERS_RETRY_DELAY_IN_SECONDS,
    NUM_PARALLEL_GET_GUARDIAN_DATA_REQUESTS, NUM_PARALLEL_GET_NONCE_REQUESTS,
    NUM_PARALLEL_GET_TRANSACTION_REQUESTS,
    TRANSACTION_AWAITING_PATIENCE_IN_MILLISECONDS,
    TRANSACTION_AWAITING_POLLING_TIMEOUT_IN_MILLISECONDS)
from wizard.currencies import is_native_currency
from wizard.errors import KnownError, TransientError
from wizard.guardians import (AuthApp, AuthRegistrationEntry, CosignerClient,
                              GuardianData)
from wizard.rewards import ClaimableRewards, ReceivedRewards, RewardsType
from wizard.timecache import TimeCache
from wizard.transactions import TransactionWrapper
from wizard.utils import split_to_chunks


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

        self.deep_history_proxy_network_provider = ProxyNetworkProvider(
            url=configuration.deep_history_url,
            config=NetworkProviderConfig(requests_options={"timeout": NETWORK_PROVIDER_TIMEOUT_SECONDS})
        )

        self.account_awaiting_options = AwaitingOptions(
            polling_interval_in_milliseconds=ACCOUNT_AWAITING_POLLING_TIMEOUT_IN_MILLISECONDS,
            patience_in_milliseconds=ACCOUNT_AWAITING_PATIENCE_IN_MILLISECONDS
        )

        self.transaction_awaiting_options = AwaitingOptions(
            polling_interval_in_milliseconds=TRANSACTION_AWAITING_POLLING_TIMEOUT_IN_MILLISECONDS,
            patience_in_milliseconds=TRANSACTION_AWAITING_PATIENCE_IN_MILLISECONDS
        )

        native_auth_config = NativeAuthClientConfig(
            origin=self.configuration.api_url,
            api_url=self.configuration.api_url,
        )

        self.native_auth_client = NativeAuthClient(native_auth_config)
        self.cosigner = CosignerClient(configuration.cosigner_url)
        self.timecache = TimeCache()

    def get_start_of_epoch_timestamp(self, epoch: int) -> int:
        url = f"network/epoch-start/{METACHAIN_ID}/by-epoch/{epoch}"
        data = self.proxy_network_provider.do_get_generic(url)
        timestamp = data.get("epochStart", {}).get("timestamp", 0)
        return timestamp

    def get_start_of_epoch_nonce(self, shard: int, epoch: int) -> int:
        url = f"network/epoch-start/{shard}/by-epoch/{epoch}"
        data = self.proxy_network_provider.do_get_generic(url)
        nonce = data.get("epochStart", {}).get("nonce", 0)
        return nonce

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

    def recall_nonces(self, accounts_wrappers: list[AccountWrapper]):
        def recall_nonce(wrapper: AccountWrapper):
            wrapper.account.nonce = self.network_entrypoint.recall_account_nonce(wrapper.account.address)

        Pool(NUM_PARALLEL_GET_NONCE_REQUESTS).map(recall_nonce, accounts_wrappers)

    def recall_guardians(self, accounts: list[AccountWrapper]):
        def recall_guardian(wrapper: AccountWrapper):
            guardian_data = self.get_guardian_data(wrapper.account.address)
            wrapper.guardian = Address.new_from_bech32(guardian_data.active_guardian) if guardian_data.is_guarded else None

        Pool(NUM_PARALLEL_GET_GUARDIAN_DATA_REQUESTS).map(recall_guardian, accounts)

    def claim_rewards(self, delegator: AccountWrapper, staking_provider: Address, gas_price: int) -> Transaction:
        controller = self.network_entrypoint.create_delegation_controller()

        transaction = controller.create_transaction_for_claiming_rewards(
            sender=delegator.account,
            nonce=delegator.account.get_nonce_then_increment(),
            delegation_contract=staking_provider,
            gas_price=gas_price,
            guardian=delegator.guardian
        )

        return transaction

    def claim_rewards_legacy(self, delegator: AccountWrapper, gas_price: int) -> Transaction:
        legacy_delegation_contract = Address.new_from_bech32(self.configuration.legacy_delegation_contract)

        controller = self.network_entrypoint.create_smart_contract_controller()
        transaction = controller.create_transaction_for_execute(
            sender=delegator.account,
            nonce=delegator.account.get_nonce_then_increment(),
            contract=legacy_delegation_contract,
            gas_limit=20_000_000,
            function="claimRewards",
            gas_price=gas_price,
            guardian=delegator.guardian
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

    def transfer_funds(self, sender: AccountWrapper, receiver: Address, transfer: TokenTransfer) -> Transaction:
        controller = self.network_entrypoint.create_transfers_controller()

        if is_native_currency(transfer.token.identifier):
            return controller.create_transaction_for_transfer(
                sender=sender.account,
                nonce=sender.account.get_nonce_then_increment(),
                receiver=receiver,
                native_transfer_amount=transfer.amount,
                guardian=sender.guardian
            )

        return controller.create_transaction_for_transfer(
            sender=sender.account,
            nonce=sender.account.get_nonce_then_increment(),
            receiver=receiver,
            token_transfers=[transfer],
            guardian=sender.guardian
        )

    def vote_on_governance(self, sender: AccountWrapper, proposal: int, choice: int, power: int, proof: bytes, gas_price: int) -> Transaction:
        governance_contract = Address.new_from_bech32(self.configuration.governance_contract)

        controller = self.network_entrypoint.create_smart_contract_controller()
        transaction = controller.create_transaction_for_execute(
            sender=sender.account,
            nonce=sender.account.get_nonce_then_increment(),
            contract=governance_contract,
            gas_limit=50_000_000,
            function="vote",
            arguments=[
                U64Value(proposal),
                U64Value(choice),
                BigUIntValue(power),
                BytesValue(proof)
            ],
            gas_price=gas_price,
            guardian=sender.guardian
        )

        return transaction

    def get_guardian_data(self, address: Address):
        response = self.proxy_network_provider.do_get_generic(f"address/{address.to_bech32()}/guardian-data")
        response_payload = response.get("guardianData", {})
        guardian_data = GuardianData.new_from_response_payload(response_payload)
        return guardian_data

    def register_cosigner(self, auth_app: AuthApp, account_wrapper: AccountWrapper) -> AuthRegistrationEntry:
        access_token = self.get_native_auth_access_tokens(account_wrapper.account)

        registration_entry = self.cosigner.register(
            native_auth_access_token=access_token,
            address=account_wrapper.account.address.to_bech32(),
            wallet_name=account_wrapper.wallet_name,
        )

        secret = registration_entry.secret
        code = auth_app.get_code_given_secret(secret)

        self.cosigner.verify_code(
            native_auth_access_token=access_token,
            code=code,
            guardian=registration_entry.get_guardian(),
        )

        auth_app.learn_registration_entry(registration_entry)

        return registration_entry

    def get_native_auth_init_token(self) -> str:
        init_token = self.timecache.get("native_auth_init_token", lambda: (self.native_auth_client.initialize(), 60))
        return init_token

    def get_native_auth_access_tokens(self, account: IMyAccount) -> str:
        init_token = self.get_native_auth_init_token()
        token_for_signing = self.native_auth_client.get_token_for_signing(account.address, init_token)
        signature = account.sign_message(Message(token_for_signing))
        access_token = self.native_auth_client.get_token(address=account.address, token=init_token, signature=signature.hex())
        return access_token

    def set_guardian(self, sender: AccountWrapper, guardian: Address) -> Transaction:
        controller = self.network_entrypoint.create_account_controller()
        transaction = controller.create_transaction_for_setting_guardian(
            sender=sender.account,
            nonce=sender.account.get_nonce_then_increment(),
            guardian_address=guardian,
            service_id=COSIGNER_SERVICE_ID,
            guardian=sender.guardian
        )

        return transaction

    def guard_account(self, sender: AccountWrapper) -> Transaction:
        controller = self.network_entrypoint.create_account_controller()
        transaction = controller.create_transaction_for_guarding_account(
            sender=sender.account,
            nonce=sender.account.get_nonce_then_increment(),
        )

        return transaction

    def get_custom_tokens(self, address: Address, identifier_or_collection: str) -> list[Token]:
        # For the moment, we ignore NFTs.
        # We have to perform this GET, so that we can observe all MetaESDTs (all nonces) held by the account, as well.
        data_esdt_and_meta: list[dict[str, Any]] = self.api_network_provider.do_get_generic(
            f"accounts/{address.to_bech32()}/tokens", {
                "from": 0,
                "size": MAX_NUM_CUSTOM_TOKENS_TO_FETCH,
                "fields": "identifier,collection,nonce",
                "includeMetaESDT": True,
            })

        tokens: list[Token] = []

        for item in data_esdt_and_meta:
            collection = item.get("collection", "")
            identifier = item.get("identifier", "")
            nonce = int(item.get("nonce", 0))
            item_identifier_or_collection = identifier if nonce == 0 else collection

            if item_identifier_or_collection != identifier_or_collection:
                continue

            tokens.append(Token(item_identifier_or_collection, nonce))

        return tokens

    def get_custom_token_balance(self, token: Token, address: Address, block_nonce: int) -> int:
        current_state = self.api_network_provider.get_token_of_account(address, token)
        current_balance = current_state.amount

        if not block_nonce:
            return current_state.amount

        historical_balance = self.get_custom_token_balance_on_block_nonce(token, address, block_nonce)
        return max(current_balance - historical_balance, 0)

    def get_custom_token_balance_on_block_nonce(self, token: Token, address: Address, block_nonce: int) -> int:
        if token.nonce == 0:
            response = self.deep_history_proxy_network_provider.do_get_generic(f"address/{address.to_bech32()}/esdt/{token.identifier}?blockNonce={block_nonce}")
        else:
            response = self.deep_history_proxy_network_provider.do_get_generic(f"address/{address.to_bech32()}/nft/{token.identifier}/nonce/{token.nonce}?blockNonce={block_nonce}")

        balance = response.get("balance", 0)
        return balance

    def send_multiple(self, auth_app: AuthApp, wrappers: list[TransactionWrapper], chunk_size: int = DEFAULT_CHUNK_SIZE_OF_SEND_TRANSACTIONS):
        print("Cosigning transactions, if necessary...")
        self.guard_transactions(auth_app, wrappers)

        print(f"Sending {len(wrappers)} transactions...")

        chunks: list[list[TransactionWrapper]] = list(split_to_chunks(wrappers, chunk_size))

        for index, chunk in enumerate(chunks):
            print(f"Chunk {index}:")

            for item in chunk:
                print(f"\t{item.get_hash()} ([yellow]{item.label}[/yellow])")

            num_sent, _ = self.network_entrypoint.send_transactions([item.transaction for item in chunk])
            print(f"Chunk {index}: sent {num_sent} transactions.")

            if num_sent != len(chunk):
                raise KnownError(f"sent {num_sent} transactions, instead of {len(chunk)}")

            self.await_processing_started(chunk)

        self.await_completed(wrappers)

    def send_one_by_one(self, auth_app: AuthApp, wrappers: list[TransactionWrapper]):
        print("Cosigning transactions, if necessary...")
        self.guard_transactions(auth_app, wrappers)

        print(f"Sending {len(wrappers)} transactions...")

        for index, wrapper in enumerate(wrappers):
            print(f"{index}: {wrapper.get_hash()} ([yellow]{wrapper.label}[/yellow])")

            _ = self.network_entrypoint.send_transaction(wrapper.transaction)
            self.await_processing_started([wrapper])

        self.await_completed(wrappers)

    def guard_transactions(self, auth_app: AuthApp, wrappers: list[TransactionWrapper]):
        grouped_by_sender: dict[str, list[Transaction]] = {}

        for index, wrapper in enumerate(wrappers):
            if wrapper.transaction.guardian is None:
                continue

            sender = wrapper.transaction.sender.to_bech32()
            grouped_by_sender.setdefault(sender, []).append(wrapper.transaction)

        # Signatures are applied inline.
        for sender, transactions in grouped_by_sender.items():
            while True:
                try:
                    print(f"Attempt to co-sign transactions from {sender}...")
                    code = auth_app.get_code(sender)
                    self.cosigner.sign_multiple_transactions(code, transactions)
                    break
                except KnownError as error:
                    print(f"Unexpected error: [red]{error}[/red], will retry in {COSIGNER_SIGN_TRANSACTIONS_RETRY_DELAY_IN_SECONDS} seconds...")
                    time.sleep(COSIGNER_SIGN_TRANSACTIONS_RETRY_DELAY_IN_SECONDS)

    def await_processing_started(self, wrappers: list[TransactionWrapper]) -> list[TransactionOnNetwork]:
        print(f"Await processing started for {len(wrappers)} transactions...")

        def await_processing_started_one(wrapper: TransactionWrapper) -> TransactionOnNetwork:
            condition: Callable[[AccountOnNetwork], bool] = lambda account: account.nonce > wrapper.transaction.nonce
            self.proxy_network_provider.await_account_on_condition(
                address=wrapper.transaction.sender,
                condition=condition,
                options=self.account_awaiting_options,
            )

            transaction_on_network = self.proxy_network_provider.get_transaction(wrapper.get_hash())

            print(f"Started: {self.configuration.explorer_url}/transactions/{wrapper.get_hash()}")
            return transaction_on_network

        transactions_on_network = Pool(NUM_PARALLEL_GET_TRANSACTION_REQUESTS).map(
            await_processing_started_one,
            wrappers
        )

        return transactions_on_network

    def await_completed(self, wrappers: list[TransactionWrapper]) -> list[TransactionOnNetwork]:
        def await_completed_one(wrapper: TransactionWrapper) -> TransactionOnNetwork:
            transaction_on_network = self.api_network_provider.await_transaction_completed(
                transaction_hash=wrapper.get_hash(),
                options=self.transaction_awaiting_options
            )

            print(f"Completed: {self.configuration.explorer_url}/transactions/{wrapper.get_hash()}")
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
            except NetworkProviderError as error:
                latest_error = error

                print(f"Attempt #{attempt}, [red]failed to get {error.url}[/red]")

                is_last_attempt = attempt == NETWORK_PROVIDER_NUM_RETRIES - 1
                if not is_last_attempt:
                    time.sleep(NETWORK_PROVIDERS_RETRY_DELAY_IN_SECONDS)

        raise TransientError(f"cannot get from API", latest_error)
