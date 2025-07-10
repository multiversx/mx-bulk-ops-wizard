import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path

from rich import print

from wizard import errors, ux
from wizard.accounts import load_accounts
from wizard.configuration import CONFIGURATIONS
from wizard.entrypoint import MyEntrypoint
from wizard.guardians import AuthApp


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
    parser.add_argument("--auth", required=False, help="auth registration file")
    args = parser.parse_args(cli_args)

    network = args.network
    configuration = CONFIGURATIONS[network]
    entrypoint = MyEntrypoint(configuration)
    accounts_wrappers = load_accounts(Path(args.wallets))
    auth_app = AuthApp.new_from_registration_file(Path(args.auth)) if args.auth else AuthApp([])

    ux.show_message(f"Getting guardians status...")

    for account_wrapper in accounts_wrappers:
        account = account_wrapper.account
        address = account.address
        label = account_wrapper.wallet_name

        print(address.to_bech32(), f"([yellow]{label}[/yellow])")

        registration_entry = auth_app.get_registration_entry(address.to_bech32())
        guardian_data = entrypoint.get_guardian_data(address)

        if registration_entry:
            print(f"\tAuth registration entry available, guardian = {registration_entry.get_guardian()}")
        else:
            print("\t[yellow]No auth registration entry available.[/yellow]")

        if guardian_data.is_guarded:
            print(f"\t[green]Guarded.[/green]")
        else:
            print("\tNot guarded.")

        if guardian_data.active_guardian:
            print(f"\t[blue]Active[/blue] guardian: {guardian_data.active_guardian}")
        else:
            print("\tNo active guardian.")

        if guardian_data.pending_guardian:
            print(f"\t[yellow]Pending[/yellow] guardian: {guardian_data.pending_guardian} (activation epoch = {guardian_data.pending_epoch})")
        else:
            print("\tNo pending guardian.")

        if registration_entry and guardian_data.active_guardian:
            if registration_entry.get_guardian() == guardian_data.active_guardian:
                print("\t[green]Active guardian and registered guardian match.[/green]")
            else:
                print("\t[red]Active guardian and registered guardian do not match![/red]")


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
