import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path

from multiversx_sdk import Address
from rich import print

from collector import errors, ux
from collector.accounts import load_accounts
from collector.configuration import CONFIGURATIONS
from collector.entrypoint import MyEntrypoint
from collector.guardians import AuthApp
from collector.transactions import TransactionWrapper


def main(cli_args: list[str] = sys.argv[1:]):
    try:
        _do_main(cli_args)
    except errors.KnownError as err:
        ux.show_critical_error(traceback.format_exc())
        ux.show_critical_error(err.get_pretty())
        return 1


def _do_main(cli_args: list[str]):
    parser = ArgumentParser()
    parser.add_argument("--network", choices=CONFIGURATIONS.keys(), required=True, help="network name")
    parser.add_argument("--wallets", required=True, help="path of the wallets configuration file")
    args = parser.parse_args(cli_args)

    network = args.network
    configuration = CONFIGURATIONS[network]
    entrypoint = MyEntrypoint(configuration)
    auth_app = AuthApp([])
    accounts_wrappers = load_accounts(Path(args.wallets))

    ux.show_message("Looking for already guarded accounts...")

    for account_wrapper in accounts_wrappers:
        account = account_wrapper.account
        address = account.address
        label = account_wrapper.wallet_name

        account_on_network = entrypoint.proxy_network_provider.get_account(address)
        if account_on_network.is_guarded:
            raise errors.UsageError(f"account {label} ({address}) is already guarded; should be excluded beforehand")

    ux.show_message("Registering on cosigner service...")

    entrypoint.recall_nonces([item.account for item in accounts_wrappers])
    transactions_wrappers: list[TransactionWrapper] = []

    for account_wrapper in accounts_wrappers:
        account = account_wrapper.account
        address = account.address
        label = account_wrapper.wallet_name

        print(address.to_bech32(), f"([yellow]{label}[/yellow])")

        registration_entry = entrypoint.register_cosigner(auth_app, account_wrapper)
        guardian = Address.new_from_bech32(registration_entry.guardian)

        print("\tGuardian (to be set)", f"([yellow]{guardian.to_bech32()}[/yellow])")

        transaction = entrypoint.set_guardian(account, guardian)
        transactions_wrappers.append(TransactionWrapper(transaction, label))

    ux.confirm_continuation(f"Ready to set guardians, by sending [green]{len(transactions_wrappers)}[/green] transactions?")
    entrypoint.send_multiple(transactions_wrappers)


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
