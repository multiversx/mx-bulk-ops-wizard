from multiversx_sdk import (Address, ApiNetworkProvider, DevnetEntrypoint,
                            MainnetEntrypoint, NetworkEntrypoint,
                            NetworkProviderConfig, TestnetEntrypoint)

from collector.configuration import Configuration
from collector.delegation import ClaimableRewards
from collector.errors import KnownError


class MyEntrypoint:
    def __init__(self, configuration: Configuration) -> None:
        self.network_entrypoint = NetworkEntrypoint(
            network_provider_url=configuration.proxy_url, network_provider_kind="proxy",
            chain_id=configuration.chain_id,
        )

        self.api_network_provider = ApiNetworkProvider(
            url=configuration.api_url,
            config=NetworkProviderConfig(requests_options={"timeout": 30})
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


def create_entrypoint(name: str) -> NetworkEntrypoint:
    if name == "mainnet":
        return MainnetEntrypoint()
    if name == "devnet":
        return DevnetEntrypoint()
    if name == "testnet":
        return TestnetEntrypoint()

    raise KnownError(f"unknown entrypoint name: {name}")
