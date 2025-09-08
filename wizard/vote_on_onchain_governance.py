import sys
import traceback
from argparse import ArgumentParser
from pathlib import Path
from typing import List

from rich import print

from wizard import errors, ux
from wizard.accounts import load_accounts
from wizard.configuration import CONFIGURATIONS
from wizard.constants import DEFAULT_GAS_PRICE
from wizard.entrypoint import MyEntrypoint
from wizard.guardians import AuthApp
from wizard.transactions import TransactionWrapper

from multiversx_sdk.core.address import Address
from multiversx_sdk.core.transactions_factory_config import TransactionsFactoryConfig
from multiversx_sdk.governance.governance_transactions_factory import GovernanceTransactionsFactory
from multiversx_sdk.governance.resources import VoteType
from multiversx_sdk.network_providers.proxy_network_provider import ProxyNetworkProvider


def _addr_from_bech32(b: str) -> Address:
    if hasattr(Address, "new_from_bech32"):
        return Address.new_from_bech32(b)
    if hasattr(Address, "from_bech32"):
        return Address.from_bech32(b)
    try:
        return Address(b)
    except Exception:
        raise errors.KnownError("Address bech32 constructor not found in this SDK.")

def _vote_enum(choice: str):
    try:
        return {"yes": VoteType.YES, "no": VoteType.NO, "abstain": VoteType.ABSTAIN}[choice]
    except AttributeError:
        return {"yes": getattr(VoteType, "yes"), "no": getattr(VoteType, "no"), "abstain": getattr(VoteType, "abstain")}[choice]


def main(cli_args: list[str] = sys.argv[1:]):
    try:
        _do_main(cli_args)
    except errors.KnownError as err:
        ux.show_critical_error(traceback.format_exc())
        ux.show_critical_error(err.get_pretty())
        return 1

def _do_main(cli_args: List[str]):
    parser = ArgumentParser()
    parser.add_argument("--network", choices=CONFIGURATIONS.keys(), required=True, help="network name")
    parser.add_argument("--wallets", required=True, help="path to wallets configuration file")
    parser.add_argument("--auth", required=True, help="auth registration file")
    parser.add_argument("--gas-price", type=int, default=DEFAULT_GAS_PRICE, help="min gas price")
    sub = parser.add_subparsers(dest="action", required=True)

    vote_p = sub.add_parser("vote", help="cast votes (bulk) for a proposal")
    vote_p.add_argument("--proposal", type=int, required=True, help="proposal nonce / id")
    vote_p.add_argument("--choice", choices=["yes", "no", "abstain"], required=True, help="vote choice")

    close_p = sub.add_parser("close", help="close a proposal")
    close_p.add_argument("--proposal", type=int, required=True, help="proposal nonce / id")

    propose_p = sub.add_parser("propose", help="create a new proposal")
    propose_p.add_argument("--commit-hash", required=True, help="commit hash for proposal content")
    propose_p.add_argument("--start-epoch", type=int, required=True, help="start vote epoch")
    propose_p.add_argument("--end-epoch", type=int, required=True, help="end vote epoch")
    propose_p.add_argument("--fee-egld", type=float, default=0.0, help="native EGLD amount to attach")

    clear_p = sub.add_parser("clear", help="clear ended proposals for given proposers")
    clear_p.add_argument("--proposers", nargs="+", required=True, help="list of bech32 proposer addresses")

    claim_p = sub.add_parser("claim-fees", help="claim accumulated governance fees")

    chgcfg_p = sub.add_parser("change-config", help="change governance configuration")
    chgcfg_p.add_argument("--proposal-fee", type=int, required=True, help="proposal fee (wei)")
    chgcfg_p.add_argument("--lost-proposal-fee", type=int, required=True, help="lost proposal fee (wei)")
    chgcfg_p.add_argument("--min-quorum", type=int, required=True, help="minimum quorum")
    chgcfg_p.add_argument("--min-veto-threshold", type=int, required=True, help="minimum veto threshold")
    chgcfg_p.add_argument("--min-pass-threshold", type=int, required=True, help="minimum pass threshold")

    args = parser.parse_args(cli_args)

    network = args.network
    configuration = CONFIGURATIONS[network]
    entrypoint = MyEntrypoint(configuration)

    proxy_url = getattr(configuration, "proxy", None) or getattr(configuration, "proxy_url", None)
    if not proxy_url:
        raise errors.KnownError("CONFIGURATION is missing 'proxy' URL.")
    provider = ProxyNetworkProvider(proxy_url)

    chain_id = getattr(configuration, "chain_id", None)
    if not chain_id:
        netcfg = provider.get_network_config()
        chain_id = getattr(netcfg, "chain_id", None)
        if not chain_id:
            raise errors.KnownError("Unable to resolve chain_id from provider network config.")

    try:
        cfg = TransactionsFactoryConfig(chain_id=chain_id, min_gas_price=args.gas_price)
    except TypeError:
        try:
            cfg = TransactionsFactoryConfig(chain_id, args.gas_price)
        except TypeError:
            cfg = TransactionsFactoryConfig(chain_id)
            if hasattr(cfg, "min_gas_price"):
                cfg.min_gas_price = args.gas_price

    optional_limits = {
        "gas_limit_for_vote": getattr(configuration, "gas_limit_for_vote", 6_000_000),
        "gas_limit_for_proposal": getattr(configuration, "gas_limit_for_proposal", 12_000_000),
        "gas_limit_for_closing_proposal": getattr(configuration, "gas_limit_for_closing_proposal", 6_000_000),
        "gas_limit_for_clear_proposals": getattr(configuration, "gas_limit_for_clear_proposals", 6_000_000),
        "gas_limit_for_claim_accumulated_fees": getattr(configuration, "gas_limit_for_claim_accumulated_fees", 6_000_000),
        "gas_limit_for_change_config": getattr(configuration, "gas_limit_for_change_config", 12_000_000),
    }
    for attr, val in optional_limits.items():
        if hasattr(cfg, attr):
            setattr(cfg, attr, val)

    try:
        factory = GovernanceTransactionsFactory(config=cfg)
    except TypeError:
        factory = GovernanceTransactionsFactory(cfg)

    accounts_wrappers = load_accounts(Path(args.wallets))
    auth_app = AuthApp.new_from_registration_file(Path(args.auth)) if args.auth else AuthApp([])

    entrypoint.recall_nonces(accounts_wrappers)
    entrypoint.recall_guardians(accounts_wrappers)

    transactions_wrappers: List[TransactionWrapper] = []

    if args.action == "vote":
        proposal = args.proposal
        vote = _vote_enum(args.choice)

        ux.confirm_continuation(
            f"Submit bulk votes on proposal [green]{proposal}[/green] with choice [green]{args.choice.upper()}[/green]?"
        )
        for aw in accounts_wrappers:
            tx = factory.create_transaction_for_voting(
                sender=aw.account.address,
                proposal_nonce=proposal,
                vote=vote,
            )
            transactions_wrappers.append(TransactionWrapper(tx, aw.wallet_name))

    elif args.action == "close":
        proposal = args.proposal
        ux.confirm_continuation(f"Closing proposal [green]{proposal}[/green]?")
        aw = accounts_wrappers[0]
        tx = factory.create_transaction_for_closing_proposal(
            sender=aw.account.address,
            proposal_nonce=proposal,
        )
        transactions_wrappers.append(TransactionWrapper(tx, aw.wallet_name))

    elif args.action == "propose":
        value = int(round(args.fee_egld * 10**18)) if hasattr(args, "fee_egld") else 0
        aw = accounts_wrappers[0]
        ux.confirm_continuation(
            f"Creating proposal with commit {args.commit_hash}, "
            f"epochs {args.start_epoch}→{args.end_epoch}, "
            f"value {args.fee_egld} EGLD. Continue?"
        )
        tx = factory.create_transaction_for_new_proposal(
            sender=aw.account.address,
            commit_hash=args.commit_hash,
            start_vote_epoch=args.start_epoch,
            end_vote_epoch=args.end_epoch,
            native_token_amount=value,
        )
        transactions_wrappers.append(TransactionWrapper(tx, aw.wallet_name))

    elif args.action == "clear":
        proposers = [_addr_from_bech32(b) for b in args.proposers]
        ux.confirm_continuation(f"Clear ended proposals for [green]{len(proposers)}[/green] proposer(s)?")
        aw = accounts_wrappers[0]
        tx = factory.create_transaction_for_clearing_ended_proposals(
            sender=aw.account.address,
            proposers=proposers,
        )
        transactions_wrappers.append(TransactionWrapper(tx, aw.wallet_name))

    elif args.action == "claim-fees":
        ux.confirm_continuation("Claim accumulated governance fees?")
        aw = accounts_wrappers[0]
        tx = factory.create_transaction_for_claiming_accumulated_fees(sender=aw.account.address)
        transactions_wrappers.append(TransactionWrapper(tx, aw.wallet_name))

    elif args.action == "change-config":
        ux.confirm_continuation(
        f"Changing governance configuration with values: "
        f"proposal_fee={args.proposal_fee}, lost_proposal_fee={args.lost_proposal_fee}, "
        f"min_quorum={args.min_quorum}, min_veto_threshold={args.min_veto_threshold}, "
        f"min_pass_threshold={args.min_pass_threshold}. Continue?"
    )
        aw = accounts_wrappers[0]
        tx = factory.create_transaction_for_changing_config(
            sender=aw.account.address,
            proposal_fee=args.proposal_fee,
            lost_proposal_fee=args.lost_proposal_fee,
            min_quorum=args.min_quorum,
            min_veto_threshold=args.min_veto_threshold,
            min_pass_threshold=args.min_pass_threshold,
        )
        transactions_wrappers.append(TransactionWrapper(tx, aw.wallet_name))

    else:
        raise errors.KnownError("Unknown action")

    ux.confirm_continuation(f"Ready to send [green]{len(transactions_wrappers)}[/green] transaction(s)?")
    entrypoint.send_multiple(auth_app, transactions_wrappers)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))