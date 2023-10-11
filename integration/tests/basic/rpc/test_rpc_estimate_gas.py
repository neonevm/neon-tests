import typing as tp

import allure
import pytest

from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.basic import BaseMixin
from utils import helpers


@allure.feature("JSON-RPC-ESTIMATE-GAS validation")
@allure.story("Verify eth_estimateGas RPC call")
class TestRpcEstimateGas(BaseMixin):
    account: "eth_account.signers.local.LocalAccount" = None

    @pytest.fixture(params=[(850000, 15000), (8500000, 150000), (8500000, 150000)])
    def constructor_args(self, request: tp.Any) -> tp.List[int]:
        return request.param

    @pytest.fixture(params=["BigGasFactory1", "BigGasFactory2"])
    def deploy_big_gas_requirements_contract(
            self, request: tp.Any, constructor_args: tp.List[int]
    ) -> "web3._utils.datatypes.Contract":
        """Deploy contracts"""
        self.account = self.sender_account
        #  contract
        contract_interface = helpers.get_contract_interface(
            contract="issues/Ndev49", version="0.8.10", contract_name=request.param
        )
        counter = self.web3_client.eth.contract(
            abi=contract_interface["abi"], bytecode=contract_interface["bin"]
        )
        # Build transaction
        transaction = counter.constructor(*constructor_args).build_transaction(
            {
                "chainId": self.web3_client._chain_id,
                "gas": 0,
                "gasPrice": hex(self.web3_client.gas_price()),
                "nonce": self.web3_client.eth.get_transaction_count(
                    self.account.address
                ),
                "value": "0x0",
            }
        )
        del transaction["to"]
        # Check Base contract eth_estimateGas
        response = self.proxy_api.send_rpc(method="eth_estimateGas", params=transaction)
        assert "error" not in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response result, `{response['result']}`"
        transaction["gas"] = int(response["result"], 16)
        # Deploy contract
        signed_tx = self.web3_client.eth.account.sign_transaction(
            transaction, self.account.key
        )
        tx = self.web3_client.eth.send_raw_transaction(signed_tx.rawTransaction)
        contract_deploy_tx = self.web3_client.eth.wait_for_transaction_receipt(tx)
        return self.web3_client.eth.contract(
            address=contract_deploy_tx["contractAddress"], abi=contract_interface["abi"]
        )

    def test_eth_estimate_gas_with_big_int(
            self, deploy_big_gas_requirements_contract: tp.Any
    ) -> None:
        """Check eth_estimateGas request on contracts with big int"""
        big_gas_contract = deploy_big_gas_requirements_contract
        trx_big_gas = (
            big_gas_contract.functions.checkBigGasRequirements().build_transaction(
                {
                    "chainId": self.web3_client._chain_id,
                    "from": self.account.address,
                    "nonce": self.web3_client.eth.get_transaction_count(
                        self.account.address
                    ),
                    "gas": "0x0",
                    "gasPrice": hex(self.web3_client.gas_price()),
                    "value": "0x0",
                }
            )
        )
        # Check Base contract eth_estimateGas
        response = self.proxy_api.send_rpc(method="eth_estimateGas", params=trx_big_gas)
        assert "error" not in response
        estimated_gas = int(response["result"], 16)
        assert rpc_checks.is_hex(
            response["result"]
        ), f"Invalid response result, `{response['result']}`"
        trx_big_gas["gas"] = estimated_gas
        signed_trx_big_gas = self.web3_client.eth.account.sign_transaction(
            trx_big_gas, self.account.key
        )
        raw_trx_big_gas = self.web3_client.eth.send_raw_transaction(
            signed_trx_big_gas.rawTransaction
        )
        deploy_trx_big_gas = self.web3_client.eth.wait_for_transaction_receipt(
            raw_trx_big_gas
        )
        assert deploy_trx_big_gas.get(
            "status"
        ), f"Transaction is incomplete: {deploy_trx_big_gas}"
        assert estimated_gas >= int(
            deploy_trx_big_gas["gasUsed"]
        ), "Estimated Gas < Used Gas"

    def test_rpc_estimate_gas_send_neon(self):
        receipt = self.send_neon(
            self.sender_account, self.recipient_account, amount=0.001
        )

        assert receipt.cumulativeGasUsed == 10000

    def test_rpc_estimate_gas_erc20(self, erc20_simple):
        tx_receipt = erc20_simple.transfer(erc20_simple.owner, self.recipient_account, 1)

        assert "cumulativeGasUsed" in tx_receipt
        assert tx_receipt["cumulativeGasUsed"] == 1527280

    def test_rpc_estimate_gas_contract_get_value(self):
        contract, receipt = self.web3_client.deploy_and_get_contract(
            "common/Common", "0.8.12",
            contract_name="Common", account=self.sender_account
        )
        tx = self.make_contract_tx_object()
        instruction_tx = contract.functions.getText().build_transaction(tx)
        tx_receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)

        assert tx_receipt["gasUsed"] == 10000

    def test_rpc_estimate_gas_contract_set_value(self):
        contract, _ = self.web3_client.deploy_and_get_contract(
            "common/Common", "0.8.12",
            contract_name="Common", account=self.sender_account
        )
        tx = self.make_contract_tx_object()
        instruction_tx = contract.functions.setNumber(100).build_transaction(tx)
        tx_receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)

        assert tx_receipt["gasUsed"] == 10000

    def test_rpc_estimate_gas_contract_calls_another_contract(self):
        common_contract, _ = self.web3_client.deploy_and_get_contract(
            "common/Common", "0.8.12",
            contract_name="Common", account=self.sender_account
        )
        caller_contract, _ = self.web3_client.deploy_and_get_contract(
            "common/Common", "0.8.12",
            contract_name="CommonCaller", account=self.sender_account,
            constructor_args=[common_contract.address]
        )
        tx = self.make_contract_tx_object()
        instruction_tx = caller_contract.functions.getNumber().build_transaction(tx)
        tx_receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)

        assert tx_receipt["gasUsed"] == 10000

    def test_rpc_estimate_gas_spl(self, erc20_spl):
        tx_receipt = erc20_spl.transfer(erc20_spl.account, self.recipient_account, 1)

        assert tx_receipt["gasUsed"] == 10000
