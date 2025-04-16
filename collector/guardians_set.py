import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path

from multiversx_sdk import Address
from rich import print
from rich.prompt import Confirm
from rich.rule import Rule

from collector import errors, ux
from collector.accounts import AccountWrapper, load_accounts
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
    parser.add_argument("--auth", required=True, help="auth registration file")
    args = parser.parse_args(cli_args)

    network = args.network
    configuration = CONFIGURATIONS[network]
    entrypoint = MyEntrypoint(configuration)
    accounts_wrappers = load_accounts(Path(args.wallets))
    auth_app = AuthApp.new_from_registration_file(Path(args.auth))

    accounts_wrappers_by_addresses: dict[str, AccountWrapper] = {
        item.account.address.to_bech32(): item for item in accounts_wrappers
    }

    entrypoint.recall_nonces([item.account for item in accounts_wrappers])
    transactions_wrappers: list[TransactionWrapper] = []

    ux.show_message("Creating and signing 'set guardian' transactions for all auth registration entries...")

    for entry in auth_app.get_all_entries():
        account_wrapper = accounts_wrappers_by_addresses.get(entry.address)
        if not account_wrapper:
            raise errors.UsageError(f"account (wallet) not found for registration entry {entry.address}")

        account = account_wrapper.account
        address = account.address
        label = account_wrapper.wallet_name

        print(Rule())
        print(address.to_bech32(), f"([yellow]{label}[/yellow])")

        guardian_data = entrypoint.get_guardian_data(address)

        if guardian_data.is_guarded:
            print(f"... account is [blue]already guarded[/blue]")

            if guardian_data.active_guardian == entry.guardian:
                print(f"... active guardian is same as the one in the auth registration file")
            else:
                print(f"... active guardian [red]is not same[/red] as the one in the auth registration file")

            if not Confirm.ask("Re-set guardian?"):
                continue

        if guardian_data.pending_guardian:
            print(f"... account has a [blue]pending[/blue] guardian = {guardian_data.pending_guardian}")

            if guardian_data.pending_guardian == entry.guardian:
                print(f"... pending guardian is same as the one in the auth registration file")
            else:
                print(f"... pending guardian [red]is not same[/red] as the one in the auth registration file")

            if not Confirm.ask("Re-set guardian?"):
                continue

        guardian = Address.new_from_bech32(entry.guardian)
        transaction = entrypoint.set_guardian(account, guardian)
        transactions_wrappers.append(TransactionWrapper(transaction, label))

    ux.confirm_continuation(f"Ready to set guardians, by sending [green]{len(transactions_wrappers)}[/green] transactions?")
    entrypoint.send_multiple(transactions_wrappers)


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
