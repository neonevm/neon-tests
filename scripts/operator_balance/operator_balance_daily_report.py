import argparse
import datetime
import logging
import threading
import time
from pathlib import Path
import typing as tp

import pandas as pd
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from utils.indexer_postgres_client import IndexerPostgresClient
from utils.logger import Logger
from . import parent_logger
from utils import coingecko
from .resources.fetch_operator_balance_data import fetch_data
from .resources.cli_validators import existing_dir
from .resources.common_cli_arg_parser import get_common_cli_arg_parser


logger: Logger = logging.getLogger(f"{parent_logger.name}.{Path(__file__).name}")


def parse_args() -> argparse.Namespace:
    parser = get_common_cli_arg_parser()
    parser.add_argument("--from_slot", type=int, required=True, help="Oldest slot")
    parser.add_argument("--to_slot", type=int, required=True, help="Newest slot")
    parser.add_argument("--report_dir", type=existing_dir, default=Path(__file__).parent)

    known_args, _ = parser.parse_known_args()
    return known_args


def get_coin_prices(
    from_date: datetime.date,
    to_date: datetime.date,
) -> dict[tp.Literal["neon", "solana"], dict[datetime.date, float]]:
    coin_prices: dict[tp.Literal["neon", "solana"], dict[datetime.date, float]] = {
        "neon": {},
        "solana": {},
    }

    date = from_date
    total = ((to_date - from_date).days + 1) * len(coin_prices)
    with tqdm(total=total, desc="Fetching coin prices", position=0) as pbar:
        loggers = [logger, coingecko.logger]
        with logging_redirect_tqdm(loggers=loggers, tqdm_class=tqdm):
            while date <= to_date:
                for coin_id in coin_prices:
                    coin_price = coingecko.get_coin_price(date, coin_id, "usd")
                    coin_prices[coin_id][date] = coin_price
                    pbar.update()
                date += datetime.timedelta(days=1)

    return coin_prices


def render_csv_report(df: pd.DataFrame, report_dir: Path, first_slot: int, last_slot: int):
    title = f"Report from slot {first_slot} to slot {last_slot}"
    csv_file = report_dir / f"operator_daily_report_{time.time()}.csv"
    parent_logger.info(f"Save daily report to {csv_file}")
    csv_file.unlink(missing_ok=True)
    header = True

    for operator_name, group in df.groupby("operator"):
        total_expense_sol = group["expense_SOL"].sum()
        total_sol_diff_usd = group["expense_sol_USD"].sum()
        total_deposit_neon = group["deposit_NEON"].sum()
        total_deposit_neon_usd = group["deposit_neon_USD"].sum()
        total_diff_sol_usd_neon_usd = group["diff_expense_sol_deposit_neon_USD"].sum()
        total = pd.DataFrame(
            {
                "operator": [""],
                "date": ["TOTAL"],
                "expense_SOL": [total_expense_sol],
                "sol_price_USD": [""],
                "expense_sol_USD": [total_sol_diff_usd],
                "deposit_NEON": [total_deposit_neon],
                "neon_price_USD": [""],
                "deposit_neon_USD": [total_deposit_neon_usd],
                "diff_expense_sol_deposit_neon_USD": [total_diff_sol_usd_neon_usd],
            }
        )

        csv_df = pd.concat([group, total])

        # Convert all values to strings to avoid scientific notation
        for column in csv_df.columns.values:
            csv_df[column] = csv_df[column].astype(str)

        csv_data = csv_df.to_csv(header=header, index=False)

        with open(csv_file, "a") as f:
            if header:
                f.write(f"{title}\n")
            f.write(csv_data)
            f.write("\n")

        header = False


def main():
    args = parse_args()
    # args.from_slot = args.to_slot - int(1 * 60 * 60 / 0.4),  # TODO comment out

    log_level = getattr(logging, args.log_level)
    parent_logger.setLevel(log_level)
    coingecko.logger.setLevel(log_level)

    logger.debug(f"Args: {str(args.__dict__)}")

    # Start fetching and caching coin prices in the background
    db = IndexerPostgresClient(
        host=args.indexer_pg_host,
        db=args.indexer_pg_db,
        user=args.indexer_pg_user,
        password=args.indexer_pg_password,
        port=args.indexer_pg_port,
        log_level=parent_logger.level,
    )
    first_block_time = db.get_solana_block_time(args.from_slot)
    last_block_time = db.get_solana_block_time(args.to_slot)

    from_date = datetime.datetime.utcfromtimestamp(first_block_time).date()
    to_date = datetime.datetime.utcfromtimestamp(last_block_time).date()
    thread = threading.Thread(
        target=get_coin_prices,
        kwargs={"from_date": from_date, "to_date": to_date},
        daemon=True,
    )
    thread.start()

    # Fetch Operator balance data
    df = fetch_data(
        operators=args.operators,
        from_slot=args.from_slot,
        to_slot=args.to_slot,
        db=db,
    )

    first_slot = df["block_slot"].min()
    last_slot = df["block_slot"].max()

    # Aggregate data to daily sums by Operator and date
    daily_df = (
        df.groupby(["operator", "date"])
        .agg(
            {
                "expense_SOL": "sum",
                "deposit_NEON": "sum",
            }
        )
        .reset_index()
    )

    # Finish getting coin USD prices
    thread.join()

    # Add sol_price_USD and expense_sol_USD
    expense_sol_index = daily_df.columns.get_loc("expense_SOL")
    sol_prices_per_date = []

    for date in daily_df["date"]:
        sol_price_per_date = coingecko.get_coin_price(date, "solana", "usd")
        sol_prices_per_date.append(sol_price_per_date)

    daily_df.insert(
        loc=expense_sol_index + 1,
        column="sol_price_USD",
        value=sol_prices_per_date,
    )
    daily_df.insert(
        loc=expense_sol_index + 2,
        column="expense_sol_USD",
        value=daily_df["expense_SOL"] * daily_df["sol_price_USD"],
    )

    # Add neon_price_USD and deposit_neon_USD
    neon_prices_per_date = []

    for date in daily_df["date"]:
        neon_price_per_date = coingecko.get_coin_price(date, "neon", "usd")
        neon_prices_per_date.append(neon_price_per_date)

    daily_df["neon_price_USD"] = neon_prices_per_date
    daily_df["deposit_neon_USD"] = daily_df["deposit_NEON"] * daily_df["neon_price_USD"]

    # Add diff between expense SOL USD and deposit Neon USD
    daily_df["diff_expense_sol_deposit_neon_USD"] = daily_df["deposit_neon_USD"] - daily_df["expense_sol_USD"]

    render_csv_report(
        df=daily_df,
        report_dir=args.report_dir,
        first_slot=first_slot,
        last_slot=last_slot,
    )


if __name__ == "__main__":
    main()
