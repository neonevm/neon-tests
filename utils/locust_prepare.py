import base58
import random
import string
import json
import os

from deploy.cli.network_manager import NetworkManager
from utils.web3client import NeonChainWeb3Client
from utils.consts import LAMPORT_PER_SOL
from solders.keypair import Keypair
from solana.rpc import commitment
from utils.erc20wrapper import ERC20NewWrapper
from utils.evm_loader import EvmLoader
from utils.neon_user import NeonUser
from utils.accounts import EthAccounts
from utils.faucet import Faucet


def prepare_locust(network, neon_users):
    network_manager = NetworkManager()
    network_object = network_manager.get_network_object(network)
    web3_client = NeonChainWeb3Client(proxy_url=network_object["proxy_url"])
    faucet = Faucet(faucet_url=network_object["faucet_url"], web3_client=web3_client)

    # set bank account if needed
    bank_account = None
    if network != "local" and network_object["use_bank"]:
        if network == "devnet":
            private_key = os.environ.get("BANK_PRIVATE_KEY")
        else:
            raise ValueError("set BANK_PRIVATE_KEY env variable")
        key = base58.b58decode(private_key)
        bank_account = Keypair.from_bytes(key)

    account_manager = EthAccounts(web3_client, faucet, bank_account)

    neon_user_balance = int(10**10 / neon_users)
    contract_info = {}

    evm_loader = EvmLoader(
        program_id=network_object["evm_loader"],
        endpoint=network_object["solana_url"],
        neon_chain_id=network_object["network_ids"]["neon"],
        sol_chain_id=network_object["network_ids"]["sol"],
        neon_token_mint_str=network_object["spl_neon_mint"],
    )

    # create solana account
    solana_account = Keypair()
    if network != "local" and network_object["use_bank"]:
        evm_loader.send_sol(bank_account, solana_account.pubkey(), int(1 * LAMPORT_PER_SOL))
    else:
        evm_loader.request_airdrop(solana_account.pubkey(), 1 * LAMPORT_PER_SOL)

    # create owner
    eth_account = account_manager.create_account()

    try:
        # deploy a new erc20 contract
        print("Start to deploy a contract...")
        symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
        erc20 = ERC20NewWrapper(
            web3_client,
            faucet,
            f"Test {symbol}",
            symbol,
            evm_loader,
            solana_account=solana_account,
            mintable=True,
            bank_account=bank_account,
            account=eth_account,
        )
        erc20.mint_tokens(erc20.account, erc20.account.address)

        contract_info["erc20_address"] = erc20.contract.address
        contract_info["erc20_owner_address"] = erc20.account.address

        neon_users_info = []
        for i in range(neon_users):
            neon_solana_account = Keypair()
            neon_users_info.append((bytes(neon_solana_account)).decode(encoding="raw_unicode_escape"))
            print(f"Creating {i} neon user...")
            neon_user = NeonUser(evm_loader.loader_id, keypair=neon_solana_account)
            balance = evm_loader.get_solana_balance(neon_user.solana_account.pubkey())
            if network not in ["devnet"]:
                if balance < 5 * LAMPORT_PER_SOL:
                    evm_loader.request_airdrop(
                        neon_user.solana_account.pubkey(), 5 * LAMPORT_PER_SOL, commitment=commitment.Confirmed
                    )
            print(f"Pop up {i} neon user balance...")
            erc20.pop_up_balance(
                evm_loader, recipient=neon_user, pda_amount=neon_user_balance, ata_amount=neon_user_balance
            )
            erc20.approve(erc20.account, neon_user.checksum_address, neon_user_balance)

        contract_info["neon_users"] = neon_users_info
    except Exception as e:
        print(f"Error in erc20 contract and neon users preparstion: {e}")
    finally:
        directory_path = "./loadtesting/proxy/data/"
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
        with open(directory_path + "scheduled_test_info.json", "w+") as f:
            json.dump(contract_info, f)
