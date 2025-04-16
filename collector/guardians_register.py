import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path

from multiversx_sdk import Address
from rich import print
from rich.prompt import Confirm
from rich.rule import Rule

from collector import errors, ux
from collector.accounts import load_accounts
from collector.configuration import CONFIGURATIONS
from collector.entrypoint import MyEntrypoint
from collector.guardians import AuthApp


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
    parser.add_argument("--auth", required=True, help="auth registration entries (if exists, it will be updated in-place)")
    args = parser.parse_args(cli_args)

    network = args.network
    configuration = CONFIGURATIONS[network]
    entrypoint = MyEntrypoint(configuration)
    accounts_wrappers = load_accounts(Path(args.wallets))

    auth_path = Path(args.auth).expanduser().resolve()
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    auth_app = AuthApp.new_from_registration_file(auth_path) if auth_path.is_file() else AuthApp([])

    ux.show_message("Registering on cosigner service...")

    for account_wrapper in accounts_wrappers:
        account = account_wrapper.account
        address = account.address
        label = account_wrapper.wallet_name

        print(Rule())
        print(address.to_bech32(), f"([yellow]{label}[/yellow])")

        registration_entry = auth_app.get_registration_entry(address.to_bech32())
        guardian_data = entrypoint.get_guardian_data(address)

        if registration_entry:
            print(f"... registration entry [blue]already available[/blue], guardian = {registration_entry.guardian}")
            if not Confirm.ask("Re-register (to get a new guardian)?"):
                continue

        if guardian_data.is_guarded:
            print(f"... account is [blue]already guarded[/blue] by guardian = {guardian_data.active_guardian}")
            if not Confirm.ask("Re-register (to get a new guardian)?"):
                continue

        if guardian_data.pending_guardian:
            print(f"... account has a [blue]pending[/blue] guardian = {guardian_data.pending_guardian}")
            if not Confirm.ask("Re-register (to get a new guardian)?"):
                continue

        registration_entry = entrypoint.register_cosigner(auth_app, account_wrapper)
        guardian = Address.new_from_bech32(registration_entry.guardian)

        print(f"[green]Registered with guardian = {guardian}[/green]")

        # We save the file after each account.
        auth_app.export_to_registration_file(auth_path)
        ux.show_message(f"File saved: {auth_path}")


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
