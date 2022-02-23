from enum import Enum


class JsonRpcMethods(Enum):
    GET_BLOCK_BY_HASH = "eth_getBlockByHash"
    GET_BLOCK_BY_NUMBER = "eth_getBlockByNumber"
    BLOCK_NUMBER = "eth_blockNumber"
    CALL = "eth_call"
    ESTIMATE_GAS = "eth_estimateGas"
    GAS_PROCE = "eth_gasPrice"
    GET_LOGS = "eth_getLogs"
    GET_BALANCE = "eth_getBalance"
    GET_TRX_COUNT = "eth_getTransactionCount"
    GET_CODE = "eth_getCode"
    SEND_RAW_TRX = "eth_sendRawTransaction"
    GET_TRX_BY_HASH = "eth_getTransactionByHash"
    GET_TRX_RECEIPT = "eth_getTransactionReceipt"
    GET_STORAGE_AT = "eth_getStorageAt"
    WEB3_CLIENT_VERSION = "web3_clientVersion"
    NET_VERSION = "net_version"
