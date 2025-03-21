import sys
import traceback
from argparse import ArgumentParser

from collector import errors, ux
from collector.configuration import CONFIGURATIONS


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
    parser.add_argument("--what", choices=["delegation", "legacy-delegation", "staking"], required=True, help="which rewards to collect")
    parser.add_argument("--wallets", required=True, help="path of the wallets configuration file")
    parser.add_argument("--threshold", type=int, default=0, help="collect rewards larger than this amount")
    parser.add_argument("--after-epoch", type=int, default=0, help="consider rewards received (claimed) after this epoch")
    parser.add_argument("--after-time", type=int, default=0, help="consider rewards received (claimed) after this timestamp")
    parser.add_argument("--outfile", required=True, help="where to save the prepared collection instructions")
    args = parser.parse_args(cli_args)

    after_epoch = args.after_epoch
    after_time = args.after_time


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
