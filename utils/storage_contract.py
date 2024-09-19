import typing
from utils.web3client import NeonChainWeb3Client

class StorageContract:
    web3_client: NeonChainWeb3Client
    storage_contract: typing.Any

    def __init__(self, web3_client, storage_contract):
        self._web3_client = web3_client
        self._storage_contract = storage_contract
        self.contract_address = storage_contract.address

    def store_value(self, sender_account, value):
        tx = self._web3_client.make_raw_tx(sender_account)
        instruction_tx = self._storage_contract.functions.store(value).build_transaction(tx)
        receipt = self._web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1
        return receipt

    def retrieve_value(self, sender_account):
        tx = self._web3_client.make_raw_tx(sender_account)
        instruction_tx = self._storage_contract.functions.retrieve().build_transaction(tx)
        receipt = self._web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1
        return instruction_tx, receipt
    
    def retrieve_doubled_value(self, sender_account, value):
        tx = self._web3_client.make_raw_tx(sender_account)
        instruction_tx = self._storage_contract.functions.returnDoubledNumber(value).build_transaction(tx)
        receipt = self._web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1
        return instruction_tx, receipt

    def call_storage(self, sender_account, storage_value, request_type):
        request_value = None
        self.store_value(sender_account, storage_value)
        tx, receipt = self.retrieve_value(sender_account)

        tx_obj = self._web3_client.make_raw_tx(
            from_=sender_account.address,
            to=self._storage_contract.address,
            amount=tx["value"],
            gas=hex(tx["gas"]),
            gas_price=hex(tx["gasPrice"]),
            data=tx["data"],
            estimate_gas=False,
        )
        del tx_obj["chainId"]
        del tx_obj["nonce"]

        if request_type == "blockNumber":
            request_value = hex(receipt[request_type])
        else:
            request_value = receipt[request_type].hex()
        return tx_obj, request_value, receipt
    
    def retrieve_block(self, sender_account):
        tx = self._web3_client.make_raw_tx(sender_account)
        instruction_tx = self._storage_contract.functions.storeBlock().build_transaction(tx)
        receipt = self._web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1
        return receipt
    
    def retrieve_block_timestamp(self, sender_account):
        tx = self._web3_client.make_raw_tx(sender_account)
        instruction_tx = self._storage_contract.functions.storeBlockTimestamp().build_transaction(tx)
        receipt = self._web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1
        return receipt
    
    def retrieve_block_info(self, sender_account):
        tx = self._web3_client.make_raw_tx(sender_account)
        instruction_tx = self._storage_contract.functions.storeBlockInfo().build_transaction(tx)
        receipt = self._web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1
        return receipt

    def retrieve_sum_of_values(self, sender_account, value_1, value_2):
        tx = self._web3_client.make_raw_tx(sender_account)
        instruction_tx = self._storage_contract.functions.storeSumOfNumbers(value_1, value_2).build_transaction(tx)
        receipt = self._web3_client.send_transaction(sender_account, instruction_tx)
        assert receipt["status"] == 1
        return receipt
