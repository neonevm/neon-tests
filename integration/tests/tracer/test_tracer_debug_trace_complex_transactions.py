import allure
import pytest

from utils.web3client import NeonChainWeb3Client
from utils.accounts import EthAccounts
from utils.tracer_client import TracerClient
from utils.helpers import wait_condition
from tracer_helper import validate_response_result

tracer_params = {"tracer": "callTracer", "tracerConfig": {"withLog": True}}


@allure.feature("Tracer API")
@allure.story("Tracer API RPC calls debug method trace_transaction iterative txs check")
@pytest.mark.usefixtures("accounts", "web3_client", "tracer_api")
class TestDebugTraceIterativeTransaction:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    tracer_api: TracerClient

    def test_trace_iterative_tx_struct_opcode_tracer(self, counter_contract):
        sender_account = self.accounts[0]
        tx = self.web3_client.make_raw_tx(from_=sender_account)

        instruction_tx = counter_contract.functions.moreInstruction(0, 3000).build_transaction(tx)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        wait_condition(
            lambda: self.web3_client.is_trx_iterative(receipt["transactionHash"].hex()) is True,
            timeout_sec=120,
        )

        params = [receipt["transactionHash"].hex()]
        response = self.tracer_api.send_rpc_and_wait_response("debug_traceTransaction", params)
        validate_response_result(response)
