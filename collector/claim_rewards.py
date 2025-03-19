import sys
from argparse import ArgumentParser
from pathlib import Path

from collector import errors, ux
from collector.accounts_loader import load_accounts
from collector.configuration import CONFIGURATIONS
from collector.entrypoint import MyEntrypoint


def main(cli_args: list[str] = sys.argv[1:]):
    try:
        _do_main(cli_args)
    except errors.KnownError as err:
        ux.show_critical_error(err.get_pretty())
        return 1


def _do_main(cli_args: list[str]):
    parser = ArgumentParser()
    parser.add_argument("--network", choices=CONFIGURATIONS.keys(), required=True, help="network name")
    parser.add_argument("--wallets", required=True, help="path of the wallets configuration file")
    parser.add_argument("--threshold", type=int, default=0, help="claim rewards larger than this amount")
    args = parser.parse_args(cli_args)

    network = args.network
    configuration = CONFIGURATIONS[network]
    entrypoint = MyEntrypoint(configuration)
    accounts = load_accounts(Path(args.wallets))

    for account in accounts:
        pass

    # for each one, go to API, search for staking providers
    # for each, do claim transaction & wait it's processing at source / do all at once?


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
