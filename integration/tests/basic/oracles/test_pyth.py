import allure
import pytest

from utils.web3client import NeonChainWeb3Client
from utils.consts import REMAPPING_ZEPPELIN


PYTH_MAINNET = {
    "SOL/USDC": "0x66d23fc4521d75613921f6475ce1776ed4a8f109",
    "USDC/USD": "0x94CDaE0758F7dA5EcA97646A665345BC20f72D53",
    "USDT/USD": "0xb22f95f4F203646ffe5752A5C1142A359c82cD47",
    "ETH/USD": "0x9ca5Ae7Fdc9Ef33fd8B86634678252Af052cF920",
    "NEON/USD": "0x5418Bd0bd3A43D6DcC486fb374a2346BE5e07A0D",
    "BTC/USD": "0x4359E879c83fB21e33BB62061bf22806873F06d6",
    "WBTC/USD": "0x8C96809746B45e1506007613d6Ec035cA41bEcB4",
    "JITOSOL/USD": "0x05CE377b7df379460EdEcB2baa3Ca18fB59b082C",
    "MSOL/USD": "0x47b1aD7a08D026a54DEd3d9C3935173FEdfbD2CF",
    "BONK/USD": "0x3d22FD7e59D19e08a6D5f55aD720549339fc8544",
    "JUP/USD": "0xD98d90B922C0a7112825232C7380B99176F090A7",
    "INF/USD": "0x4Ff8DfecEb1d29bbF58e92Cc9847fd20b51406aD",
}

PYTH_DEVNET = {
    "SOL/USDC": "0x19c6315fCb69aAE8eB74f0c8a6c1a1DD9540F64f",
    "USDC/USD": "0xdc339bBBFfab4ED48F387e2247f5e2a19EFD33D1",
    "USDT/USD": "0xDea4B3Dd378DDeB434D3ed99E42F323E724776a8",
    "ETH/USD": "0x89B341c29272bb8e769F237238E6176D9d55f57e",
    "NEON/USD": "0xE587137a76dF04Bf25A9a83e681d6814f312500f",
    "BTC/USD": "0x125BCeDd1C104024904E4Ee376c4B0e58620677C",
    "JITOSOL/USD": "0xb7B6AF71eB684d2594EDC5Bc7812ad4937864561",
    "MSOL/USD": "0xeafBBf2E99403516A28Bf6556477472580739c06",
    "BONK/USD": "0xed78C14f68D65157b64C9Cf2FadD0b89f2043eD4",
    "JUP/USD": "0x127063555ecF8B20aBFa6169fD3A70CeA30e17fB",
    "INF/USD": "0x06D84D91d003013Bafc550f907A728413bfdb342",
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

    def get_prices(self, pyth_addresses):
        for pair, address in pyth_addresses.items():
            contract = self.get_pyth_contract(address)
            price = contract.functions.latestAnswer().call()
            assert price is not None
            with allure.step(f"Pyth price for pair {pair} is {price}"):
                pass

    @pytest.mark.only_devnet
    def test_get_pyth_prices_devnet(self):
        self.get_prices(PYTH_DEVNET)

    @pytest.mark.mainnet
    def test_get_pyth_prices_mainnet(self):
        self.get_prices(PYTH_MAINNET)
