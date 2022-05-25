import allure
import pytest
import typing as tp
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.rpc_request_factory import RpcRequestFactory
from integration.tests.basic.helpers.unit import Unit
from integration.tests.basic.model.model import TrxReceiptResponse, TrxResponse
from integration.tests.basic.model.tags import Tag
from integration.tests.basic.test_data.input_data import InputData
from integration.tests.basic.helpers.basic import BaseMixin
from integration.tests.basic.helpers.rpc_request_factory import RpcRequestFactory
from integration.tests.basic.helpers.rpc_request_params_factory import RpcRequestParamsFactory
from integration.tests.basic.model import model as request_models
from integration.tests.basic.model.tags import Tag
from integration.tests.basic.test_data import input_data
from integration.tests.basic.test_transfers import TestTransfer


@allure.story("Basic: EIP compatibility tests")
# class TestEip(BaseMixin):
class TestEip(TestTransfer):
    @pytest.mark.parametrize("transfer_amount", [(1)])
    def test_send_neon_from_one_account_to_another(self, transfer_amount: tp.Union[int, float]):
        """Send neon from one account to another
        Send zero: Neon
        """

        initial_sender_balance, initial_recipient_balance = self.get_initial_balances()

        tx_receipt = self.process_transaction(self.sender_account, self.recipient_account, transfer_amount)
        self.assert_balance(
            self.sender_account.address,
            initial_sender_balance - transfer_amount - self.calculate_trx_gas(tx_receipt=tx_receipt),
            rnd_dig=1,
        )
        self.assert_balance(self.recipient_account.address, initial_recipient_balance + transfer_amount, rnd_dig=3)

    def test_nft_erc721(self):
        pass
