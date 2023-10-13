import typing as tp

import allure
import pytest
from hexbytes import HexBytes

from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.basic import BaseMixin, Tag
from integration.tests.basic.helpers.errors import Error32000


@pytest.fixture(scope="class")
def common_contract(web3_client, class_account) -> tp.Any:
    contract, receipt = web3_client.deploy_and_get_contract(
        contract="common/Common", version="0.8.12",
        contract_name="Common", account=class_account
    )
    yield contract, receipt


@allure.feature("JSON-RPC validation")
@allure.story("Verify eth_estimateGas RPC call")
class TestRpcEstimateGas(BaseMixin):

    @pytest.mark.xfail(reason="NDEV-2310")
    @pytest.mark.parametrize("block_param", [Tag.LATEST, Tag.PENDING, Tag.EARLIEST, Tag.FINALIZED, 1, None])
    def test_eth_estimate_gas(self, common_contract, class_account, block_param: tp.Union[int, Tag, None]):
        t_raw = self.web3_client.get_transaction_by_hash(common_contract[1]["transactionHash"])
        transaction = {k: v if type(v) is not HexBytes else v.hex() for k, v in dict(t_raw).items()}
        transaction["to"] = class_account.address
        params = [dict(transaction)]
        if isinstance(block_param, int):
            response = self.proxy_api.send_rpc(method="eth_blockNumber")
            assert "result" in response
            params.append(int(response["result"], 16))
        if isinstance(block_param, Tag):
            params.append(block_param.value)
        response = self.proxy_api.send_rpc(method="eth_estimateGas", params=params)
        assert "result" in response
        assert rpc_checks.is_hex(response["result"]), \
            f"the result for estimated gas should be in hex, but got'{response['result']}'"
        assert int(response["result"], 16) == 30_000

    def test_eth_estimate_gas_negative(self):
        response = self.proxy_api.send_rpc(method="eth_estimateGas", params=[])
        assert "error" in response, "error field not in response"
        assert "code" in response["error"]
        assert "message" in response["error"], "message field not in response"
        code = response["error"]["code"]
        message = response["error"]["message"]
        assert code == Error32000.CODE, "wrong code"
        assert Error32000.MISSING_ARGUMENT in message, "wrong message"

    @pytest.mark.parametrize("contract_name", ["BigGasFactory1", "BigGasFactory2"])
    @pytest.mark.parametrize("process_gas, reserve_gas", [(850_000, 15_000), (8_500_000, 150_000)])
    def test_eth_estimate_gas_with_big_int(self, contract_name, process_gas, reserve_gas):
        big_gas_contract, _ = self.web3_client.deploy_and_get_contract(
            contract="issues/Ndev49", version="0.8.10",
            contract_name=contract_name, account=self.sender_account,
            constructor_args=[process_gas, reserve_gas]
        )

        """Check eth_estimateGas request on contracts with big int"""
        trx_big_gas = (
            big_gas_contract.functions.checkBigGasRequirements().build_transaction(
                {
                    "chainId": self.web3_client._chain_id,
                    "from": self.sender_account.address,
                    "nonce": self.web3_client.eth.get_transaction_count(self.sender_account.address),
                    "gas": "0x0",
                    "gasPrice": hex(self.web3_client.gas_price()),
                    "value": "0x0",
                }
            )
        )
        # Check Base contract eth_estimateGas
        response = self.proxy_api.send_rpc(method="eth_estimateGas", params=trx_big_gas)
        assert "error" not in response
        assert rpc_checks.is_hex(response["result"]), f"Invalid response result, '{response['result']}'"
        estimated_gas = int(response["result"], 16)
        trx_big_gas["gas"] = estimated_gas
        signed_trx_big_gas = self.web3_client.eth.account.sign_transaction(trx_big_gas, self.sender_account.key)
        raw_trx_big_gas = self.web3_client.eth.send_raw_transaction(signed_trx_big_gas.rawTransaction)
        deploy_trx_big_gas = self.web3_client.eth.wait_for_transaction_receipt(raw_trx_big_gas)
        assert deploy_trx_big_gas.get("status"), f"Transaction is incomplete: {deploy_trx_big_gas}"
        assert estimated_gas >= int(deploy_trx_big_gas["gasUsed"]), "Estimated Gas < Used Gas"

    def test_rpc_estimate_gas_send_neon(self):
        tx_receipt = self.send_neon(self.sender_account, self.recipient_account, amount=0.001)
        transaction = self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"])

        assert "gas" in transaction
        estimated_gas = transaction["gas"]
        assert estimated_gas == 30_000

    def test_rpc_estimate_gas_erc20(self, erc20_simple):
        tx_receipt = erc20_simple.transfer(erc20_simple.owner, self.recipient_account, 1)
        transaction = self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"])

        assert "gas" in transaction
        estimated_gas = transaction["gas"]
        assert estimated_gas == 1_552_280

    def test_rpc_estimate_gas_spl(self, erc20_spl):
        tx_receipt = erc20_spl.transfer(erc20_spl.account, self.recipient_account, 1)
        transaction = self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"])

        assert "gas" in transaction
        estimated_gas = transaction["gas"]
        assert estimated_gas == 2_084_280

    def test_rpc_estimate_gas_contract_get_value(self, common_contract):
        tx = self.make_contract_tx_object()
        instruction_tx = common_contract[0].functions.getText().build_transaction(tx)
        tx_receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        transaction = self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"])

        assert "gas" in transaction
        estimated_gas = transaction["gas"]
        assert estimated_gas == 30_000

    def test_rpc_estimate_gas_contract_set_value(self, common_contract):
        tx = self.make_contract_tx_object()
        instruction_tx = common_contract[0].functions.setNumber(100).build_transaction(tx)
        tx_receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)
        transaction = self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"])

        assert "gas" in transaction
        estimated_gas = transaction["gas"]
        assert estimated_gas == 30_000

    def test_rpc_estimate_gas_contract_calls_another_contract(self, common_contract):
        caller_contract, _ = self.web3_client.deploy_and_get_contract(
            "common/Common", "0.8.12",
            contract_name="CommonCaller", account=self.sender_account,
            constructor_args=[common_contract[0].address]
        )
        tx = self.make_contract_tx_object()
        instruction_tx = caller_contract.functions.getNumber().build_transaction(tx)
        tx_receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)

        transaction = self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"])

        assert "gas" in transaction
        estimated_gas = transaction["gas"]
        assert estimated_gas == 30_000
