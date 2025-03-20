import sys
import traceback
from argparse import ArgumentParser

from collector import errors, ux
from collector.configuration import CONFIGURATIONS
from collector.constants import ONE_DAY_IN_SECONDS


def main(cli_args: list[str] = sys.argv[1:]):
    try:
        _do_main(cli_args)
    except errors.KnownError as err:
        ux.show_critical_error(traceback.format_exc())
        ux.show_critical_error(err.get_pretty())
        return 1


def _do_main(cli_args: list[str]):
    parser = ArgumentParser()
    # parser.add_argument("--network", choices=CONFIGURATIONS.keys(), required=True, help="network name")
    # parser.add_argument("--wallets", required=True, help="path of the wallets configuration file")
    # parser.add_argument("--threshold", type=int, default=0, help="consider rewards larger than this amount")
    # parser.add_argument("--since-seconds-delegation", type=int, default=ONE_DAY_IN_SECONDS, help="consider rewards received after ")
    # parser.add_argument("--since-seconds-delegation-legacy", type=int, default=ONE_DAY_IN_SECONDS, help="...")
    # parser.add_argument("--since-seconds-staking", type=int, default=ONE_DAY_IN_SECONDS, help="...")
    args = parser.parse_args(cli_args)

    # time after?
    # after epoch?


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
