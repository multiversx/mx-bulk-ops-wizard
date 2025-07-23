import json
import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path

from rich import print

from wizard import errors, ux
from wizard.accounts import load_accounts
from wizard.configuration import CONFIGURATIONS
from wizard.entrypoint import MyEntrypoint
from wizard.errors import UsageError
from wizard.rewards import ReceivedRewardsOfAccount
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
    parser.add_argument("--after-epoch", type=int, default=0, help="consider rewards received (claimed) after this epoch")
    parser.add_argument("--after-time", type=int, default=0, help="consider rewards received (claimed) after this timestamp")
    parser.add_argument("--outfile", required=True, help="where to save the rewards summary")
    args = parser.parse_args(cli_args)

    network = args.network
    configuration = CONFIGURATIONS[network]
    entrypoint = MyEntrypoint(configuration)
    accounts_wrappers = load_accounts(Path(args.wallets))
    after_epoch = args.after_epoch
    after_time = args.after_time
    outfile = args.outfile

    outfile_path = Path(outfile).expanduser().resolve()
    outfile_path.parent.mkdir(parents=True, exist_ok=True)

    if outfile_path.exists():
        raise UsageError("'output file' should not be an existing file")

    is_time_missing = not after_epoch and not after_time
    is_time_overconfigured = after_epoch and after_time
    if is_time_missing or is_time_overconfigured:
        raise UsageError("either 'after epoch' or 'after time' must be set")

    if after_epoch:
        after_time = entrypoint.get_start_of_epoch_timestamp(after_epoch)

    print(f"After epoch: [yellow]{after_epoch}[/yellow]")
    print(f"After timestamp: [yellow]{after_time} ({format_time(after_time)})[/yellow]")

    ux.show_message("Looking for previously received (claimed) rewards...")

    all_rewards: list[ReceivedRewardsOfAccount] = []

    for account_wrapper in accounts_wrappers:
        account = account_wrapper.account
        address = account.address
        rewards_of_account: ReceivedRewardsOfAccount = ReceivedRewardsOfAccount(address, account_wrapper.wallet_name, [])

        print(address.to_bech32(), f"([yellow]{account_wrapper.wallet_name}[/yellow])")

        rewards = entrypoint.get_claimed_rewards(address, after_time)
        rewards_of_account.rewards.extend(rewards)

        rewards = entrypoint.get_claimed_rewards_legacy(address, after_time)
        rewards_of_account.rewards.extend(rewards)

        rewards = entrypoint.get_received_staking_rewards(address, after_time)
        rewards_of_account.rewards.extend(rewards)

        rewards_of_account.sort_rewards()
        all_rewards.append(rewards_of_account)

    json_content = json.dumps([item.to_dictionary() for item in all_rewards], indent=4)
    outfile_path.write_text(json_content)

    ux.show_message(f"File saved: {outfile_path}")


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
