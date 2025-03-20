import sys
import traceback
from argparse import ArgumentParser

from collector import errors, ux


def main(cli_args: list[str] = sys.argv[1:]):
    try:
        _do_main(cli_args)
    except errors.KnownError as err:
        ux.show_critical_error(traceback.format_exc())
        ux.show_critical_error(err.get_pretty())
        return 1


def _do_main(cli_args: list[str]):
    parser = ArgumentParser()

    # wallets, ...
    # json file as input

    args = parser.parse_args(cli_args)


if __name__ == "__main__":
    ret = main(sys.argv[1:])
    sys.exit(ret)
