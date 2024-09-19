import allure

from utils.consts import ZERO_ADDRESS


@allure.feature("EIP Verifications")
@allure.story(
    "EIP-3448: MetaProxy Standard: \
              A minimal bytecode implementation for creating proxy contracts \
              with immutable metadata attached to the bytecode"
)
class TestMetaProxyStandard:
    expected_a = ZERO_ADDRESS
    expected_b = 0xC0FFE
    expected_c = [0, 0, 0, 0, 0, 0, 0, 0, 0]

    def test_create_from_call_data(self, meta_proxy_contract):
        self.expected_a = meta_proxy_contract.address

        a, b, c = meta_proxy_contract.functions.testCreateFromCalldataGetMetadataViaCall().call()
        assert a == self.expected_a
        assert b == self.expected_b
        assert c == self.expected_c

        a, b, c = meta_proxy_contract.functions.testCreateFromCalldataGetMetadataWithoutCall().call()
        assert a == self.expected_a
        assert b == self.expected_b
        assert c == self.expected_c

        b = meta_proxy_contract.functions.testCreateFromCalldataReturnSingleValue().call()
        assert b == self.expected_b

        b, c = meta_proxy_contract.functions.testCreateFromCalldataReturnMultiValues().call()
        assert b == self.expected_b
        assert len(c) == len(self.expected_c)

        success = meta_proxy_contract.functions.testCreateFromCalldataReturnRevert().call()
        assert not success

    def test_create_from_bytes(self, meta_proxy_contract):
        self.expected_a = meta_proxy_contract.address

        a, b, c = meta_proxy_contract.functions.testCreateFromBytesGetMetadataViaCall().call()
        assert a == self.expected_a
        assert b == self.expected_b
        assert c == self.expected_c

        a, b, c = meta_proxy_contract.functions.testCreateFromBytesGetMetadataWithoutCall().call()
        assert a == self.expected_a
        assert b == self.expected_b
        assert c == self.expected_c

        b = meta_proxy_contract.functions.testCreateFromBytesReturnSingleValue().call()
        assert b == self.expected_b

        b, c = meta_proxy_contract.functions.testCreateFromBytesReturnMultiValues().call()
        assert b == self.expected_b
        assert len(c) == len(self.expected_c)

        success = meta_proxy_contract.functions.testCreateFromBytesReturnRevert().call()
        assert not success
