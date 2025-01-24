import logging

import psycopg2
from psycopg2.extras import DictCursor, DictRow
from tqdm import tqdm

from utils.logger import create_logger

QUERY_SLOT_RANGE_LIMIT = 500000


class IndexerPostgresClient:
    def __init__(self, host: str, db: str, user: str, password: str, port: int, log_level=logging.INFO):
        self.logger = create_logger(__name__, level=log_level)
        self.conn = psycopg2.connect(
            database=db,
            user=user,
            password=password,
            host=host,
            port=port,
        )

    def get_latest_block_slot(self, finalized: bool) -> int:
        query = """
            SELECT block_slot
            FROM solana_blocks
            WHERE is_finalized = %s
            AND is_active = TRUE
            ORDER BY block_time DESC
            LIMIT 1
        """
        with self.conn.cursor(name="fetch_latest_block_slot", cursor_factory=DictCursor) as cursor:
            self.logger.info("Fetch latest block_slot")
            cursor.execute(query, (finalized,))
            block_slot = cursor.fetchall()[0]["block_slot"]
        return block_slot

    def get_solana_block_time(self, block: int) -> int:
        query = """
            SELECT block_time
            FROM solana_blocks
            WHERE block_slot = %s
        """
        with self.conn.cursor(name="fetch_solana_block_time", cursor_factory=DictCursor) as cursor:
            self.logger.info(f"Fetch block {block} timestamp")
            cursor.execute(query, (block,))
            block_time = cursor.fetchall()[0]["block_time"]
        return block_time

    def get_operator_gas_data(
        self,
        keys: list[str],
        from_slot: int,
        to_slot: int,
        operator_name: str,
    ) -> list[DictRow]:
        select_query = """
            SELECT DISTINCT
                c.operator,
                c.sol_sig,
                b.block_slot,
                b.block_time,
                c.sol_spent,
                n.gas_price,
                s.neon_gas_used,
                s.idx,
                s.inner_idx
            FROM
                solana_transaction_costs c
            INNER JOIN
                neon_transactions n
                ON n.sol_sig = c.sol_sig
            INNER JOIN
                solana_neon_transactions s
                ON s.neon_sig = n.neon_sig
            INNER JOIN
                solana_blocks b
                ON c.block_slot = b.block_slot
            WHERE
                c.operator = ANY(%s)
                AND c.block_slot BETWEEN %s AND %s
                AND b.is_finalized = TRUE
                AND b.is_active = TRUE
        """

        count_query = f"""
            SELECT COUNT(*)
            FROM (
                {select_query}
            ) AS distinct_rows;
        """

        total_rows = 0
        with self.conn.cursor() as cursor:
            start = from_slot
            step = QUERY_SLOT_RANGE_LIMIT
            while start < to_slot:
                end = min(start + step, to_slot)
                self.logger.info(f"Fetch operator {operator_name} transaction count in slot range {start} to {end}")
                cursor.execute(count_query, (keys, start, end))
                total_rows += cursor.fetchone()[0]
                start = end + 1

        rows = []

        with self.conn.cursor(cursor_factory=DictCursor) as cursor:
            with tqdm(total=total_rows, desc=f"Fetching Operator {operator_name} gas data") as pbar:
                start = from_slot
                step = QUERY_SLOT_RANGE_LIMIT
                while start < to_slot:
                    end = min(start + step, to_slot)
                    cursor.execute(select_query, (keys, start, end))
                    batch = cursor.fetchall()
                    rows.extend(batch)
                    pbar.update(len(batch))
                    start = end + 1

        return rows
