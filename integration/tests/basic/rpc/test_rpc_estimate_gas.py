import typing as tp

import allure
import pytest
from solana.rpc.commitment import Confirmed
from solders.signature import Signature
from web3 import Web3

from clickfile import EnvName
from integration.tests.basic.helpers import rpc_checks
from integration.tests.basic.helpers.basic import Tag
from integration.tests.basic.helpers.errors import Error32602
from utils.accounts import EthAccounts
from utils.cu_cost_packed import CuCostPktData
from utils.models.error import EthError32602
from utils.models.result import EthEstimateGas, EthResult
from utils.solana_client import SolanaClient
from utils.web3client import NeonChainWeb3Client

_MIN_GAS_LIMIT = 1038831


@allure.feature("JSON-RPC validation")
@allure.story("Verify eth_estimateGas RPC call")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestRpcEstimateGas:
    accounts: EthAccounts
    web3_client: NeonChainWeb3Client

    @pytest.mark.parametrize("block_param", [Tag.LATEST, Tag.PENDING, Tag.EARLIEST, Tag.FINALIZED, 1, None])
    @pytest.mark.neon_only
    @pytest.mark.only_stands
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
        assert int(response["result"], 16) == _MIN_GAS_LIMIT

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
        raw_trx_big_gas = self.web3_client.eth.send_raw_transaction(signed_trx_big_gas.raw_transaction)
        deploy_trx_big_gas = self.web3_client.wait_for_transaction_receipt(raw_trx_big_gas)
        assert deploy_trx_big_gas.get("status"), f"Transaction is incomplete: {deploy_trx_big_gas}"
        assert gas_estimate >= int(deploy_trx_big_gas["gasUsed"]), "Estimated Gas < Used Gas"
        EthEstimateGas(**response)

    @pytest.mark.neon_only  # Geth returns a different estimate
    @pytest.mark.only_stands
    def test_rpc_estimate_gas_send_neon(self):
        sender_account = self.accounts[0]
        recipient_account = self.accounts[1]
        tx_receipt = self.web3_client.send_neon(sender_account, recipient_account, amount=0.001)
        transaction = self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"])

        assert "gas" in transaction
        estimated_gas = transaction["gas"]
        assert estimated_gas == _MIN_GAS_LIMIT

    @pytest.mark.neon_only  # Geth returns a different estimate
    @pytest.mark.only_stands
    def test_rpc_estimate_gas_erc20(self, erc20_simple, env_name: EnvName):
        recipient_account = self.accounts[1]
        tx_receipt = erc20_simple.transfer(erc20_simple.owner, recipient_account, 1)
        transaction = self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"])

        assert "gas" in transaction
        estimated_gas = transaction["gas"]
        assert estimated_gas == 2_087_407

    @pytest.mark.neon_only  # Geth returns a different estimate
    @pytest.mark.only_stands
    def test_rpc_estimate_gas_spl(self, erc20_spl):
        recipient_account = self.accounts.create_account()
        tx_receipt = erc20_spl.transfer(erc20_spl.owner, recipient_account, 1)
        transaction = self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"])
        assert transaction["gas"] == 3_004_911

    @pytest.mark.neon_only  # Geth returns a different estimate
    @pytest.mark.only_stands
    def test_rpc_estimate_gas_contract_get_value(self, common_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = common_contract.functions.getText().build_transaction(tx)
        tx_receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        transaction = self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"])

        assert "gas" in transaction
        estimated_gas = transaction["gas"]
        assert estimated_gas == _MIN_GAS_LIMIT

    @pytest.mark.neon_only  # Geth returns a different estimate
    @pytest.mark.only_stands
    def test_rpc_estimate_gas_contract_set_value(self, common_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(from_=sender_account)
        instruction_tx = common_contract.functions.setNumber(100).build_transaction(tx)
        tx_receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
        transaction = self.web3_client.get_transaction_by_hash(tx_receipt["transactionHash"])
        assert "gas" in transaction
        estimated_gas = transaction["gas"]
        assert estimated_gas == _MIN_GAS_LIMIT

    @pytest.mark.neon_only  # Geth returns a different estimate
    @pytest.mark.only_stands
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
        assert estimated_gas == _MIN_GAS_LIMIT

    @pytest.mark.parametrize("cu_price_coefficient", [0, 1, 1.1])
    def test_compute_unit_price_malicious_manipulation(
        self,
        web3_client: NeonChainWeb3Client,
        sol_client: SolanaClient,
        default_cu_price: int,
        cu_price_coefficient,
        env_name,
    ):
        if cu_price_coefficient < 1 and env_name == EnvName.DEVNET:
            pytest.skip("Devnet DEFAULT_CU_PRICE is dynamic, so we can't test < 1")
        sender = self.accounts[1]
        receiver = self.accounts[0]
        raw_tx = web3_client.make_raw_tx(sender, receiver, amount=100000, estimate_gas=True)
        neon_gas_estimate = self.web3_client.neon_estimate_gas(raw_tx, show_gas_details=True)

        gas = (
            neon_gas_estimate["gasTransactionSizeUsed"]
            + neon_gas_estimate["gasAddressLookupTableUsed"]
            + neon_gas_estimate["gasExecutionUsed"]
            + neon_gas_estimate["gasFinishUsed"]
        )
        cu_price_initial = neon_gas_estimate["solanaComputeUnitPrice"]
        cu_price_new = int(cu_price_initial * cu_price_coefficient)
        pkt = CuCostPktData.from_raw(gas, neon_gas_estimate["numIterations"], cu_price_new)
        cu_gas = pkt.tx_cu_cost
        gas_limit = gas + cu_gas
        raw_tx["gas"] = gas_limit

        eth_receipt = web3_client.send_transaction(account=sender, transaction=raw_tx)
        eth_tx_hash = eth_receipt["transactionHash"]
        neon_receipt = self.web3_client.get_neon_trx_receipt(eth_tx_hash)["result"]
        solana_lamport_expense_total = 0
        neon_gas_used_total = 0

        for sol_tx in neon_receipt["solanaTransactions"]:
            solana_lamport_expense_per_tx = sol_tx["solanaLamportExpense"]
            solana_lamport_expense_total += solana_lamport_expense_per_tx
            for instruction in sol_tx["solanaInstructions"]:
                if instruction["solanaProgram"].lower() == "neonevm":
                    neon_gas_used_per_tx = instruction["neonGasUsed"]
                    neon_gas_used_total += neon_gas_used_per_tx

        assert abs(solana_lamport_expense_total - neon_gas_used_total) <= 1

        solana_transaction_sigs = web3_client.get_solana_trx_by_neon(eth_tx_hash.hex())["result"]
        operator_spent_total = 0
        cu_prices_actual: list[int] = []

        for solana_transaction_sig in solana_transaction_sigs:
            solana_tx = sol_client.get_transaction(
                tx_sig=Signature.from_string(solana_transaction_sig),
                max_supported_transaction_version=0,
                commitment=Confirmed,
            ).value
            cu_price_actual = sol_client.get_compute_budget_set_cu_price_from_tx(solana_tx)
            cu_prices_actual.append(cu_price_actual)

            operator_spent_per_tx = (
                solana_tx.transaction.meta.pre_balances[0] - solana_tx.transaction.meta.post_balances[0]
            )
            operator_spent_total += operator_spent_per_tx

        assert abs(operator_spent_total - neon_gas_used_total) <= 1

        msg = str(cu_prices_actual) + " {sign} " + str(default_cu_price)
        if cu_price_coefficient < 1:
            assert all(cu_price < cu_price_initial for cu_price in cu_prices_actual), msg.format(sign="<")
        else:
            assert all(cu_price == cu_price_initial for cu_price in cu_prices_actual), msg.format(sign="==")
