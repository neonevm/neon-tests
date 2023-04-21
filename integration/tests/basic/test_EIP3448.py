import allure
from integration.tests.basic.helpers.basic import BaseMixin


@allure.feature("EIP Verifications")
@allure.story("EIP-3448: MetaProxy Standard: \
              A minimal bytecode implementation for creating proxy contracts \
              with immutable metadata attached to the bytecode")
class TestMetaProxyStandard(BaseMixin):
    def test_create_from_call_data(self, meta_proxy_contract):
        assert meta_proxy_contract.functions.testCreateFromCalldataGetMetadataViaCall().call()
        assert meta_proxy_contract.functions.testCreateFromCalldataGetMetadataWithoutCall().call()
        assert meta_proxy_contract.functions.testCreateFromCalldataReturnSingleValue().call()
        assert meta_proxy_contract.functions.testCreateFromCalldataReturnMultiValues().call()
        assert meta_proxy_contract.functions.testCreateFromCalldataReturnRevert().call()

    def test_create_from_bytes(self, meta_proxy_contract):
        assert meta_proxy_contract.functions.testCreateFromBytesGetMetadataViaCall().call()
        assert meta_proxy_contract.functions.testCreateFromBytesGetMetadataWithoutCall().call()
        assert meta_proxy_contract.functions.testCreateFromBytesReturnSingleValue().call()
        assert meta_proxy_contract.functions.testCreateFromBytesReturnMultiValues().call()
        assert meta_proxy_contract.functions.testCreateFromBytesReturnRevert().call()
