import typing as tp

import pytest
from web3 import Web3

import allure
from clickfile import EnvName
from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.basic import Tag
from integration.tests.basic.helpers.errors import Error32602
from utils.accounts import EthAccounts
from utils.models.error import EthError32602
from utils.models.result import EthEstimateGas, EthResult
from utils.web3client import NeonChainWeb3Client


@allure.feature("JSON-RPC validation")
@allure.story("Verify eth_estimateGas RPC call")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestRpcEstimateGas:
    accounts: EthAccounts
    web3_client: NeonChainWeb3Client

    @pytest.mark.parametrize("block_param", [Tag.LATEST, Tag.PENDING, Tag.EARLIEST, Tag.FINALIZED, 1, None])
    @pytest.mark.neon_only
    def test_eth_estimate_gas_different_block_param(self, block_param: tp.Union[int, Tag, None], json_rpc_client):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]

        transaction = {
            "from": sender_account.address,
            "to": recipient_account.address,
            "value": hex(1000),
            "gasPrice": hex(self.web3_client.gas_price()),
            "nonce": hex(self.web3_client.get_nonce(sender_account.address)),
            "chainId": hex(self.web3_client.eth.chain_id),
            "gas": hex(0),
        }
        params = [dict(transaction)]
        if isinstance(block_param, int):
            response = json_rpc_client.send_rpc(method="eth_blockNumber")
            assert "result" in response
            EthResult(**response)
            params.append(response["result"])
        if isinstance(block_param, Tag):
            params.append(block_param.value)
        response = json_rpc_client.send_rpc(method="eth_estimateGas", params=params)
        assert "result" in response
        assert rpc_checks.is_hex(
            response["result"]
        ), f"the result for estimated gas should be in hex, but got'{response['result']}'"
        EthEstimateGas(**response)
        assert int(response["result"], 16) == 25_000

    @pytest.mark.bug  # fails on geth (returns a different error message), needs a fix, and refactor of Error32602
    def test_eth_estimate_gas_negative(self, json_rpc_client):
        response = json_rpc_client.send_rpc(method="eth_estimateGas", params=[])
        assert "error" in response, "error field not in response"
        assert "code" in response["error"]
        assert "message" in response["error"], "message field not in response"
        code = response["error"]["code"]
        message = response["error"]["message"]
        assert code == Error32602.CODE, "wrong code"
        assert message == Error32602.INVALID_CALL, "wrong message"
        EthError32602(**response)

    @pytest.mark.parametrize("contract_name", ["BigGasFactory1", "BigGasFactory2"])
    @pytest.mark.parametrize("process_gas, reserve_gas", [(850_000, 15_000), (8_500_000, 150_000)])
    @pytest.mark.neon_only
    def test_eth_estimate_gas_with_big_int(self, contract_name, process_gas, reserve_gas, json_rpc_client):
        sender_account = self.accounts.create_account()

        big_gas_contract, _ = self.web3_client.deploy_and_get_contract(
            contract="issues/Ndev49",
            version="0.8.10",
            contract_name=contract_name,
            account=sender_account,
            constructor_args=[process_gas, reserve_gas],
        )

        """Check eth_estimateGas request on contracts with big int"""
        tx = self.web3_client.make_raw_tx(from_=sender_account, estimate_gas=True)  # gas needed to build the tx
        trx_big_gas = big_gas_contract.functions.checkBigGasRequirements().build_transaction(tx)
        trx_big_gas["value"] = Web3.to_hex(0)
        trx_big_gas["nonce"] = Web3.to_hex(trx_big_gas["nonce"])
        trx_big_gas["chainId"] = Web3.to_hex(trx_big_gas["chainId"])
        trx_big_gas["gasPrice"] = Web3.to_hex(trx_big_gas["gasPrice"])

        # gas needed just to estimate gas -_-
        trx_big_gas["gas"] = Web3.to_hex((process_gas + reserve_gas) + self.web3_client.gas_price() // 1000)

        gas_estimate = self.web3_client.eth.estimate_gas(trx_big_gas)
        trx_big_gas["gas"] = Web3.to_hex(gas_estimate)

        response = json_rpc_client.send_rpc(method="eth_estimateGas", params=trx_big_gas)
        assert "error" not in response
        assert rpc_checks.is_hex(response["result"]), f"Invalid response result, '{response['result']}'"

        signed_trx_big_gas = self.web3_client.eth.account.sign_transaction(trx_big_gas, sender_account.key)
        raw_trx_big_gas = self.web3_client.eth.send_raw_transaction(signed_trx_big_gas.rawTransaction)
        deploy_trx_big_gas = self.web3_client.eth.wait_for_transaction_receipt(raw_trx_big_gas)
        assert deploy_trx_big_gas.get("status"), f"Transaction is incomplete: {deploy_trx_big_gas}"
        assert gas_estimate >= int(deploy_trx_big_gas["gasUsed"]), "Estimated Gas < Used Gas"
        EthEstimateGas(**response)

    @pytest.mark.neon_only  # Geth returns a different estimate
    def test_rpc_estimate_gas_send_neon(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        tx_receipt = self.web3_client.send_neon(sender_account, recipient_account, amount=0.001)
        transaction = self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"])

        assert "gas" in transaction
        estimated_gas = transaction["gas"]
        assert estimated_gas == 25_000

    @pytest.mark.neon_only  # Geth returns a different estimate
    def test_rpc_estimate_gas_erc20(self, erc20_simple, env_name: EnvName):
        recipient_account = self.accounts[1]
        tx_receipt = erc20_simple.transfer(erc20_simple.owner, recipient_account, 1)
        transaction = self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"])

        assert "gas" in transaction
        estimated_gas = transaction["gas"]
        assert estimated_gas == 1_192_320

    @pytest.mark.neon_only  # Geth returns a different estimate
    def test_rpc_estimate_gas_spl(self, erc20_spl):
        recipient_account = self.accounts[1]
        tx_receipt = erc20_spl.transfer(erc20_spl.account, recipient_account, 1)
        transaction = self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"])

        assert "gas" in transaction
        estimated_gas = transaction["gas"]
        assert estimated_gas == 2_089_280

    @pytest.mark.neon_only  # Geth returns a different estimate
    def test_rpc_estimate_gas_contract_get_value(self, common_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = common_contract.functions.getText().build_transaction(tx)
        tx_receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        transaction = self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"])

        assert "gas" in transaction
        estimated_gas = transaction["gas"]
        assert estimated_gas == 25_000

    @pytest.mark.neon_only  # Geth returns a different estimate
    def test_rpc_estimate_gas_contract_set_value(self, common_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = common_contract.functions.setNumber(100).build_transaction(tx)
        tx_receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        transaction = self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"])
        assert "gas" in transaction
        estimated_gas = transaction["gas"]
        assert estimated_gas == 25_000

    @pytest.mark.neon_only  # Geth returns a different estimate
    def test_rpc_estimate_gas_contract_calls_another_contract(self, common_contract):
        sender_account = self.accounts[0]
        caller_contract, _ = self.web3_client.deploy_and_get_contract(
            "common/Common",
            "0.8.12",
            contract_name="CommonCaller",
            account=sender_account,
            constructor_args=[common_contract.address],
        )

        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = caller_contract.functions.getNumber().build_transaction(tx)
        tx_receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        transaction = self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"])

        assert "gas" in transaction
        estimated_gas = transaction["gas"]
        assert estimated_gas == 25_000
