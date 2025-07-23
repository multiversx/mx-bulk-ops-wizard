import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path

from rich import print

from wizard import errors, ux
from wizard.accounts import load_accounts
from wizard.configuration import CONFIGURATIONS
from wizard.constants import DEFAULT_GAS_PRICE
from wizard.entrypoint import MyEntrypoint
from wizard.guardians import AuthApp
from wizard.transactions import TransactionWrapper
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
    parser.add_argument("--network", choices=CONFIGURATIONS.keys(), required=True, help="network name")
    parser.add_argument("--wallets", required=True, help="path of the wallets configuration file")
    parser.add_argument("--threshold", type=int, default=0, help="claim rewards larger than this amount")
    parser.add_argument("--gas-price", type=int, default=DEFAULT_GAS_PRICE, help="gas price")
    parser.add_argument("--auth", required=True, help="auth registration file")
    args = parser.parse_args(cli_args)

    network = args.network
    configuration = CONFIGURATIONS[network]
    entrypoint = MyEntrypoint(configuration)
    accounts_wrappers = load_accounts(Path(args.wallets))
    threshold = args.threshold
    gas_price = args.gas_price
    auth_app = AuthApp.new_from_registration_file(Path(args.auth)) if args.auth else AuthApp([])

    entrypoint.recall_nonces(accounts_wrappers)
    entrypoint.recall_guardians(accounts_wrappers)
    transactions_wrappers: list[TransactionWrapper] = []

    ux.show_message("Looking for rewards to claim...")

    for account_wrapper in accounts_wrappers:
        account = account_wrapper.account
        address = account.address
        label = account_wrapper.wallet_name

        print(address.to_bech32(), f"([yellow]{account_wrapper.wallet_name}[/yellow])")

        claimable_rewards = entrypoint.get_claimable_rewards(address)

        for item in claimable_rewards:
            if item.amount < threshold:
                continue

            print(f"\tClaim {format_native_amount(item.amount)} from {item.staking_provider.to_bech32()}")
            transaction = entrypoint.claim_rewards(account_wrapper, item.staking_provider, gas_price)
            transactions_wrappers.append(TransactionWrapper(transaction, label))

    ux.confirm_continuation(f"Ready to claim rewards, by sending [green]{len(transactions_wrappers)}[/green] transactions?")
    entrypoint.send_multiple(auth_app, transactions_wrappers)


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
