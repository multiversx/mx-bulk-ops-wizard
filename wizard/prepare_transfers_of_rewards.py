import json
import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path

from multiversx_sdk import TokenTransfer
from rich import print

from wizard import errors, ux
from wizard.currencies import OnlyNativeCurrencyProvider
from wizard.errors import UsageError
from wizard.rewards import ReceivedRewardsOfAccount
from wizard.transfers import MyTransfer
from wizard.utils import format_native_amount


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

    currency_provider = OnlyNativeCurrencyProvider()
    threshold = args.threshold
    infile = args.infile
    outfile = args.outfile

    infile_path = Path(infile).expanduser().resolve()
    outfile_path = Path(outfile).expanduser().resolve()
    outfile_path.parent.mkdir(parents=True, exist_ok=True)

    if outfile_path.exists():
        raise UsageError("'output file' should not be an existing file")

    json_content = infile_path.read_text()
    data = json.loads(json_content)
    all_rewards = [ReceivedRewardsOfAccount.new_from_dictionary(item) for item in data]
    all_transfers: list[MyTransfer] = []

    for rewards_of_account in all_rewards:
        address = rewards_of_account.address
        label = rewards_of_account.label
        rewards = rewards_of_account.rewards
        amount = sum([item.amount for item in rewards])

        if amount < threshold:
            continue

        print(address.to_bech32(), f"([yellow]{label}[/yellow])")
        print(f"\tAmount: [yellow]{format_native_amount(amount)}[/yellow]")

        all_transfers.append(MyTransfer(address, label, TokenTransfer.new_from_native_amount(amount)))

    total_amount = sum([item.token_transfer.amount for item in all_transfers])
    ux.show_message(f"Total amount: {format_native_amount(total_amount)}")

    json_content = json.dumps([item.to_dictionary(currency_provider) for item in all_transfers], indent=4)
    outfile_path.write_text(json_content)

    ux.show_message(f"File saved: {outfile_path}")


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
