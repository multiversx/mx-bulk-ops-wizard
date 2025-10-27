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
from wizard.governance import GovernanceRecord
from wizard.utils import format_time


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

    governance_records_for_liquid_staking_contracts: dict[str, dict[str, GovernanceRecord]] = {}

    # Load previous votes, load governance records
    for contract in configuration.liquid_staking_contracts:
        proofs_path = Path("governance_proofs") / network / contract / f"{proposal}.json"
        governance_records_for_liquid_staking_contracts[contract] = GovernanceRecord.load_many_from_proofs_file(proofs_path)

    for account_wrapper in accounts_wrappers:
        address = account_wrapper.account.address

        print(f"[yellow]{account_wrapper.wallet_name}[/yellow]", address.to_bech32())

        try:
            direct_voting_power = entrypoint.get_direct_voting_power(address)
        except SmartContractQueryError:
            direct_voting_power = 0

        voting_power_via_legacy_delegation = entrypoint.get_voting_power_via_legacy_delegation(address)

        previous_direct_vote = entrypoint.get_direct_vote(address, proposal)
        previous_vote_via_legacy_delegation = entrypoint.get_vote_via_legacy_delegation(address, proposal)

        print("\t", "direct voting power", direct_voting_power)
        print("\t", "voting power via legacy delegation", voting_power_via_legacy_delegation)

        if previous_direct_vote:
            print("\t", f"previous direct vote on {format_time(previous_direct_vote.timestamp)}:", previous_direct_vote.vote_type)
        if previous_vote_via_legacy_delegation:
            print("\t", f"previous delegated vote (legacy delegation) on {format_time(previous_vote_via_legacy_delegation.timestamp)}:", previous_vote_via_legacy_delegation.vote_type)

        if direct_voting_power and not previous_direct_vote:
            print("\t", "[red]missing direct vote![/red]")
        if voting_power_via_legacy_delegation and not previous_vote_via_legacy_delegation:
            print("\t", "[red]missing delegated vote (legacy delegation)![/red]")

        for contract in configuration.liquid_staking_contracts:
            record = governance_records_for_liquid_staking_contracts[contract].get(address.to_bech32())
            previous_vote = entrypoint.get_vote_via_liquid_staking(address, contract, proposal)

            if record:
                print("\t", f"voting power via {contract}", record.power)

            if previous_vote:
                print("\t", f"previous delegated vote ({contract}) on {format_time(previous_vote.timestamp)}:", previous_vote.vote_type)

            if record and not previous_vote:
                print("\t", f"[red]missing delegated vote ({contract})![/red]")


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
