# coding: utf-8
"""
Created on 2022-08-29
@author: Eugeny Kurkovich
"""
from dataclasses import dataclass
from hashlib import sha256

from construct import Bytes, Int8ul, Struct
from eth_keys import keys as eth_keys
from sha3 import keccak_256
from solana._layouts.system_instructions import SYSTEM_INSTRUCTIONS_LAYOUT, InstructionType as SystemInstructionType
from solana.publickey import PublicKey
from solana.rpc import commitment
from solana.transaction import AccountMeta, Transaction, TransactionInstruction

ACCOUNT_INFO_LAYOUT = Struct(
    "type" / Int8ul,
    "ether" / Bytes(20),
    "nonce" / Int8ul,
    "trx_count" / Bytes(8),
    "balance" / Bytes(32),
    "code_account" / Bytes(32),
    "is_rw_blocked" / Int8ul,
    "ro_blocked_cnt" / Int8ul,
)


DEFAULT_UNITS = 500 * 1000
DEFAULT_HEAP_FRAME = 256 * 1024
DEFAULT_ADDITIONAL_FEE = 0
COMPUTE_BUDGET_ID: PublicKey = PublicKey("ComputeBudget111111111111111111111111111111")
SYSTEM_ADDRESS = "11111111111111111111111111111111"


@dataclass
class AccountInfo:
    ether: eth_keys.PublicKey
    code_account: PublicKey
    trx_count: int

    @staticmethod
    def from_bytes(data: bytes):
        cont = ACCOUNT_INFO_LAYOUT.parse(data)
        return AccountInfo(cont.ether, PublicKey(cont.code_account), cont.trx_count)


@dataclass
class SOLCommitmentState:
    """Bank states to solana query"""

    CONFIRMED: str = commitment.Confirmed
    FINALIZED: str = commitment.Finalized
    PROCESSED: str = commitment.Processed


class ComputeBudget:
    @staticmethod
    def request_units(units, additional_fee):
        return TransactionInstruction(
            program_id=COMPUTE_BUDGET_ID,
            keys=[],
            data=bytes.fromhex("00") + units.to_bytes(4, "little") + additional_fee.to_bytes(4, "little"),
        )

    @staticmethod
    def request_heap_frame(heap_frame):
        return TransactionInstruction(
            program_id=COMPUTE_BUDGET_ID, keys=[], data=bytes.fromhex("01") + heap_frame.to_bytes(4, "little")
        )


class TransactionWithComputeBudget(Transaction):
    def __init__(
        self, units=DEFAULT_UNITS, additional_fee=DEFAULT_ADDITIONAL_FEE, heap_frame=DEFAULT_HEAP_FRAME, *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        if units:
            self.instructions.append(ComputeBudget.request_units(units, additional_fee))
        if heap_frame:
            self.instructions.append(ComputeBudget.request_heap_frame(heap_frame))


class Trx:
    def __init__(self):
        self.nonce = None
        self.gasPrice = None
        self.gasLimit = None
        self.toAddress = None
        self.value = None
        self.callData = None
        self.v = None
        self.r = None
        self.s = None

    @classmethod
    def from_string(cls, s):
        t = Trx()
        (unpacked, data) = unpack(memoryview(s))
        (nonce, gasPrice, gasLimit, toAddress, value, callData, v, r, s) = unpacked
        t.nonce = get_int(nonce)
        t.gasPrice = get_int(gasPrice)
        t.gasLimit = get_int(gasLimit)
        t.toAddress = toAddress
        t.value = get_int(value)
        t.callData = callData
        t.v = get_int(v)
        t.r = get_int(r)
        t.s = get_int(s)
        return t

    def chain_id(self):
        # chainid*2 + 35  xxxxx0 + 100011   xxxx0 + 100010 +1
        # chainid*2 + 36  xxxxx0 + 100100   xxxx0 + 100011 +1
        return (self.v - 1) // 2 - 17

    def __str__(self):
        return pack(
            (
                self.nonce,
                self.gasPrice,
                self.gasLimit,
                self.toAddress,
                self.value,
                self.callData,
                self.v,
                self.r.to_bytes(32, "big") if self.r else None,
                self.s.to_bytes(32, "big") if self.s else None,
            )
        ).hex()

    def get_msg(self, chain_id=None):
        return pack(
            (
                self.nonce,
                self.gasPrice,
                self.gasLimit,
                self.toAddress,
                self.value,
                self.callData,
                chain_id or self.chain_id(),
                None,
                None,
            )
        )

    def hash(self, chain_id=None):
        trx = pack(
            (
                self.nonce,
                self.gasPrice,
                self.gasLimit,
                self.toAddress,
                self.value,
                self.callData,
                chain_id or self.chain_id(),
                None,
                None,
            )
        )
        return keccak_256(trx).digest()

    def sender(self):
        msg_hash = self.hash()
        sig = eth_keys.Signature(vrs=[1 if self.v % 2 == 0 else 0, self.r, self.s])
        pub = sig.recover_public_key_from_msg_hash(msg_hash)
        return pub.to_canonical_address().hex()


def unpack(data):
    ch = data[0]
    if ch <= 0x7F:
        return ch, data[1:]
    elif ch == 0x80:
        return None, data[1:]
    elif ch <= 0xB7:
        l = ch - 0x80
        return data[1 : 1 + l].tobytes(), data[1 + l :]
    elif ch <= 0xBF:
        lLen = ch - 0xB7
        l = int.from_bytes(data[1 : 1 + lLen], byteorder="big")
        return data[1 + lLen : 1 + lLen + l].tobytes(), data[1 + lLen + l :]
    elif ch == 0xC0:
        return (), data[1:]
    elif ch <= 0xF7:
        l = ch - 0xC0
        lst = list()
        sub = data[1 : 1 + l]
        while len(sub):
            (item, sub) = unpack(sub)
            lst.append(item)
        return lst, data[1 + l :]
    else:
        lLen = ch - 0xF7
        l = int.from_bytes(data[1 : 1 + lLen], byteorder="big")
        lst = list()
        sub = data[1 + lLen : 1 + lLen + l]
        while len(sub):
            (item, sub) = unpack(sub)
            lst.append(item)
        return lst, data[1 + lLen + l :]


def pack(data):
    if data is None:
        return (0x80).to_bytes(1, "big")
    if isinstance(data, str):
        return pack(data.encode("utf8"))
    elif isinstance(data, bytes):
        if len(data) <= 55:
            return (len(data) + 0x80).to_bytes(1, "big") + data
        else:
            l = len(data)
            lLen = (l.bit_length() + 7) // 8
            return (0xB7 + lLen).to_bytes(1, "big") + l.to_bytes(lLen, "big") + data
    elif isinstance(data, int):
        if data < 0x80:
            return data.to_bytes(1, "big")
        else:
            l = (data.bit_length() + 7) // 8
            return (l + 0x80).to_bytes(1, "big") + data.to_bytes(l, "big")
        pass
    elif isinstance(data, list) or isinstance(data, tuple):
        if len(data) == 0:
            return (0xC0).to_bytes(1, "big")
        else:
            res = bytearray()
            for d in data:
                res += pack(d)
            l = len(res)
            if l <= 55:
                return (l + 0xC0).to_bytes(1, "big") + res
            else:
                lLen = (l.bit_length() + 7) // 8
                return (lLen + 0xF7).to_bytes(1, "big") + l.to_bytes(lLen, "big") + res
    else:
        raise Exception("Unknown type {} of data".format(str(type(data))))


def get_int(a):
    if isinstance(a, int):
        return a
    if isinstance(a, bytes):
        return int.from_bytes(a, "big")
    if a is None:
        return a
    raise Exception("Invalid convertion from {} to int".format(a))


def create_account_with_seed(funding, base, seed, lamports, space, loder_id):
    loder_id = PublicKey(loder_id)
    data = SYSTEM_INSTRUCTIONS_LAYOUT.build(
        dict(
            instruction_type=SystemInstructionType.CREATE_ACCOUNT_WITH_SEED,
            args=dict(
                base=bytes(base),
                seed=dict(length=len(seed), chars=seed),
                lamports=lamports,
                space=space,
                program_id=bytes(loder_id),
            ),
        )
    )
    created = PublicKey(sha256(bytes(base) + bytes(seed, "utf8") + bytes(loder_id)).digest())
    return TransactionInstruction(
        keys=[
            AccountMeta(pubkey=funding, is_signer=True, is_writable=True),
            AccountMeta(pubkey=created, is_signer=False, is_writable=True),
            AccountMeta(pubkey=base, is_signer=True, is_writable=False),
        ],
        program_id=PublicKey(SYSTEM_ADDRESS),
        data=data,
    )
