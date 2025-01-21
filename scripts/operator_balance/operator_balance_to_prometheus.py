import argparse
import datetime
import logging
import threading
from pathlib import Path

import pandas as pd
import requests
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

from scripts.operator_balance import parent_logger
from utils import coingecko
from .operator_balance_daily_report import get_coin_prices
from .resources.common_cli_arg_parser import get_common_cli_arg_parser
from utils.indexer_postgres_client import IndexerPostgresClient
from utils.logger import Logger
from .resources.cli_validators import valid_url
from .resources.fetch_operator_balance_data import fetch_data


logger: Logger


def parse_args() -> argparse.Namespace:
    parser = get_common_cli_arg_parser()

    parser.add_argument("--prometheus_url", type=valid_url, required=True)
    parser.add_argument("--push_gateway_url", type=valid_url, required=True)
    parser.add_argument("--job", default="operator_balance")
    parser.add_argument(
        "--metrics",
        choices=["expense_SOL", "deposit_NEON", "expense_sol_USD", "deposit_neon_USD"],
        default=["expense_SOL", "deposit_NEON", "expense_sol_USD", "deposit_neon_USD"],
        nargs="+",
    )

    known_args, _ = parser.parse_known_args()
    return known_args


def get_metric_names(prometheus_url) -> list[str]:
    logger.info("Get metric names")
    response = requests.get(f"{prometheus_url}/api/v1/label/__name__/values")
    response.raise_for_status()
    metrics = response.json().get("data", [])
    return metrics


def get_prometheus_last_slot(prometheus_url: str) -> int:
    logger.info("Get Prometheus last slot")
    metric_names = get_metric_names(prometheus_url=prometheus_url)

    for metric_name in metric_names:
        if "deposit_neon" in metric_name.lower():
            response = requests.get(f"{prometheus_url}/api/v1/query", params={"query": metric_name})
            response.raise_for_status()
            result = response.json().get("data", {}).get("result", [])
            if result:
                last_slot = int(result[0]["metric"]["to_slot"])
                break
    else:
        last_slot = 0

    logger.info(f"Prometheus last slot: {last_slot}")
    return last_slot


def push_to_prometheus(
    df: pd.DataFrame,
    metrics: list[str],
    job: str,
    gateway_url: str,
    first_slot: int,
    last_slot: int,
):
    registry = CollectorRegistry()

    for operator, group in df.groupby("operator"):
        for metric_name in metrics:
            gauge_name = f"{metric_name}_{operator}"
            gauge = Gauge(
                name=gauge_name,
                documentation=f"{metric_name} for Operator {operator}",
                labelnames=["operator", "from_slot", "to_slot"],
                registry=registry,
            )

            label_value = group[metric_name].sum()
            logger.debug(f"Set gauge {gauge_name} value = {label_value}")
            gauge.labels(operator=operator, from_slot=first_slot, to_slot=last_slot).set(label_value)

    logger.info(f"Push registry to Prometheus job {job}")
    push_to_gateway(gateway_url, job=job, registry=registry)


def main():
    args = parse_args()

    log_level = getattr(logging, args.log_level)
    parent_logger.setLevel(log_level)

    global logger
    logger = logging.getLogger(f"{parent_logger.name}.{Path(__file__).name}")
    logger.debug(str(args.__dict__))

    db = IndexerPostgresClient(
        host=args.indexer_pg_host,
        db=args.indexer_pg_db,
        user=args.indexer_pg_user,
        password=args.indexer_pg_password,
        port=args.indexer_pg_port,
        log_level=parent_logger.level,
    )

    prometheus_last_slot = get_prometheus_last_slot(prometheus_url=args.prometheus_url)
    to_slot = db.get_latest_block_slot(finalized=True)
    from_slot = prometheus_last_slot + 1 if prometheus_last_slot else to_slot - int(0.25 * 60 * 60 / 0.4)  # ~15 min.

    # Start fetching and caching coin USD prices in the background
    first_block_time = db.get_solana_block_time(from_slot)
    last_block_time = db.get_solana_block_time(to_slot)
    from_date = datetime.datetime.utcfromtimestamp(first_block_time).date()
    to_date = datetime.datetime.utcfromtimestamp(last_block_time).date()
    thread = threading.Thread(
        target=get_coin_prices,
        kwargs={"from_date": from_date, "to_date": to_date},
        daemon=True,
    )
    thread.start()

    # Fetch Operator Balance Data
    df = fetch_data(
        operators=args.operators,
        from_slot=from_slot,
        to_slot=to_slot,
        db=db,
    )

    # Finish getting coin USD prices
    thread.join()

    # Add sol_price_USD and expense_sol_USD
    sol_prices_per_date: dict[datetime.date, float] = {}

    for date in df["date"].unique():
        sol_price_per_date = coingecko.get_coin_price(date, "solana", "usd")
        sol_prices_per_date[date] = sol_price_per_date

    df["sol_price_USD"] = [sol_prices_per_date[date] for date in df["date"]]
    df["expense_sol_USD"] = df["expense_SOL"] * df["sol_price_USD"]

    # Add neon_price_USD and deposit_neon_USD
    neon_prices_per_date: dict[datetime.date, float] = {}

    for date in df["date"].unique():
        neon_price_per_date = coingecko.get_coin_price(date, "neon", "usd")
        neon_prices_per_date[date] = neon_price_per_date

    df["neon_price_USD"] = [neon_prices_per_date[date] for date in df["date"]]
    df["deposit_neon_USD"] = df["deposit_NEON"] * df["neon_price_USD"]

    # Since some transactions don't have a timestamp, and are being ignored, from_slot and to_slot may change
    first_slot = df["block_slot"].min()
    last_slot = df["block_slot"].max()

    push_to_prometheus(
        df=df,
        metrics=args.metrics,
        job=args.job,
        gateway_url=args.push_gateway_url,
        first_slot=first_slot,
        last_slot=last_slot,
    )


if __name__ == "__main__":
    main()
