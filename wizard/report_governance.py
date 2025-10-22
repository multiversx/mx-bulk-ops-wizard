import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path

from multiversx_sdk.smart_contracts.errors import SmartContractQueryError
from rich import print

from wizard import errors, ux
from wizard.accounts import load_accounts
from wizard.configuration import CONFIGURATIONS
from wizard.entrypoint import MyEntrypoint
from wizard.utils import format_native_amount, format_time


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
    parser.add_argument("--proposal", type=int, required=True, help="proposal nonce / id")

    args = parser.parse_args(cli_args)

    network = args.network
    configuration = CONFIGURATIONS[network]
    entrypoint = MyEntrypoint(configuration)
    accounts_wrappers = load_accounts(Path(args.wallets))
    proposal = args.proposal

    previous_votes_by_voter = entrypoint.get_onchain_delegated_votes(proposal, configuration.legacy_delegation_contract)

    for account_wrapper in accounts_wrappers:
        address = account_wrapper.account.address

        print(f"[yellow]{account_wrapper.wallet_name}[/yellow]", address.to_bech32())

        try:
            direct_voting_power = entrypoint.get_voting_power_on_onchain_governance(address)
        except SmartContractQueryError:
            direct_voting_power = 0

        voting_power_via_legacy_delegation = entrypoint.get_voting_power_via_legacy_delegation(address)

        previous_direct_votes = entrypoint.get_onchain_direct_votes(address, proposal)
        previous_votes_via_legacy_delegation = previous_votes_by_voter.get(address.to_bech32(), [])

        print("\t", "direct voting power", direct_voting_power)
        print("\t", "voting power via legacy delegation", voting_power_via_legacy_delegation)

        for vote in previous_direct_votes:
            print("\t", f"previous direct vote on {format_time(vote.timestamp)}:", vote.vote_type)
        for vote in previous_votes_via_legacy_delegation:
            print("\t", f"previous delegated vote (legacy delegation) on {format_time(vote.timestamp)}:", vote.vote_type)

        if direct_voting_power and not previous_direct_votes:
            print("\t", "[red]missing direct vote![/red]")
        if voting_power_via_legacy_delegation and not previous_votes_via_legacy_delegation:
            print("\t", "[red]missing delegated vote (legacy delegation)![/red]")


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
