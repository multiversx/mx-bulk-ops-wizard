from multiprocessing.dummy import Pool

from multiversx_sdk import (Account, Address, ApiNetworkProvider,
                            NetworkEntrypoint, NetworkProviderConfig)

from collector.configuration import Configuration
from collector.constants import (API_TIMEOUT_SECONDS,
                                 NUM_PARALLEL_GET_NONCE_REQUESTS)
from collector.delegation import ClaimableRewards


class MyEntrypoint:
    def __init__(self, configuration: Configuration) -> None:
        self.network_entrypoint = NetworkEntrypoint(
            network_provider_url=configuration.proxy_url, network_provider_kind="proxy",
            chain_id=configuration.chain_id,
        )

        self.api_network_provider = ApiNetworkProvider(
            url=configuration.api_url,
            config=NetworkProviderConfig(requests_options={"timeout": API_TIMEOUT_SECONDS})
        )

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

    def claim_rewards(self, delegator: Account, staking_provider: Address) -> None:
        controller = self.network_entrypoint.create_delegation_controller()
        transaction = controller.create_transaction_for_claiming_rewards(
            sender=delegator,
            nonce=delegator.get_nonce_then_increment(),
            delegation_contract=staking_provider,
        )

        transaction_hash = self.network_entrypoint.send_transaction(transaction)
        self.network_entrypoint.await_transaction_completed
        # await processing started (?)
        # nope, better in bulk.


# condition: Callable[[AccountOnNetwork], bool] = lambda account: account.nonce > transaction.nonce
# self.network_provider.await_account_on_condition(transaction.sender, condition, self.awaiting_options)

# transaction_hash = self.transaction_computer.compute_transaction_hash(transaction).hex()
# transaction_on_network = self.network_provider.get_transaction(transaction_hash)

# print(f"    ✓ Processing started: {self.configuration.view_url.replace('{hash}', transaction_hash)}")
