import sys
import solcx
import requests
import pathlib

from utils.web3client import NeonWeb3Client

web3client = NeonWeb3Client("https://proxy.devnet.neonlabs.org/solana", 245022926)

account1 = web3client._web3.eth.account.from_key("0x719ded2b2bb4a5372460314e22e2fad03b0c197745f9832ff81e3f4afb733842")
account2 = web3client._web3.eth.account.from_key("0xcc4c52f87447901f366274ef445cc110f6916bea4c94ad7ea6f4a2a3ab0aa695")
account3 = web3client._web3.eth.account.from_key("0x0f11a3403a6a3fc6e60e081bf220d5af5da27184da5b6cd78b276b7a9f53ab28")


def get_contract_erc20_interface():
    contract_path = (
            pathlib.Path(__file__).parent / "integration" / "tests" / "economy" / "contracts" / "ERC20.sol"
    ).absolute()

    compiled = solcx.compile_files([contract_path], output_values=["abi", "bin"], solc_version="0.6.6")
    contract_interface = compiled["/Users/gigimon/workspaces/neon/neon-tests/integration/tests/economy/contracts/ERC20.sol:ERC20"]

    return contract_interface


def get_contract_payed_interface():
    contract_path = (
            pathlib.Path(__file__).parent / "integration" / "tests" / "economy" / "contracts" / "Payed.sol"
    ).absolute()

    compiled = solcx.compile_files([contract_path], output_values=["abi", "bin"], solc_version="0.6.6")
    contract_interface = compiled["/Users/gigimon/workspaces/neon/neon-tests/integration/tests/economy/contracts/Payed.sol:Payed"]

    return contract_interface


def prepare_all():
    # for acc in [account1, account2, account3]:
    #     resp = requests.post('https://neonswap.live/request_eth_token', json={
    #         "wallet": acc.address,
    #         "amount": 999
    #     })
    #     print(resp.text, resp.status_code)

    web3client.send_neon(account1, account2, 50, gas=1000000000)
    web3client.send_neon(account2, account3, 30, gas=1000000000)
    web3client.send_neon(account3, account1, 66, gas=1000000000)

    contract_interface = get_contract_erc20_interface()

    contract_deploy_tx = web3client.deploy_contract(
        account1,
        abi=contract_interface["abi"],
        bytecode=contract_interface["bin"],
        constructor_args=[1000],
        gas=1000000000
    )

    contract = web3client.eth.contract(
        address=contract_deploy_tx["contractAddress"], abi=contract_interface["abi"]
    )

    web3client.send_erc20(
        account1, account2, 234, contract_deploy_tx["contractAddress"], abi=contract.abi, gas=1000000000
    )

    print("ERC20 Contract address: ", contract_deploy_tx["contractAddress"])

    contract_interface = get_contract_payed_interface()

    contract_deploy_tx = web3client.deploy_contract(
        account1,
        abi=contract_interface["abi"],
        bytecode=contract_interface["bin"],
        gas=1000000000
    )

    contract = web3client.eth.contract(
        address=contract_deploy_tx["contractAddress"], abi=contract_interface["abi"]
    )
    print("Before ", web3client.get_balance(account1.address))
    instruction_tx = contract.functions.transferTo(account2.address).buildTransaction(  # 1086 steps in evm
            {
                "from": account1.address,
                "nonce": web3client.eth.get_transaction_count(account1.address),
                "gasPrice": 1000000000,
                "gas": 100000000000,
                "value": 1000000000
            }
        )

    instruction_receipt = web3client.send_transaction(account1, instruction_tx)

    print("After ", web3client.get_balance(account1.address))
    print("Payed Contract address: ", contract_deploy_tx["contractAddress"])

    print(f"Account 1 balance: {web3client.get_balance(account1.address)}")
    print(f"Account 2 balance: {web3client.get_balance(account2.address)}")
    print(f"Account 3 balance: {web3client.get_balance(account3.address)}")
    print(f"Account ERC20 balance: {contract.functions.balanceOf(account2.address).call()}")


def verify_migration():
    print(f"Account 1 balance: {web3client.get_balance(account1.address)}")
    print(f"Account 2 balance: {web3client.get_balance(account2.address)}")
    print(f"Account 3 balance: {web3client.get_balance(account3.address)}")

    contract_interface = get_contract_erc20_interface()
    contract = web3client.eth.contract(
        address=sys.argv[2], abi=contract_interface["abi"]
    )
    print(f"Account ERC20 balance: {contract.functions.balanceOf(account2.address).call()}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "prepare":
        prepare_all()
    elif cmd == "verify":
        verify_migration()
