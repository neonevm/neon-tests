import pathlib

import pytest
import allure

from ..base import BaseTests


class TestProxyBaseOperations(BaseTests):
    def test_create_user_get_balance(self):
        pass

    @pytest.mark.parametrize("amount,result", [
        (10, True),
        (0, True),
        (-10, False),
        (100000, False),
    ])
    def test_send_neon_tokens(self, amount, result):
        pass

    def test_send_to_nonexist_account(self):
        pass

    def test_send_to_bad_address(self):
        pass

    def test_send_with_small_gas(self):
        pass

    def test_send_with_negative_gas(self):
        pass

    def test_send_with_bad_nonce(self):
        pass

    def test_send_with_old_nonce(self):
        pass

    def test_send_with_big_nonce(self):
        pass

    def test_send_two_identical_tx(self):
        pass

    def test_cancel_tx(self):
        pass

    def test_speedup_tx(self):
        pass

    def test_deploy_and_interact_erc20_contract(self):
        pass

    def test_deploy_and_interact_simple_contract(self):
        pass
