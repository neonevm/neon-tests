import random

import allure
import pytest
import web3

from integration.tests.basic.helpers.basic import BaseMixin
from utils.consts import ZERO_ADDRESS


@allure.feature("EIP Verifications")
@allure.story("EIP-3448: MetaProxy Standard: \
              A minimal bytecode implementation for creating proxy contracts \
              with immutable metadata attached to the bytecode")
class TestMetaProxyStandard(BaseMixin):
    def test_create_from_call_data(self, meta_proxy_contract):
        assert meta_proxy_contract.functions.testCreateFromCalldata().call()

    def test_create_from_bytes(self, meta_proxy_contract):
        assert meta_proxy_contract.functions.testCreateFromBytes().call()
