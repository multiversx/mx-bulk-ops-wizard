import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path
from typing import List

from multiversx_sdk import VoteType
from rich import print

from wizard import errors, ux
from wizard.accounts import load_accounts
from wizard.configuration import CONFIGURATIONS
from wizard.constants import DEFAULT_GAS_PRICE
from wizard.entrypoint import MyEntrypoint
from wizard.governance import GovernanceRecord
from wizard.guardians import AuthApp
from wizard.transactions import TransactionWrapper
from wizard.utils import format_native_amount, format_time


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
    parser.add_argument("--contract", required=True, help="contract address")
    parser.add_argument("--proposal", type=int, required=True, help="proposal nonce / id")
    parser.add_argument("--vote", choices=["yes", "no", "abstain", "veto"], required=True, help="vote choice")

    args = parser.parse_args(cli_args)

    network = args.network
    configuration = CONFIGURATIONS[network]
    entrypoint = MyEntrypoint(
        configuration=configuration,
        # Gas estimator might not completely work in this context (on-chain governance via proxy contracts).
        use_gas_estimator=False,
    )

    accounts_wrappers = load_accounts(Path(args.wallets))
    auth_app = AuthApp.new_from_registration_file(Path(args.auth)) if args.auth else AuthApp([])

    contract = args.contract
    proposal = args.proposal
    vote = get_vote_type_from_args(args.vote)
    gas_price = args.gas_price

    proofs_path = Path("governance_proofs") / network / contract / f"{proposal}.json"
    governance_records_by_adresses = GovernanceRecord.load_many_from_proofs_file(proofs_path)

    entrypoint.recall_nonces(accounts_wrappers)
    entrypoint.recall_guardians(accounts_wrappers)

    transactions_wrappers: List[TransactionWrapper] = []

    ux.confirm_continuation(
        f"Submit bulk votes on proposal [green]{proposal}[/green] with choice [green]{vote.value.upper()}[/green]?"
    )

    for account_wrapper in accounts_wrappers:
        address = account_wrapper.account.address

        print(f"[yellow]{account_wrapper.wallet_name}[/yellow]", address.to_bech32())

        if address.to_bech32() not in governance_records_by_adresses:
            print(f"\t[red]has no voting power[/red]")
            continue

        record = governance_records_by_adresses[address.to_bech32()]
        print(f"\t[blue]has voting power[/blue]", format_native_amount(record.power))

        previous_vote = entrypoint.get_vote_via_liquid_staking(address, contract, proposal)
        if previous_vote:
            print(f"\tprevious vote at {format_time(previous_vote.timestamp)}:", previous_vote.vote_type)
            print(f"\t[red]has already voted![/red]")
            continue

        tx = entrypoint.vote_via_liquid_staking(
            sender=account_wrapper,
            contract=contract,
            proposal=proposal,
            vote=vote,
            power=record.power,
            proof=record.proof,
            gas_price=gas_price,
        )

        transactions_wrappers.append(TransactionWrapper(tx, account_wrapper.wallet_name))

    ux.confirm_continuation(f"Ready to send [green]{len(transactions_wrappers)}[/green] transaction(s)?")
    entrypoint.send_multiple(auth_app, transactions_wrappers)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
