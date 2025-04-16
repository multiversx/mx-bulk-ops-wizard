import json
import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path

from rich import print

from collector import errors, ux
from collector.accounts import load_accounts
from collector.configuration import CONFIGURATIONS
from collector.constants import DEFAULT_GAS_PRICE
from collector.entrypoint import MyEntrypoint
from collector.governance import GovernanceRecord
from collector.guardians import AuthApp
from collector.transactions import TransactionWrapper
from collector.utils import format_amount


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
    parser.add_argument("--proofs", required=True, help="path of the proofs file")
    parser.add_argument("--proposal", type=int, default=1, help="vote")
    parser.add_argument("--choice", type=int, default=0, help="vote")
    parser.add_argument("--gas-price", type=int, default=DEFAULT_GAS_PRICE, help="gas price")
    parser.add_argument("--auth", required=False, help="auth registration file")
    args = parser.parse_args(cli_args)

    network = args.network
    configuration = CONFIGURATIONS[network]
    entrypoint = MyEntrypoint(configuration)
    accounts_wrappers = load_accounts(Path(args.wallets))
    proofs_path = Path(args.proofs).expanduser().resolve()
    proposal = args.proposal
    choice = args.choice
    gas_price = args.gas_price
    auth_app = AuthApp.new_from_registration_file(Path(args.auth)) if args.path else AuthApp([])

    ux.confirm_continuation(f"You chose to vote on proposal =y [green]{proposal}[/green], with choice = [green]{choice}[/green]. Continue?")

    ux.show_message("Loading proofs...")

    json_content = proofs_path.read_text()
    data = json.loads(json_content)
    records = [GovernanceRecord.new_from_dictionary(item) for item in data]

    records_by_adresses: dict[str, GovernanceRecord] = {
        item.address.to_bech32(): item for item in records
    }

    entrypoint.recall_nonces([item.account for item in accounts_wrappers])
    transactions_wrappers: list[TransactionWrapper] = []

    ux.show_message("Crafting transactions...")

    for account_wrapper in accounts_wrappers:
        account = account_wrapper.account
        address = account.address
        label = account_wrapper.wallet_name

        print(address.to_bech32(), f"([yellow]{account_wrapper.wallet_name}[/yellow])")

        if address.bech32() not in records_by_adresses:
            ux.show_warning("Not eligible for voting.")
            continue

        record = records_by_adresses[address.to_bech32()]
        print(f"\tVote with power {format_amount(record.power)}")

        transaction = entrypoint.vote_on_governance(
            sender=account,
            proposal=proposal,
            choice=choice,
            power=record.power,
            proof=record.proof,
            gas_price=gas_price
        )

        transactions_wrappers.append(TransactionWrapper(transaction, label))

    ux.confirm_continuation(f"Ready to vote, by sending [green]{len(transactions_wrappers)}[/green] transactions?")
    entrypoint.send_multiple(auth_app, transactions_wrappers)


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
