import json
from pathlib import Path

from multiversx_sdk import Account

from collector.wallets_configuration import WalletsConfiguration


def load_accounts(wallets_configuration_file: Path) -> list[Account]:
    configuration = WalletsConfiguration.new_from_file(wallets_configuration_file)
    return []


def load_accounts_from_mnemonic() -> list[Account]:
    return []


def load_accounts_from_mnemonics() -> list[Account]:
    return []


def load_accounts_from_keystore() -> list[Account]:
    return []


def load_accounts_from_keystores() -> list[Account]:
    return []


def load_accounts_from_ledger() -> list[Account]:
    return []


if __name__ == "__main__":
    pass
