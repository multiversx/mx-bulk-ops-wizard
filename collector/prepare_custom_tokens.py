import json
import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path

from multiversx_sdk import AddressComputer, TokenTransfer
from rich import print

from collector import errors, ux
from collector.accounts import load_accounts
from collector.configuration import CONFIGURATIONS
from collector.currencies import CurrencyProvider
from collector.entrypoint import MyEntrypoint
from collector.errors import UsageError
from collector.transfers import MyTransfer
from collector.utils import format_amount, format_time


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
    parser.add_argument("--token", required=True, help="token identifier (without nonce in case of )")
    parser.add_argument("--after-epoch", type=int, default=0, help="consider tokens received after this epoch")
    parser.add_argument("--threshold", type=int, default=0, help="transfer amounts larger than this amount")
    parser.add_argument("--outfile", required=True, help="where to save the prepared transfers")
    args = parser.parse_args(cli_args)

    network = args.network
    configuration = CONFIGURATIONS[network]
    entrypoint = MyEntrypoint(configuration)
    currency_provider = CurrencyProvider(configuration)
    accounts_wrappers = load_accounts(Path(args.wallets))
    token_identifier = args.token
    after_epoch = args.after_epoch
    threshold = args.threshold
    outfile = args.outfile

    outfile_path = Path(outfile).expanduser().resolve()
    outfile_path.parent.mkdir(parents=True, exist_ok=True)

    if outfile_path.exists():
        raise UsageError("'output file' should not be an existing file")

    print(f"After epoch: [yellow]{after_epoch}[/yellow]")

    all_transfers: list[MyTransfer] = []

    for account_wrapper in accounts_wrappers:
        account = account_wrapper.account
        address = account.address
        label = account_wrapper.wallet_name
        shard = AddressComputer().get_shard_of_address(address)

        print(address.to_bech32(), f"([yellow]{account_wrapper.wallet_name}[/yellow])")

        after_block_nonce = entrypoint.get_start_of_epoch_nonce(shard, after_epoch) if after_epoch else 0
        tokens = entrypoint.get_custom_tokens(address, token_identifier)

        for token in tokens:
            print(f"\t([yellow]{token.identifier}, {token.nonce}[/yellow])")

            amount = entrypoint.get_custom_token_balance(token, address, after_block_nonce)
            if amount < threshold:
                continue

            all_transfers.append(MyTransfer(address, label, TokenTransfer(token, amount)))

    total_amount = sum([item.token_transfer.amount for item in all_transfers])
    ux.show_message(f"Total amount: {format_amount(currency_provider, total_amount, token_identifier)}")

    json_content = json.dumps([item.to_dictionary(currency_provider) for item in all_transfers], indent=4)
    outfile_path.write_text(json_content)

    ux.show_message(f"File saved: {outfile_path}")


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
