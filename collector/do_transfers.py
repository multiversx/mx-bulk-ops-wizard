import json
import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path

from multiversx_sdk import Address
from rich import print

from collector import errors, ux
from collector.accounts import AccountWrapper, load_accounts
from collector.configuration import CONFIGURATIONS
from collector.entrypoint import MyEntrypoint
from collector.guardians import AuthApp
from collector.transactions import TransactionWrapper
from collector.transfers import Transfer


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
    parser.add_argument("--infile", required=True, help="collection instructions (see 'collect_rewards.py')")
    parser.add_argument("--receiver", required=True, help="the unique receiver")
    parser.add_argument("--auth", required=True, help="auth registration file")

    args = parser.parse_args(cli_args)

    network = args.network
    configuration = CONFIGURATIONS[network]
    entrypoint = MyEntrypoint(configuration)
    accounts_wrappers = load_accounts(Path(args.wallets))
    infile = args.infile
    infile_path = Path(infile).expanduser().resolve()
    receiver = Address.new_from_bech32(args.receiver)
    auth_app = AuthApp.new_from_registration_file(Path(args.auth)) if args.auth else AuthApp([])

    accounts_wrappers_by_addresses: dict[str, AccountWrapper] = {
        item.account.address.to_bech32(): item for item in accounts_wrappers
    }

    json_content = infile_path.read_text()
    data = json.loads(json_content)
    transfers = [Transfer.new_from_dictionary(item) for item in data]

    entrypoint.recall_nonces(accounts_wrappers)
    entrypoint.recall_guardians(accounts_wrappers)
    transactions_wrappers: list[TransactionWrapper] = []

    ux.show_message("Creating and signing transactions...")

    for transfer in transfers:
        sender = accounts_wrappers_by_addresses[transfer.sender.to_bech32()]
        transaction = entrypoint.transfer_value(sender, receiver, transfer.amount)
        transactions_wrappers.append(TransactionWrapper(transaction, transfer.label))

    ux.confirm_continuation(f"Ready to transfer rewards, by sending [green]{len(transactions_wrappers)}[/green] transactions?")
    entrypoint.send_multiple(auth_app, transactions_wrappers)


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
