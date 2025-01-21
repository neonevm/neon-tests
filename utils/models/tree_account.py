import json
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class TreeAccountTransaction:
    status: str
    result_hash: str
    transaction_hash: str
    gas_limit: str
    value: str
    child_transaction: int
    success_execute_limit: int
    parent_count: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TreeAccountTransaction":
        return cls(
            status=data["status"],
            result_hash=data["result_hash"],
            transaction_hash=data["transaction_hash"],
            gas_limit=data["gas_limit"],
            value=data["value"],
            child_transaction=data["child_transaction"],
            success_execute_limit=data["success_execute_limit"],
            parent_count=data["parent_count"],
        )

    def is_successful(self) -> bool:
        return self.status == "Success"

    def is_failed(self) -> bool:
        return self.status == "Failed"

    def is_skipped(self) -> bool:
        return self.status == "Skipped"


@dataclass
class TreeAccount:
    result: str
    status: str
    pubkey: str
    payer: str
    last_slot: int
    chain_id: int
    max_fee_per_gas: str
    max_priority_fee_per_gas: str
    balance: int
    last_index: int
    transactions: List[TreeAccountTransaction]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TreeAccount":
        transactions = [TreeAccountTransaction.from_dict(tx) for tx in data["value"]["transactions"]]
        value = data["value"]
        return cls(
            result=data["result"],
            status=value["status"],
            pubkey=value["pubkey"],
            payer=value["payer"],
            last_slot=value["last_slot"],
            chain_id=value["chain_id"],
            max_fee_per_gas=value["max_fee_per_gas"],
            max_priority_fee_per_gas=value["max_priority_fee_per_gas"],
            balance=int(value["balance"], 16),
            last_index=value["last_index"],
            transactions=transactions,
        )

    def all_transactions_successful(self) -> bool:
        return all(tx.status == "Success" for tx in self.transactions)

    def get_transaction_count(self) -> int:
        return len(self.transactions)

    def get_transaction_statuses(self) -> Dict[str, str]:
        return {tx.transaction_hash: tx.status for tx in self.transactions}
