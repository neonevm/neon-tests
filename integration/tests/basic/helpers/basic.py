from dataclasses import dataclass
from enum import Enum


@dataclass
class AccountData:
    address: str
    key: str = ""


class Tag(Enum):
    EARLIEST = "earliest"
    LATEST = "latest"
    PENDING = "pending"
    SAFE = "safe"
    FINALIZED = "finalized"


class NeonEventType(Enum):
    EnterCreate = "EnterCreate"
    ExitStop = "ExitStop"
    Return = "Return"
    Log = "Log"
    EnterCall = "EnterCall"
    EnterCallCode = "EnterCallCode"
    EnterStaticCall = "EnterStaticCall"
    EnterDelegateCall = "EnterDelegateCall"
    EnterCreate2 = "EnterCreate2"
    ExitReturn = "ExitReturn"
    ExitSelfDestruct = "ExitSelfDestruct"
    ExitRevert = "ExitRevert"
    ExitSendAll = "ExitSendAll"
    Cancel = "Cancel"
    Lost = "Lost"
    InvalidRevision = "InvalidRevision"
    StepReset = "StepReset"


class SolanaInstruction(Enum):
    CollectTreasure = "CollectTreasure", 30
    HolderCreate = "HolderCreate", 36
    HolderDelete = "HolderDelete", 37
    HolderWrite = "HolderWrite", 38
    CreateAccountBalance = "CreateAccountBalance", 48
    Deposit = "Deposit", 49
    TxExecFromData = "TxExecFromData", 61
    TxExecFromAccount = "TxExecFromAccount", 51
    TxStepFromData = "TxStepFromData", 52
    TxStepFromAccount = "TxStepFromAccount", 53
    TxStepFromAccountNoChainId = "TxStepFromAccountNoChainId", 54
    CancelWithHash = "CancelWithHash", 55
    TxExecFromDataSolanaCall = "TxExecFromDataSolanaCall", 62
    TxExecFromAccountSolanaCall = "TxExecFromAccountSolanaCall", 57
    CreateOperatorBalance = "CreateOperatorBalance", 58
    DeleteOperatorBalance = "DeleteOperatorBalance", 59
    WithdrawOperatorBalance = "WithdrawOperatorBalance", 60
    OldDepositV1004 = "OldDepositV1004", 39
    OldCreateAccountV1004 = "OldCreateAccountV1004", 40
    OldTxExecFromDataV1004 = "OldTxExecFromDataV1004", 31
    OldTxExecFromAccountV1004 = "OldTxExecFromAccountV1004", 42
    OldTxStepFromDataV1004 = "OldTxStepFromDataV1004", 32
    OldTxStepFromAccountV1004 = "OldTxStepFromAccountV1004", 33
    OldTxStepFromAccountNoChainIdV1004 = "OldTxStepFromAccountNoChainIdV1004", 34
    OldCancelWithHashV1004 = "OldCancelWithHashV1004", 35

    @property
    def inst_name(self):
        return self.value[0]

    @property
    def inst_code(self):
        return self.value[1]
