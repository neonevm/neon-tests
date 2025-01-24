import os

from deploy.cli.network_manager import NetworkManager
from utils.faucet import Faucet
from utils.web3client import NeonChainWeb3Client
from utils.k6_prepare_tracer import TracerLoadTestsDataProducer


NETWORK = os.environ.get("NETWORK")
BANK_ACCOUNT_PRIVATE_KEY = os.environ.get("BANK_ACCOUNT_PRIVATE_KEY")
TRANSFERS = int(os.environ.get("TRANSFERS"))
CONTRACT_CALLS = int(os.environ.get("CONTRACT_CALLS"))
ITERATIVE_TXS = int(os.environ.get("ITERATIVE_TXS"))


network_manager = NetworkManager()
network_object = network_manager.get_network_object(NETWORK)
web3_client = NeonChainWeb3Client(proxy_url=network_object["proxy_url"])
faucet = Faucet(faucet_url=network_object['faucet_url'], web3_client=web3_client)

tracer_data_producer = TracerLoadTestsDataProducer(web3_client,
                                                    faucet,
                                                    network_object["solana_url"],
                                                    network_object["evm_loader"],
                                                    "\3",
                                                    BANK_ACCOUNT_PRIVATE_KEY)
tracer_data_producer.prepare_tracer(transfers_number=TRANSFERS, 
                                    contracts_calls_number=CONTRACT_CALLS,
                                    iterative_txs_number=ITERATIVE_TXS)