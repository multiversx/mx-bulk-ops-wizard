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

    entrypoint.recall_nonces(accounts_wrappers)
    entrypoint.recall_guardians(accounts_wrappers)
    transactions_wrappers: list[TransactionWrapper] = []

    ux.show_message("Creating and signing 'set guardian' transactions for all auth registration entries...")

    for entry in auth_app.get_all_entries():
        account_wrapper = accounts_wrappers_by_addresses.get(entry.get_address())
        if not account_wrapper:
            raise errors.UsageError(f"account (wallet) not found for registration entry {entry.get_address()}")

        account = account_wrapper.account
        address = account.address
        label = account_wrapper.wallet_name

        print(Rule())
        print(address.to_bech32(), f"([yellow]{label}[/yellow])")

        guardian_data = entrypoint.get_guardian_data(address)

        if guardian_data.is_guarded:
            print(f"... account is [blue]already guarded[/blue]")

            if guardian_data.active_guardian == entry.get_guardian():
                print(f"... active guardian is same as the one in the auth registration file")
            else:
                print(f"... active guardian [red]is not same[/red] as the one in the auth registration file (bad flow, please handle separately)")

            print("... please see: https://docs.multiversx.com/developers/built-in-functions/#setguardian")

            if not Confirm.ask("Re-set guardian (tricky, but might produce the expected results)?"):
                continue
        else:
            print(f"... not yet guarded")

        if guardian_data.pending_guardian:
            print(f"... account has a [blue]pending[/blue] guardian = {guardian_data.pending_guardian}")

            if guardian_data.pending_guardian == entry.get_guardian():
                print(f"... pending guardian is same as the one in the auth registration file")
            else:
                print(f"... pending guardian [red]is not same[/red] as the one in the auth registration file (bad flow, please handle separately)")

            print("... please see: https://docs.multiversx.com/developers/built-in-functions/#setguardian")

            if not Confirm.ask("Re-set guardian (tricky flow, might not work as expected / no-op on chain)?"):
                continue
        else:
            print(f"... no pending guardian")

        guardian = Address.new_from_bech32(entry.get_guardian())
        transaction = entrypoint.set_guardian(account_wrapper, guardian)
        transactions_wrappers.append(TransactionWrapper(transaction, label))

    ux.confirm_continuation(f"Ready to set guardians, by sending [green]{len(transactions_wrappers)}[/green] transactions?")
    entrypoint.send_multiple(auth_app, transactions_wrappers)


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
