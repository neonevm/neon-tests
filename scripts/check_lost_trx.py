import itertools
import json
import pathlib
import glob
from concurrent.futures import ThreadPoolExecutor

from solana.transaction import Signature

from utils.web3client import NeonChainWeb3Client
from utils.solana_client import SolanaClient

NETWORK_NAME = "testnet"
BASE_PATH = pathlib.Path(__file__).parent.parent


def load_creds(network_name):
    with open(BASE_PATH / "envs.json", "r") as f:
        creds = json.load(f)
    return creds[network_name]


def get_web3_clients():
    creds = load_creds(NETWORK_NAME)
    w = NeonChainWeb3Client(creds["proxy_url"])
    s = SolanaClient(creds["solana_url"])
    return w, s


def load_transactions_list():
    txs = {}
    for f in BASE_PATH.glob("transactions-*"):
        with open(f, "r") as fp:
            txs = json.load(fp)
    return txs


def check_neon_tx(tx, web3_client: NeonChainWeb3Client):
    try:
        web3_client._web3.eth.get_transaction_receipt(tx)
        return True
    except Exception as e:
        print(f"TX: {tx} is not found")
        return False


def check_sol_tx(tx, solana_client: SolanaClient):
    res = solana_client.get_transaction(Signature.from_string(tx))
    if res.value is None:
        print(f"Solana TRx {tx} not found")
        return False
    return True


def run():
    txs = load_transactions_list()
    w3, sol = get_web3_clients()
    success_neon = 0
    success_sol = 0

    print("Start check NEON txs")
    with ThreadPoolExecutor(10) as executor:
        for res in executor.map(check_neon_tx, txs.keys(), [w3]*len(txs)):
            if res is True:
                success_neon += 1

    sol_txs = list(itertools.chain(*txs.values()))
    print("Start check Solana txs")
    with ThreadPoolExecutor(10) as executor:
        for res in executor.map(check_sol_tx, sol_txs, [sol]*len(txs)):
            if res is True:
                success_sol += 1
    print(f"NEON TX count: {len(txs)}, success got receipts: {success_neon}")
    print(f"SOL TX count: {len(sol_txs)}, success got receipts: {success_sol}")


if __name__ == "__main__":
    run()
