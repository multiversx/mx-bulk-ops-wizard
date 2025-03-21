import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path

from rich import print

from collector import errors, ux
from collector.accounts import load_accounts
from collector.configuration import CONFIGURATIONS
from collector.entrypoint import MyEntrypoint
from collector.errors import UsageError
from collector.resources import ReceivedRewards
from collector.utils import format_time


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
    parser.add_argument("--threshold", type=int, default=0, help="collect rewards larger than this amount")
    parser.add_argument("--after-epoch", type=int, default=0, help="consider rewards received (claimed) after this epoch")
    parser.add_argument("--after-time", type=int, default=0, help="consider rewards received (claimed) after this timestamp")
    parser.add_argument("--outfile", required=True, help="where to save the prepared collection instructions")
    args = parser.parse_args(cli_args)

    network = args.network
    configuration = CONFIGURATIONS[network]
    entrypoint = MyEntrypoint(configuration)
    containers = load_accounts(Path(args.wallets))
    threshold = args.threshold
    after_epoch = args.after_epoch
    after_time = args.after_time

    is_time_missing = not after_epoch and not after_time
    is_time_overconfigured = after_epoch and after_time
    if is_time_missing or is_time_overconfigured:
        raise UsageError("either 'after epoch' or 'after time' must be set")

    if after_epoch:
        after_time = entrypoint.get_start_of_epoch_timestamp(after_epoch)

    print(f"After epoch: [yellow]{after_epoch}[/yellow]")
    print(f"After timestamp: [yellow]{after_time} ({format_time(after_time)})[/yellow]")

    ux.show_message("Looking for previously received (claimed) rewards...")

    all_rewards: list[ReceivedRewards] = []

    for container in containers:
        account = container.account
        address = account.address

        print(address.to_bech32(), f"([yellow]{container.wallet_name}[/yellow])")

        rewards = entrypoint.get_claimed_rewards(address, after_time)
        all_rewards.extend(rewards)

        rewards = entrypoint.get_claimed_rewards_legacy(address, after_time)
        all_rewards.extend(rewards)

        rewards = entrypoint.get_received_staking_rewards(address, after_time)
        all_rewards.extend(rewards)


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
