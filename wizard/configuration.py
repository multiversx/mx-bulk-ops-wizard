import os
from dataclasses import dataclass

DEFAULT_MAINNET_PROXY_URL = "https://gateway.multiversx.com"
DEFAULT_MAINNET_API_URL = "https://api.multiversx.com"
DEFAULT_MAINNET_DEEP_HISTORY_URL = DEFAULT_MAINNET_PROXY_URL
ENV_MAINNET_PROXY_URL = os.environ.get("MAINNET_PROXY_URL")
ENV_MAINNET_API_URL = os.environ.get("MAINNET_API_URL")
ENV_MAINNET_DEEP_HISTORY_URL = os.environ.get("MAINNET_DEEP_HISTORY_URL")

DEFAULT_DEVNET_PROXY_URL = "https://devnet-gateway.multiversx.com"
DEFAULT_DEVNET_API_URL = "https://devnet-api.multiversx.com"
DEFAULT_DEVNET_DEEP_HISTORY_URL = DEFAULT_DEVNET_PROXY_URL
ENV_DEVNET_PROXY_URL = os.environ.get("DEVNET_PROXY_URL")
ENV_DEVNET_API_URL = os.environ.get("DEVNET_API_URL")
ENV_DEVNET_DEEP_HISTORY_URL = os.environ.get("DEVNET_DEEP_HISTORY_URL")

DEFAULT_TESTNET_PROXY_URL = "https://testnet-gateway.multiversx.com"
DEFAULT_TESTNET_API_URL = "https://testnet-api.multiversx.com"
DEFAULT_TESTNET_DEEP_HISTORY_URL = DEFAULT_TESTNET_PROXY_URL
ENV_TESTNET_PROXY_URL = os.environ.get("TESTNET_PROXY_URL")
ENV_TESTNET_API_URL = os.environ.get("TESTNET_API_URL")
ENV_TESTNET_DEEP_HISTORY_URL = os.environ.get("TESTNET_DEEP_HISTORY_URL")


@dataclass
class Configuration:
    chain_id: str
    proxy_url: str
    api_url: str
    deep_history_url: str
    explorer_url: str
    legacy_delegation_contract: str
    system_governance_contract: str
    cosigner_url: str
    liquid_staking_contracts: list[str]


CONFIGURATIONS = {
    "mainnet": Configuration(
        chain_id="1",
        proxy_url=ENV_MAINNET_PROXY_URL or DEFAULT_MAINNET_PROXY_URL,
        api_url=ENV_MAINNET_API_URL or DEFAULT_MAINNET_API_URL,
        deep_history_url=ENV_MAINNET_DEEP_HISTORY_URL or DEFAULT_MAINNET_DEEP_HISTORY_URL,
        explorer_url="https://explorer.multiversx.com",
        legacy_delegation_contract="erd1qqqqqqqqqqqqqpgqxwakt2g7u9atsnr03gqcgmhcv38pt7mkd94q6shuwt",
        system_governance_contract="erd1qqqqqqqqqqqqqqqpqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqrlllsrujgla",
        cosigner_url="https://tools.multiversx.com",
        liquid_staking_contracts=["erd1qqqqqqqqqqqqqpgq2khda0rx207gvlqg92dq5rh0z03a8dqf78ssu0qlcc", "erd1qqqqqqqqqqqqqpgqdnpmeseu3j5t7grds9dfj8ttt70pev66ah0sydkq9x"]
    ),
    "devnet": Configuration(
        chain_id="D",
        proxy_url=ENV_DEVNET_PROXY_URL or DEFAULT_DEVNET_PROXY_URL,
        api_url=ENV_DEVNET_API_URL or DEFAULT_DEVNET_API_URL,
        deep_history_url=ENV_DEVNET_DEEP_HISTORY_URL or DEFAULT_DEVNET_DEEP_HISTORY_URL,
        explorer_url="https://devnet-explorer.multiversx.com",
        legacy_delegation_contract="erd1qqqqqqqqqqqqqpgq97wezxw6l7lgg7k9rxvycrz66vn92ksh2tssxwf7ep",
        system_governance_contract="erd1qqqqqqqqqqqqqqqpqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqrlllsrujgla",
        cosigner_url="https://devnet-tools.multiversx.com",
        liquid_staking_contracts=[],
    ),
    "testnet": Configuration(
        chain_id="T",
        proxy_url=ENV_TESTNET_PROXY_URL or DEFAULT_TESTNET_PROXY_URL,
        api_url=ENV_TESTNET_API_URL or DEFAULT_TESTNET_API_URL,
        deep_history_url=ENV_TESTNET_DEEP_HISTORY_URL or DEFAULT_TESTNET_DEEP_HISTORY_URL,
        explorer_url="https://testnet-explorer.multiversx.com",
        legacy_delegation_contract="erd1qqqqqqqqqqqqqpgq97wezxw6l7lgg7k9rxvycrz66vn92ksh2tssxwf7ep",
        system_governance_contract="erd1qqqqqqqqqqqqqqqpqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqrlllsrujgla",
        cosigner_url="https://testnet-tcs-api.multiversx.com",
        liquid_staking_contracts=[],
    ),
}
