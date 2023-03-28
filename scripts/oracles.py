import time

from utils.web3client import NeonWeb3Client

web3_client = NeonWeb3Client("https://devnet.neonevm.org/solana", 245022926)

account = web3_client._web3.eth.account.from_key(
    "0x3ca872d3ab8bf75ad97a0c066e05252e775e6f1422d14d819ed13233fe6593e7"
)


def deploy_pyth():
    contract, _ = web3_client.deploy_and_get_contract(
        "./pyth/PythOracle", "0.8.0", account=account
    )
    print("Use Pyth deployed contract address for any pairs: ", contract.address)
    return contract


def deploy_chainlink():
    contract, _ = web3_client.deploy_and_get_contract(
        contract="./chainlink/ChainlinkOracle",
        version="0.8.15",
        account=account,
        constructor_args=[
            "0x502b9d5731648a1c61dcf689240e2d2c799393430d9f1d584e368ec4e5243c5f"
        ],
    )
    print(
        "Use Chainlink deployed contract address for BTC/USD pair: ", contract.address
    )
    return contract


def deploy_and_get_prices():
    pyth_contract = deploy_pyth()
    chainlink_contract = deploy_chainlink()
    for _ in range(3):
        print("Get prices for BTC/USD pair")
        pyth_price = pyth_contract.functions.getCurrentPrice(
            "0xf9c0172ba10dfa4d19088d94f5bf61d3b54d5bd7483a322a982e1373ee8ea31b"
        ).call()
        chainlink_price = chainlink_contract.functions.latestRoundData().call()
        print(
            f"Pyth price: {int(pyth_price[0]) / 100000000}   Chainlink price: {int(chainlink_price[1]) / 100000000}\n"
        )
        time.sleep(3)


if __name__ == "__main__":
    deploy_and_get_prices()
