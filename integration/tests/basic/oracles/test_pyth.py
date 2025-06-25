import allure
import pytest

from utils.web3client import NeonChainWeb3Client
from utils.consts import REMAPPING_ZEPPELIN

PRICES_DEVNET = {
    "SOL/USDC": {"address": "0x19c6315fCb69aAE8eB74f0c8a6c1a1DD9540F64f"},
    "USDC/USD": {"address": "0xdc339bBBFfab4ED48F387e2247f5e2a19EFD33D1"},
    "USDT/USD": {"address": "0xDea4B3Dd378DDeB434D3ed99E42F323E724776a8"},
    "ETH/USD": {"address": "0x89B341c29272bb8e769F237238E6176D9d55f57e"},
    "NEON/USD": {"address": "0xE587137a76dF04Bf25A9a83e681d6814f312500f"},
    "BTC/USD": {"address": "0x125BCeDd1C104024904E4Ee376c4B0e58620677C"},
    "JITOSOL/USD": {"address": "0xb7B6AF71eB684d2594EDC5Bc7812ad4937864561"},
    "MSOL/USD": {"address": "0xeafBBf2E99403516A28Bf6556477472580739c06"},
    "BONK/USD": {"address": "0xed78C14f68D65157b64C9Cf2FadD0b89f2043eD4"},
    "JUP/USD": {"address": "0x127063555ecF8B20aBFa6169fD3A70CeA30e17fB"},
    "INF/USD": {"address": "0x06D84D91d003013Bafc550f907A728413bfdb342"},
}


@allure.feature("Oracles")
@allure.story("Pyth network")
@pytest.mark.usefixtures("web3_client")
class TestPyth:
    web3_client: NeonChainWeb3Client

    def get_pyth_contract(self, address):
        contract = self.web3_client.get_deployed_contract(
            address,
            "external/neon-contracts/contracts/oracles/Pyth/PythAggregatorV3.sol",
            "PythAggregatorV3",
            "0.8.28",
            REMAPPING_ZEPPELIN,
        )
        return contract

    @pytest.mark.only_devnet
    def test_get_pyth_prices(self):
        for _, pair in PRICES_DEVNET.items():
            print("Pair: ", pair)
            contract = self.get_pyth_contract(pair["address"])
            price = contract.functions.latestAnswer().call()
            assert price is not None
