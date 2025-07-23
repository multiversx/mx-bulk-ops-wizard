from functools import cache
from typing import Any

from multiversx_sdk import ApiNetworkProvider, NetworkProviderConfig
from multiversx_sdk.core.constants import \
    EGLD_IDENTIFIER_FOR_MULTI_ESDTNFT_TRANSFER

from wizard.configuration import Configuration
from wizard.constants import NETWORK_PROVIDER_TIMEOUT_SECONDS


class Currency:
    def __init__(self, token_identifier: str, name: str, decimals: int) -> None:
        self.token_identifier = token_identifier
        self.name = name
        self.decimals = decimals


class CurrencyProvider:
    def __init__(self, configuration: Configuration) -> None:
        self.configuration = configuration

        self.api_network_provider = ApiNetworkProvider(
            url=configuration.api_url,
            config=NetworkProviderConfig(requests_options={"timeout": NETWORK_PROVIDER_TIMEOUT_SECONDS})
        )

    def get_currency_name(self, token_identifier: str) -> str:
        return self._get_currency_metadata(token_identifier).name

    def get_currency_num_decimals(self, token_identifier: str) -> int:
        return self._get_currency_metadata(token_identifier).decimals

    @cache
    def _get_currency_metadata(self, token_identifier: str) -> Currency:
        if is_native_currency(token_identifier):
            return Currency(EGLD_IDENTIFIER_FOR_MULTI_ESDTNFT_TRANSFER, "EGLD", 18)

        data = self.api_network_provider.do_get_generic(url=f"tokens/{token_identifier}")
        name = data.get("name", token_identifier)
        decimals = int(data.get("decimals", 0))
        return Currency(token_identifier, name, decimals)


class OnlyNativeCurrencyProvider:
    def __init__(self) -> None:
        pass

    def get_currency_name(self, token_identifier: str) -> str:
        assert is_native_currency(token_identifier)
        return "EGLD"

    def get_currency_num_decimals(self, token_identifier: str) -> int:
        assert is_native_currency(token_identifier)
        return 18


def is_native_currency(token_identifier: str) -> bool:
    return token_identifier == "" or token_identifier == EGLD_IDENTIFIER_FOR_MULTI_ESDTNFT_TRANSFER
