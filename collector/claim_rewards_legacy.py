import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path

from multiversx_sdk import Transaction
from rich import print

from collector import errors, ux
from collector.accounts import load_accounts
from collector.configuration import CONFIGURATIONS
from collector.constants import DEFAULT_GAS_PRICE
from collector.entrypoint import MyEntrypoint
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
    parser.add_argument("--threshold", type=int, default=0, help="claim rewards larger than this amount")
    parser.add_argument("--gas-price", type=int, default=DEFAULT_GAS_PRICE, help="claim rewards larger than this amount")
    args = parser.parse_args(cli_args)

    network = args.network
    configuration = CONFIGURATIONS[network]
    entrypoint = MyEntrypoint(configuration)
    accounts_wrappers = load_accounts(Path(args.wallets))
    threshold = args.threshold
    gas_price = args.gas_price

    entrypoint.recall_nonces([item.account for item in accounts_wrappers])
    transactions_wrappers: list[TransactionWrapper] = []

    ux.show_message("Looking for rewards to claim...")

    for account_wrapper in accounts_wrappers:
        account = account_wrapper.account
        address = account.address
        label = account_wrapper.wallet_name

        print(address.to_bech32(), f"([yellow]{label}[/yellow])")

        claimable_rewards = entrypoint.get_claimable_rewards_legacy(address)

        if claimable_rewards < threshold:
            continue

        print(f"\tClaim {format_amount(claimable_rewards)} EGLD from legacy delegation")
        transaction = entrypoint.claim_rewards_legacy(account, gas_price)
        transactions_wrappers.append(TransactionWrapper(transaction, label))

    ux.confirm_continuation(f"Ready to claim rewards, by sending [green]{len(transactions_wrappers)}[/green] transactions?")
    entrypoint.send_multiple(transactions_wrappers)


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
