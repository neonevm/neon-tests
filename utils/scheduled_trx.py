from dataclasses import dataclass

import rlp
from eth_utils import keccak, to_bytes
from rlp.sedes import big_endian_int, binary, Binary
import typing as tp


@dataclass
class ScheduledTrxEstimateRequest:
    from_address: str
    to_address: str
    data: bytes
    value: int = 0


class ScheduledTxRLP(rlp.Serializable):
    fields = [
        ("payer", Binary(min_length=20, max_length=20, allow_empty=False)),
        ("sender", Binary(min_length=20, max_length=20, allow_empty=True)),
        ("nonce", big_endian_int),
        ("index", big_endian_int),
        ("intent", binary),
        ("intent_call_data", binary),
        ("target", Binary(min_length=20, max_length=20, allow_empty=True)),
        ("call_data", binary),
        ("value", big_endian_int),
        ("chain_id", big_endian_int),
        ("gas_limit", big_endian_int),
        ("max_fee_per_gas", big_endian_int),
        ("max_priority_fee_per_gas", big_endian_int),
    ]


class ScheduledTransaction:
    DEFAULTS = {
        "intent": b"",
        "intent_call_data": b"",
        "call_data": b"",
        "value": 0,
        "chain_id": 112,
        "gas_limit": 3000000,
        "max_fee_per_gas": 3000000000,
        "max_priority_fee_per_gas": 2500000000,
    }

    FIELD_NAMES = [
        "payer",
        "sender",
        "nonce",
        "index",
        "intent",
        "intent_call_data",
        "target",
        "call_data",
        "value",
        "chain_id",
        "gas_limit",
        "max_fee_per_gas",
        "max_priority_fee_per_gas",
    ]

    def __init__(self, payer: tp.Union[bytes, str], sender, nonce, index, target: tp.Union[bytes, str, None], **kwargs):
        self.payer = payer if isinstance(payer, bytes) else to_bytes(hexstr=payer[2:])

        self.sender = sender or b""
        self.nonce = nonce
        self.index = index
        if target:
            self.target = target if isinstance(target, bytes) else to_bytes(hexstr=target[2:])
        else:
            self.target = b""
        for field, default_value in self.DEFAULTS.items():
            setattr(self, field, kwargs.get(field, default_value))

    @classmethod
    def from_estimate_result(cls, index, estimate_obj: ScheduledTrxEstimateRequest, estimate_result: dict, **kwargs):
        nonce = int(estimate_result["nonce"], 16)
        chain_id = int(estimate_result["chainId"], 16)
        max_fee_per_gas = int(estimate_result["maxFeePerGas"], 16)
        max_priority_fee_per_gas = int(estimate_result["maxPriorityFeePerGas"], 16)
        gas_limit = int(estimate_result["gasList"][index], 16)
        return cls(
            estimate_obj.from_address,
            None,
            nonce,
            index,
            estimate_obj.to_address,
            chain_id=chain_id,
            gas_limit=gas_limit,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=max_priority_fee_per_gas,
            call_data=estimate_obj.data,
            value=estimate_obj.value,
            **kwargs,
        )

    def encode(self):
        tx_data = {field: getattr(self, field) for field in self.FIELD_NAMES}
        tx = ScheduledTxRLP(**tx_data)
        type_byte, sub_type_byte = 0x7F, 0x01
        return bytes([type_byte, sub_type_byte]) + rlp.encode(tx)

    def hash(self):
        return keccak(self.encode())

    def get_serialized_node(self, child_index, success_limit):
        """
        Serialize and return the node as bytes with the following layout:
        - gas_limit: 32 bytes
        - value: 32 bytes
        - child_index: 2 bytes
        - success_limit: 2 bytes
        - tx_hash: 32 bytes
        """
        gas_limit_bytes = self.gas_limit.to_bytes(32, byteorder="big")
        value_bytes = self.value.to_bytes(32, byteorder="big")
        child_index_bytes = child_index.to_bytes(2, byteorder="little")
        success_limit_bytes = success_limit.to_bytes(2, byteorder="little")
        tx_hash_bytes = self.hash()

        return gas_limit_bytes + value_bytes + child_index_bytes + success_limit_bytes + tx_hash_bytes


class CreateTreeAccMultipleData:
    def __init__(self, nonce, max_fee_per_gas=3000000000, max_priority_fee_per_gas=2500000000):
        self.nonce = nonce.to_bytes(8, byteorder="big")
        if not isinstance(max_fee_per_gas, int):
            max_fee_per_gas = int(max_fee_per_gas, 16)
        if not isinstance(max_priority_fee_per_gas, int):
            max_priority_fee_per_gas = int(max_priority_fee_per_gas, 16)
        self.max_fee_per_gas = max_fee_per_gas.to_bytes(32, byteorder="big")
        self.max_priority_fee_per_gas = max_priority_fee_per_gas.to_bytes(32, byteorder="big")
        self.data = self.nonce + self.max_fee_per_gas + self.max_priority_fee_per_gas

    def add_trx(self, trx, child_index, success_limit):
        self.data += trx.get_serialized_node(child_index, success_limit)

    def get_data(self):
        return self.data
