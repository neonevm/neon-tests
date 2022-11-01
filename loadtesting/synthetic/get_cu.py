import os
import re
from solana.rpc.api import Client as SolanaClient


client = SolanaClient(os.environ.get("SOLANA_URL"))

block_height = client.get_slot()["result"]

for num in range(block_height-32, block_height):
    block = client.get_block(num)["result"]

    cu = 0

    for tr in block["transactions"]:
        res = re.findall(r"consumed (\d+) of (:?\d+) compute units", "".join(tr["meta"]["logMessages"]))
        if not res:
            continue
        cu += int(res[0][0])
    print(f"Transactions in block {num}: ", len(block["transactions"]))
    print("CU: ", cu)

