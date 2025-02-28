import json
import string
import random
import base58
import os
import argparse

from solders.keypair import Keypair
from utils.erc20wrapper import ERC20NewWrapper
from utils.faucet import Faucet
from utils.web3client import NeonChainWeb3Client
from utils.solana_client import SolanaClient
from utils.evm_loader import EvmLoader
from utils.consts import LAMPORT_PER_SOL
from clickfile import EXTERNAL_CONTRACT_PATH

REMAPPING_ZEPPELIN = {"@openzeppelin": str(EXTERNAL_CONTRACT_PATH / "neon-contracts/node_modules/@openzeppelin")}


parser = argparse.ArgumentParser(
    description="deploy erc20 contract for load tests", formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
parser.add_argument("-n", "--network", help="network to deploy the contract")
args = parser.parse_args()
config = vars(args)

with open("envs.json", "r") as f:
    credentials = json.load(f)

network = config["network"]
environment = credentials[network]

sol_client = SolanaClient(environment["solana_url"])
web3_client = NeonChainWeb3Client(environment["proxy_url"])
faucet = Faucet(environment["faucet_url"], web3_client)

evm_loader = EvmLoader(
    program_id=environment["evm_loader"],
    endpoint=environment["solana_url"],
    neon_chain_id=environment["network_ids"]["neon"],
    sol_chain_id=environment["network_ids"]["sol"],
    neon_token_mint_str=environment["spl_neon_mint"],
)

# set bank account if needed
bank_account = None
if network != "local" and environment["use_bank"]:
    if network == "devnet":
        private_key = os.environ.get("BANK_PRIVATE_KEY")
    else:
        raise ValueError("set BANK_PRIVATE_KEY env variable")
    key = base58.b58decode(private_key)
    bank_account = Keypair.from_bytes(key)

# create solana account
solana_account = Keypair()
eth_account = web3_client.create_account_with_balance(faucet, bank_account=bank_account)
if network != "local" and environment["use_bank"]:
    evm_loader.send_sol(bank_account, solana_account.pubkey(), int(1 * LAMPORT_PER_SOL))
else:
    evm_loader.request_airdrop(solana_account.pubkey(), 1 * LAMPORT_PER_SOL)


# deploy a new erc20 contract
symbol = "".join([random.choice(string.ascii_uppercase) for _ in range(3)])
erc20 = ERC20NewWrapper(
    web3_client,
    faucet,
    f"Test {symbol}",
    symbol,
    sol_client,
    solana_account=solana_account,
    mintable=True,
    bank_account=bank_account,
    account=eth_account,
)
erc20.mint_tokens(erc20.account, erc20.account.address)

contract_info = {
    "address": erc20.contract.address,
    "owner_key": web3_client.to_hex(eth_account.key),
    "owner_address": eth_account.address,
    "symbol": symbol,
}

with open("./loadtesting/proxy/data/contract_info.json", "w+") as f:
    json.dump(contract_info, f)
