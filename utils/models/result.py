import typing as tp
from typing import List, Union

from pydantic import BaseModel, Field, model_validator

from utils.models.mixins import ForbidExtra
from integration.tests.basic.helpers.basic import NeonEventType
from integration.tests.basic.helpers.basic import NeonEventType, SolanaInstruction
from utils.models.model_types import (
    BalanceString,
    EstimateGasPriceString,
    FalseOnly,
    GasPriceString,
    HexString,
    IdField,
    JsonRPCString,
    NetVersionString,
    NonZeroBytesString,
    StorageString,
    ZeroBytesString,
)


class EthResult(ForbidExtra):
    jsonrpc: JsonRPCString
    id: IdField
    result: HexString


class NeonGetEvmParamsDetails(ForbidExtra):
    neonAccountSeedVersion: int
    neonMaxEvmStepsInLastIteration: int
    neonMinEvmStepsInIteration: int
    neonGasLimitMultiplierWithoutChainId: int
    neonHolderMessageSize: int
    neonPaymentToTreasury: int
    neonStorageEntriesInContractAccount: int
    neonTreasuryPoolCount: int
    neonTreasuryPoolSeed: str
    neonEvmProgramId: str


class NeonGetEvmParamsResult(EthResult):
    result: NeonGetEvmParamsDetails


class EthGasPriceResult(EthResult):
    result: GasPriceString


class EthGetBalanceResult(EthResult):
    result: BalanceString


class EthGetCodeResult(EthResult):
    result: NonZeroBytesString


class EthGetZeroCodeResult(EthResult):
    result: ZeroBytesString


class Web3ClientVersionResult(EthResult):
    result: str


class NetVersionResult(EthResult):
    result: NetVersionString


class EthGetStorageAt(EthResult):
    result: StorageString


class EthMiningResult(EthResult):
    result: bool


class SyncingFields(ForbidExtra):
    startingBlock: HexString
    currentBlock: HexString
    highestBlock: HexString


class EthSyncingResult(EthResult):
    result: Union[SyncingFields, FalseOnly]


class EthEstimateGas(EthResult):
    result: EstimateGasPriceString


class Transaction(BaseModel):
    blockHash: HexString
    blockNumber: HexString
    from_: HexString = Field(alias="from")
    gas: HexString
    gasPrice: HexString
    hash: HexString
    input: HexString
    nonce: HexString
    to: Union[HexString, None]
    transactionIndex: HexString
    value: HexString
    chainId: HexString
    v: HexString
    r: HexString
    s: HexString
    type: HexString


class EthGetBlockByHashDetails(ForbidExtra):
    number: Union[HexString, None]
    hash: Union[HexString, None]
    parentHash: HexString
    nonce: Union[HexString, None]
    sha3Uncles: HexString
    logsBloom: HexString
    transactionsRoot: HexString
    stateRoot: HexString
    receiptsRoot: HexString
    miner: tp.Optional[HexString]  # check with newer geth
    baseFeePerGas: tp.Optional[HexString] = None  # check with newer geth
    withdrawals: tp.Optional[List[HexString]] = None  # check with newer geth
    withdrawalsRoot: tp.Optional[HexString] = None  # check with newer geth
    difficulty: HexString
    totalDifficulty: Union[HexString, None]
    extraData: HexString
    size: HexString
    gasLimit: HexString
    gasUsed: HexString
    timestamp: HexString
    transactions: List[HexString]
    uncles: List[HexString]
    mixHash: HexString


class EthGetBlockByHashFullDetails(ForbidExtra):
    number: Union[HexString, None]
    hash: Union[HexString, None]
    parentHash: HexString
    nonce: Union[HexString, None]
    sha3Uncles: HexString
    logsBloom: HexString
    transactionsRoot: HexString
    stateRoot: HexString
    receiptsRoot: HexString
    miner: tp.Optional[HexString]  # check with newer geth
    baseFeePerGas: tp.Optional[HexString] = None  # check with newer geth
    withdrawals: tp.Optional[List[HexString]] = None  # check with newer geth
    withdrawalsRoot: tp.Optional[HexString] = None  # check with newer geth
    difficulty: HexString
    totalDifficulty: Union[HexString, None]
    extraData: HexString
    size: HexString
    gasLimit: HexString
    gasUsed: HexString
    timestamp: HexString
    transactions: List[Transaction]
    uncles: List[HexString]
    mixHash: HexString


class EthGetBlockByHashResult(EthResult):
    result: Union[EthGetBlockByHashDetails, None]


class EthGetBlockByHashFullResult(EthResult):
    result: Union[EthGetBlockByHashFullDetails, None]


class EthGetLogsDetails(ForbidExtra):
    removed: bool
    logIndex: Union[HexString, None]
    blockNumber: Union[HexString, None]
    blockHash: Union[HexString, None]
    transactionHash: Union[HexString, None]
    transactionIndex: Union[HexString, None]
    address: HexString
    data: Union[HexString, ZeroBytesString]
    topics: List[HexString]


class EthGetLogs(EthResult):
    result: List[EthGetLogsDetails]


class NeonGetLogsDetails(ForbidExtra):
    removed: bool
    logIndex: Union[HexString, None]
    blockNumber: Union[HexString, None]
    blockHash: Union[HexString, None]
    transactionHash: Union[HexString, None]
    transactionIndex: Union[HexString, None]
    address: Union[HexString, None]
    data: Union[HexString, ZeroBytesString]
    topics: List[HexString]
    solanaTransactionSignature: str
    solanaInstructionIndex: int
    solanaInnerInstructionIndex: Union[int, None]
    solanaAddress: Union[str, None]
    neonEventType: str
    neonEventLevel: int
    neonEventOrder: int
    neonIsHidden: bool
    neonIsReverted: bool


class NeonGetLogs(EthResult):
    result: List[NeonGetLogsDetails]


class EthGetBlockByNumberAndIndexResult(EthResult):
    result: Transaction


class EthGetBlockByNumberAndIndexNoneResult(EthResult):
    result: None


class ReceiptDetails(ForbidExtra):
    transactionHash: HexString
    transactionIndex: HexString
    blockHash: HexString
    blockNumber: HexString
    from_: HexString = Field(alias="from")
    to: Union[HexString, None]
    cumulativeGasUsed: HexString
    effectiveGasPrice: HexString
    gasUsed: HexString
    contractAddress: Union[HexString, None]
    logs: List[EthGetLogsDetails]
    logsBloom: HexString
    type: HexString
    status: tp.Optional[HexString] = None
    root: tp.Optional[HexString] = None

    @model_validator(mode="before")
    @classmethod
    def check_status(cls, values):
        if values.get("status") is None and values.get("root") is None:
            raise ValueError("Either status or root must be present")
        if values.get("status") is not None and values.get("root") is not None:
            raise ValueError("Either status or root must be present")
        return values


class EthGetTransactionReceiptResult(EthResult):
    result: ReceiptDetails


class EthGetTransactionByHashResult(EthResult):
    result: Transaction


class SolanaInstruction(ForbidExtra):
    solanaProgram: str
    solanaInstructionIndex: int
    solanaInnerInstructionIndex: Union[int, None]
    svmHeapSizeLimit: int
    svmCyclesLimit: int
    svmCyclesUsed: int
    neonInstructionCode: int
    neonInstructionName: str
    neonEvmSteps: int
    neonTotalEvmSteps: int
    neonGasUsed: int
    neonTotalGasUsed: int
    neonTransactionFee: int
    neonMiner: Union[HexString, None]
    neonLogs: List[NeonGetLogsDetails]


class SolanaTransaction(ForbidExtra):
    solanaTransactionSignature: str
    solanaTransactionIsSuccess: bool
    solanaBlockSlot: int
    solanaLamportExpense: int
    neonOperatorAddress: str
    solanaInstructions: List[SolanaInstruction]


class NeonCostsDetails(ForbidExtra):
    neonOperatorAddress: str
    solanaLamportExpense: int
    neonAlanIncome: int


class NeonReceiptDetails(ForbidExtra):
    transactionHash: HexString
    transactionIndex: HexString
    type: HexString
    blockHash: HexString
    blockNumber: HexString
    from_: HexString = Field(alias="from")
    to: Union[HexString, None]
    effectiveGasPrice: HexString
    gasUsed: HexString
    cumulativeGasUsed: HexString
    contractAddress: Union[HexString, None]
    status: HexString
    logsBloom: HexString
    logs: Union[List[NeonGetLogsDetails], List]
    solanaBlockHash: str
    solanaCompleteTransactionSignature: str
    solanaCompleteInstructionIndex: int
    solanaCompleteInnerInstructionIndex: Union[int, None]
    neonRawTransaction: HexString
    neonIsCompleted: bool
    neonIsCanceled: bool
    solanaTransactions: List[SolanaTransaction]
    neonCosts: List[NeonCostsDetails]


class NeonGetTransactionResult(EthResult):
    def get_all_events(
        self,
        filter_by_type: tp.Optional[NeonEventType] = None,
        ignore_events: tp.List[NeonEventType] = list(),
        is_removed: Union[bool, None] = None,
    ):
        events = []
        ignored_events = [event.value for event in ignore_events]
        for transaction in self.result.solanaTransactions:
            for instruction in transaction.solanaInstructions:
                if filter_by_type:
                    events.extend(
                        [
                            event
                            for event in instruction.neonLogs
                            if all(
                                [
                                    event.neonEventType == filter_by_type.value,
                                    event.neonEventType not in ignored_events,
                                    event.removed == is_removed if is_removed is not None else True,
                                ]
                            )
                        ]
                    )
                else:
                    events.extend(
                        event
                        for event in instruction.neonLogs
                        if all(
                            [
                                event.neonEventType not in ignored_events,
                                event.removed == is_removed if is_removed is not None else True,
                            ]
                        )
                    )

        return events

    result: NeonReceiptDetails


class SolanaByNeonTransaction(EthResult):
    result: List[str]
