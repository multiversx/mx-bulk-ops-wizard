import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path
from typing import List

from multiversx_sdk import VoteType
from multiversx_sdk.gas_estimator.errors import GasLimitEstimationError
from rich import print

from wizard import errors, ux
from wizard.accounts import load_accounts
from wizard.configuration import CONFIGURATIONS
from wizard.constants import DEFAULT_GAS_PRICE
from wizard.entrypoint import MyEntrypoint
from wizard.guardians import AuthApp
from wizard.transactions import TransactionWrapper


def get_vote_type_from_args(choice: str) -> VoteType:
    return {
        "yes": VoteType.YES,
        "no": VoteType.NO,
        "abstain": VoteType.ABSTAIN,
        "veto": VoteType.VETO
    }[choice]


def main(cli_args: list[str] = sys.argv[1:]):
    try:
        _do_main(cli_args)
    except errors.KnownError as err:
        ux.show_critical_error(traceback.format_exc())
        ux.show_critical_error(err.get_pretty())
        return 1


def _do_main(cli_args: List[str]):
    parser = ArgumentParser()
    parser.add_argument("--network", choices=CONFIGURATIONS.keys(), required=True, help="network name")
    parser.add_argument("--wallets", required=True, help="path to wallets configuration file")
    parser.add_argument("--auth", required=True, help="auth registration file")
    parser.add_argument("--gas-price", type=int, default=DEFAULT_GAS_PRICE, help="min gas price")
    parser.add_argument("--proposal", type=int, required=True, help="proposal nonce / id")
    parser.add_argument("--vote", choices=["yes", "no", "abstain", "veto"], required=True, help="vote choice")

    args = parser.parse_args(cli_args)

    network = args.network
    configuration = CONFIGURATIONS[network]
    entrypoint = MyEntrypoint(
        configuration=configuration,
        use_gas_estimator=True,
        gas_limit_multiplier=1.1,
    )

    accounts_wrappers = load_accounts(Path(args.wallets))
    auth_app = AuthApp.new_from_registration_file(Path(args.auth)) if args.auth else AuthApp([])

    entrypoint.recall_nonces(accounts_wrappers)
    entrypoint.recall_guardians(accounts_wrappers)

    transactions_wrappers: List[TransactionWrapper] = []

    proposal = args.proposal
    vote = get_vote_type_from_args(args.vote)
    gas_price = args.gas_price

    ux.confirm_continuation(
        f"Submit bulk votes on proposal [green]{proposal}[/green] with choice [green]{vote.value.upper()}[/green]?"
    )

    for account in accounts_wrappers:
        try:
            tx = entrypoint.vote_on_onchain_governance(
                sender=account,
                proposal=proposal,
                vote=vote,
                gas_price=gas_price,
            )

            transactions_wrappers.append(TransactionWrapper(tx, account.wallet_name))
        except GasLimitEstimationError as error:
            print(f"[yellow]{account.wallet_name}[/yellow]", account.account.address.to_bech32(), f"[red]{error.error}[/red]")

    ux.confirm_continuation(f"Ready to send [green]{len(transactions_wrappers)}[/green] transaction(s)?")
    entrypoint.send_multiple(auth_app, transactions_wrappers)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
