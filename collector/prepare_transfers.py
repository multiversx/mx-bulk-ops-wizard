import json
import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path

from rich import print

from collector import errors, ux
from collector.accounts import load_accounts
from collector.configuration import CONFIGURATIONS
from collector.entrypoint import MyEntrypoint
from collector.rewards import ReceivedRewardsOfAccount
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

    parser.add_argument("--threshold", type=int, default=0, help="transfer amounts larger than this amount")
    parser.add_argument("--infile", required=True, help="rewards summary (see output of 'collect_rewards.py')")
    parser.add_argument("--outfile", required=True, help="where to save the prepared transfers")

    args = parser.parse_args(cli_args)

    threshold = args.threshold
    infile = args.infile
    infile_path = Path(infile).expanduser().resolve()

    json_content = infile_path.read_text()
    data = json.loads(json_content)
    all_rewards = [ReceivedRewardsOfAccount.new_from_dictionary(item) for item in data]

    for rewards_of_account in all_rewards:
        address = rewards_of_account.address
        label = rewards_of_account.label
        rewards = rewards_of_account.rewards
        total_amount = sum([item.amount for item in rewards])

        if total_amount < threshold:
            continue

        print(address.to_bech32(), f"([yellow]{label}[/yellow])")
        print(f"\tAmount: [yellow]{format_amount(total_amount)} EGLD[/yellow]")


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
