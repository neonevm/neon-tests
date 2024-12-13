import argparse

from .cli_validators import parse_operators
from .operator_accounts_model import OperatorAccountsModel


def get_common_cli_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "--operators",
        type=parse_operators,
        required=True,
        help=f"json file with {OperatorAccountsModel.schema()}",
    )
    parser.add_argument("--indexer_pg_host", required=True)
    parser.add_argument("--indexer_pg_db", required=True)
    parser.add_argument("--indexer_pg_user", required=True)
    parser.add_argument("--indexer_pg_password", required=True)
    parser.add_argument("--indexer_pg_port", type=int, default=5432)
    parser.add_argument(
        "--log_level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    )

    return parser
