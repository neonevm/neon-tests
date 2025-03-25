import os


START_BLOCK = os.environ.get("START_BLOCK", 0)
FINISH_BLOCK = os.environ.get("FINISH_BLOCK", 1000)
PROXY_IP = os.environ.get("PROXY_IP", "127.0.0.1")

ENVS = [
    {"name": "indexer", "url": f"http://{PROXY_IP}:9090/solana"},
    {"name": "rust-indexer", "url": f"http://{PROXY_IP}:9091/solana"},
]
LOGS_PATH = "./indexers_diff"
