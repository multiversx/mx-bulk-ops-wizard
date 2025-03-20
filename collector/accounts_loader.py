import json
from pathlib import Path

from multiversx_sdk import Account

from collector.errors import KnownError
from collector.wallets_configuration import (KeystoresWalletEntry,
                                             KeystoreWalletEntry,
                                             MnemonicWalletEntry,
                                             WalletsConfiguration)


def load_accounts(wallets_configuration_file: Path) -> list[Account]:
    configuration = WalletsConfiguration.new_from_file(wallets_configuration_file)
    accounts: list[Account] = []

    for entry in configuration.entries:
        if isinstance(entry, MnemonicWalletEntry):
            accounts.extend(load_accounts_from_mnemonic(entry))
        elif isinstance(entry, KeystoreWalletEntry):
            accounts.extend(load_accounts_from_keystore(entry))
        elif isinstance(entry, KeystoresWalletEntry):
            accounts.extend(load_accounts_from_keystores(entry))
        else:
            raise KnownError(f"unknown wallet entry: {entry.kind}")

    return accounts


def load_accounts_from_mnemonic(entry: MnemonicWalletEntry) -> list[Account]:
    print("Loading accounts from mnemonic...")

    if entry.mnemonic_path:
        mnemonic = Path(entry.mnemonic_path).expanduser().resolve().read_text()
        mnemonic = " ".join(mnemonic.split())
    else:
        mnemonic = entry.mnemonic

    assert mnemonic, "mnemonic must be set"

    accounts: list[Account] = []

    for index in entry.address_indices:
        account = Account.new_from_mnemonic(mnemonic, index)
        accounts.append(account)

    return accounts


def load_accounts_from_mnemonics() -> list[Account]:
    return []


def load_accounts_from_keystore(entry: KeystoreWalletEntry) -> list[Account]:
    return []


def load_accounts_from_keystores(entry: KeystoresWalletEntry) -> list[Account]:
    return []


def load_accounts_from_ledger() -> list[Account]:
    return []


if __name__ == "__main__":
    pass
