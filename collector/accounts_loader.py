from pathlib import Path

from multiversx_sdk import Account

from collector import ux
from collector.errors import BadConfigurationError, KnownError
from collector.wallets_configuration import (KeystoresWalletEntry,
                                             KeystoreWalletEntry,
                                             LedgerWalletEntry,
                                             MnemonicWalletEntry, WalletEntry,
                                             WalletsConfiguration)


def load_accounts(wallets_configuration_file: Path) -> list[Account]:
    configuration = WalletsConfiguration.new_from_file(wallets_configuration_file)
    accounts: list[Account] = []

    for index, entry in enumerate(configuration.entries):
        print(f"Loading accounts from wallet entry #{index}...")
        try:
            accounts.extend(load_accounts_from_wallet_entry(entry))
        except Exception as error:
            raise KnownError(f"could not load accounts from wallet entry #{index}", error)

    accounts = deduplicate_accounts(accounts)
    return accounts


def load_accounts_from_wallet_entry(entry: WalletEntry) -> list[Account]:
    if isinstance(entry, MnemonicWalletEntry):
        return load_accounts_from_mnemonic(entry)
    if isinstance(entry, KeystoreWalletEntry):
        return load_accounts_from_keystore(entry)
    if isinstance(entry, KeystoresWalletEntry):
        return load_accounts_from_keystores(entry)
    if isinstance(entry, LedgerWalletEntry):
        return load_accounts_from_ledger(entry)

    raise KnownError(f"unknown wallet entry: {entry.kind}")


def load_accounts_from_mnemonic(entry: MnemonicWalletEntry) -> list[Account]:
    print("Loading accounts from mnemonic...")

    mnemonic = entry.mnemonic
    mnemonic_file = entry.mnemonic_file
    address_indices = entry.address_indices or [0]

    is_mnemonic_missing = not mnemonic and not mnemonic_file
    is_mnemonic_overconfigured = mnemonic and mnemonic_file
    if is_mnemonic_missing or is_mnemonic_overconfigured:
        raise BadConfigurationError("either 'mnemonic' or 'mnemonic file' must be set")

    if mnemonic_file:
        mnemonic = Path(mnemonic_file).expanduser().resolve().read_text()
        mnemonic = " ".join(mnemonic.split())

    if not mnemonic:
        raise BadConfigurationError("mnemonic is empty")

    accounts: list[Account] = []

    for index in address_indices:
        account = Account.new_from_mnemonic(mnemonic, index)
        accounts.append(account)

        print(f"\t{account.address}")

    return accounts


def load_accounts_from_keystore(entry: KeystoreWalletEntry) -> list[Account]:
    file = entry.file
    password = entry.password
    password_file = entry.password_file
    address_indices = entry.address_indices

    if not file:
        raise BadConfigurationError("'file' must be set")

    is_password_missing = not password and not password_file
    is_password_overconfigured = password and password_file
    if is_password_missing or is_password_overconfigured:
        raise BadConfigurationError("either 'password' or 'password file' must be set")

    if password_file:
        password = Path(password_file).expanduser().resolve().read_text()

    if not password:
        raise BadConfigurationError("password is empty")

    file_path = Path(file).expanduser().resolve()
    accounts: list[Account] = []

    if address_indices:
        for index in address_indices:
            account = Account.new_from_keystore(file_path, password, index)
            accounts.append(account)

            print(f"\t{account.address}")
    else:
        # Maybe legacy keystores (with kind = secretKey)
        account = Account.new_from_keystore(file_path, password)
        accounts.append(account)

        print(f"\t{account.address}")

    return accounts


def load_accounts_from_keystores(entry: KeystoresWalletEntry) -> list[Account]:
    folder = entry.folder
    unique_password = entry.unique_password
    unique_password_file = entry.unique_password_file

    if not folder:
        raise BadConfigurationError("'folder' must be set")

    is_password_missing = not unique_password and not unique_password_file
    is_password_overconfigured = unique_password and unique_password_file
    if is_password_missing or is_password_overconfigured:
        raise BadConfigurationError("either 'unique password' or 'unique password file' must be set")

    if unique_password_file:
        unique_password = Path(unique_password_file).expanduser().resolve().read_text()

    if not unique_password:
        raise BadConfigurationError("password is empty")

    folder_path = Path(folder).expanduser().resolve()
    keystore_paths = folder_path.glob("*.json")
    accounts: list[Account] = []

    for path in keystore_paths:
        account = Account.new_from_keystore(path, unique_password)
        accounts.append(account)

        print(f"\t{account.address}")

    return accounts


def load_accounts_from_ledger(entry: LedgerWalletEntry) -> list[Account]:
    ux.show_warning("load_accounts_from_ledger() not yet implemented.")
    return []


def deduplicate_accounts(accounts: list[Account]) -> list[Account]:
    result: list[Account] = []
    addresses: set[str] = set()

    for account in accounts:
        address = account.address.to_bech32()

        if address in addresses:
            continue

        result.append(account)
        addresses.add(address)

    print(f"Deduplicated accounts: input = {len(accounts)}, output = {len(result)}.")

    return result


if __name__ == "__main__":
    pass
