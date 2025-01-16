import logging
import time
import typing as tp

import pandas as pd
from solana.constants import LAMPORTS_PER_SOL

from utils.indexer_postgres_client import IndexerPostgresClient
from utils.logger import Logger
from .operator_accounts_model import OperatorAccountsModel
from .. import parent_logger


T = tp.TypeVar("T")

logger: Logger
RETRY_ATTEMPTS = 11


def fetch_data(
    operators: list[OperatorAccountsModel],
    from_slot: int,
    to_slot: int,
    db: IndexerPostgresClient,
):
    global logger
    logger = logging.getLogger(f"{parent_logger.name}.{__name__}")
    logger.info(f"Fetch Operator balance data from slot {from_slot} to slot {to_slot} from Indexer DB")

    # Get Operator gas data from Indexer
    all_operator_names = []

    all_rows = []
    for operator in operators:
        rows = db.get_operator_gas_data(
            keys=operator.accounts,
            from_slot=from_slot,
            to_slot=to_slot,
            operator_name=operator.name,
        )
        all_rows.extend(rows)
        all_operator_names.extend([operator.name] * len(rows))

    df = pd.DataFrame({
        "operator": all_operator_names,
        "sol_key": [row["operator"] for row in all_rows],
        "sol_sig": [row["sol_sig"] for row in all_rows],
        "block_slot": [row["block_slot"] for row in all_rows],
        "block_time": [row["block_time"] for row in all_rows],
        "sol_spent": [row["sol_spent"] for row in all_rows],
        "gas_price": [int(row["gas_price"], 16) for row in all_rows],
        "neon_gas_used": [row["neon_gas_used"] for row in all_rows],
        "idx": [row["idx"] for row in all_rows],
        "inner_idx": [row["inner_idx"] for row in all_rows],
    })

    # Validate the data set
    duplicates = (df[df.duplicated()].sort_values(by="sol_sig")).reset_index(drop=True)
    if not duplicates.empty:
        duplicates.to_csv(f"duplicates_{time.time()}.csv")

    with pd.option_context('display.max_rows', None, 'display.max_columns', None):
        assert duplicates.empty, f"Data contains duplicates: {duplicates.head(100)}"
        msg = f"Data has missing values:\n{df[df.isna().any(axis=1)].head(100)}"
        assert not df.drop(columns=['inner_idx']).isna().any().any(), msg

    df = df.sort_values(by=["operator", "sol_key", "block_time"]).reset_index(drop=True)

    # Add expense_SOL and deposit_NEON
    df["expense_SOL"] = df["sol_spent"] / LAMPORTS_PER_SOL
    df["deposit_NEON"] = df["neon_gas_used"] * df["gas_price"] / LAMPORTS_PER_SOL / LAMPORTS_PER_SOL

    # df = pd.read_csv("data_dump_solana_1730329652.559328.csv")

    if df.empty:
        raise Exception(f"No transactions found between slots {from_slot} and {to_slot}")

    # Convert timestamp to datetime and add column "date" for daily aggregation
    df["block_time"] = pd.to_datetime(df["block_time"], unit="s", utc=True)
    df["date"] = df["block_time"].dt.date

    dump_file = f"data_dump_{time.time()}.csv"
    logger.info(f"Dump data to {dump_file}")
    df.to_csv(dump_file, index=False, header=True)

    return df
