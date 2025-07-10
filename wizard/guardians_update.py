import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path

from multiversx_sdk import Address
from rich import print
from rich.rule import Rule

from wizard import errors, ux
from wizard.accounts import AccountWrapper, load_accounts
from wizard.configuration import CONFIGURATIONS
from wizard.entrypoint import MyEntrypoint
from wizard.guardians import AuthApp
from wizard.transactions import TransactionWrapper


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
    parser.add_argument("--new-auth", required=True, help="auth registration file")
    args = parser.parse_args(cli_args)

    network = args.network
    configuration = CONFIGURATIONS[network]
    entrypoint = MyEntrypoint(configuration)
    accounts_wrappers = load_accounts(Path(args.wallets))
    new_auth_app = AuthApp.new_from_registration_file(Path(args.new_auth))
    empty_auth_app = AuthApp([])

    accounts_wrappers_by_addresses: dict[str, AccountWrapper] = {
        item.account.address.to_bech32(): item for item in accounts_wrappers
    }

    entrypoint.recall_nonces(accounts_wrappers)
    entrypoint.recall_guardians(accounts_wrappers)
    transactions_wrappers: list[TransactionWrapper] = []

    ux.show_message("Creating and signing 'set (update) guardian' transactions for all auth registration entries...")

    for entry in new_auth_app.get_all_entries():
        account_wrapper = accounts_wrappers_by_addresses.get(entry.get_address())
        if not account_wrapper:
            raise errors.UsageError(f"account (wallet) not found for registration entry {entry.get_address()}")

        account = account_wrapper.account
        address = account.address
        label = account_wrapper.wallet_name

        print(Rule())
        print(address.to_bech32(), f"([yellow]{label}[/yellow])")

        existing_guardian_data = entrypoint.get_guardian_data(address)

        if not existing_guardian_data.is_guarded:
            print(f"... account is [blue]not guarded[/blue], will be skipped")
            continue

        new_guardian = Address.new_from_bech32(entry.get_guardian())
        transaction = entrypoint.set_guardian(account_wrapper, new_guardian)
        transactions_wrappers.append(TransactionWrapper(transaction, label))

    ux.confirm_continuation(f"Ready to update guardians, by sending [green]{len(transactions_wrappers)}[/green] transactions?")
    entrypoint.send_multiple(empty_auth_app, transactions_wrappers)


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
