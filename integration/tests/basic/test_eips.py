import allure
import pytest
import typing as tp
from brownie import network, AdvancedCollectible, SimpleCollectible, convert, chain
from integration.tests.basic.helpers.assert_message import AssertMessage
from integration.tests.basic.helpers.eips.nft import (
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    get_account,
    get_contract,
    listen_for_event,
)
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


def test_erc721_can_create_advanced_collectible_integration(
    get_keyhash,
    chainlink_fee,
):
    # Arrange
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for integration testing")
    advanced_collectible = AdvancedCollectible.deploy(
        get_contract("vrf_coordinator").address,
        get_contract("link_token").address,
        get_keyhash,
        {"from": get_account()},
    )
    get_contract("link_token").transfer(advanced_collectible.address, chainlink_fee * 3, {"from": get_account()})
    # Act
    advanced_collectible.createCollectible("None", {"from": get_account()})
    # time.sleep(75)
    listen_for_event(advanced_collectible, "ReturnedCollectible", timeout=200, poll_interval=10)
    # Assert
    assert advanced_collectible.tokenCounter() > 0


def test_укс721_can_create_simple_collectible():
    if network.show_active() not in ["development"] or "fork" in network.show_active():
        pytest.skip("Only for local testing")
    simple_collectible = SimpleCollectible.deploy({"from": get_account(), "gas_price": chain.base_fee})
    simple_collectible.createCollectible("None", {"from": get_account(), "gas_price": chain.base_fee})
    assert simple_collectible.ownerOf(0) == get_account()


def test_укс721_can_create_advanced_collectible(
    get_keyhash,
    chainlink_fee,
):
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip("Only for local testing")
    advanced_collectible = AdvancedCollectible.deploy(
        get_contract("vrf_coordinator").address,
        get_contract("link_token").address,
        get_keyhash,
        {"from": get_account()},
    )
    get_contract("link_token").transfer(advanced_collectible.address, chainlink_fee * 3, {"from": get_account()})
    # Act
    transaction_receipt = advanced_collectible.createCollectible("None", {"from": get_account()})
    requestId = transaction_receipt.events["RequestedCollectible"]["requestId"]
    assert isinstance(transaction_receipt.txid, str)
    get_contract("vrf_coordinator").callBackWithRandomness(
        requestId, 777, advanced_collectible.address, {"from": get_account()}
    )
    # Assert
    assert advanced_collectible.tokenCounter() > 0
    assert isinstance(advanced_collectible.tokenCounter(), int)
