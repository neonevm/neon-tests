__doc__ = """
    1. copy operator keypair json files from deploy/operator-keypairs to id.json/
    2. copy the contents of this dir to a remote server
        scp -r ./ <ssh_user>@<ip>:~/docker-compose/bestarch/
    3. spin the env
        cd docker-compose/bestarch
        chmod +x start.sh
        ./start.sh
    4. run tests against this server with env
        "proxy_url": "http://<ssh_host>:9090/solana",
        "network_ids": {
          "neon": 111,
        },
        "solana_url": "http://<ssh_host>:8899/",
        "faucet_url": "http://<ssh_host>:3333/",
    5. set global vars
        ssh_host = ...
        ssh_user = ...
        ssh_private_key_path = ...
    6. run the script
"""

import os
import json
import pathlib
import base58
import pprint

import psycopg2
from matplotlib import pyplot as plt
from solders.keypair import Keypair
from sshtunnel import SSHTunnelForwarder

from utils.logger import create_logger

ssh_host = ""
ssh_port = 22
ssh_user = ""
ssh_password = ""
ssh_private_key_path = ""

db_host = "localhost"
db_port = 5432
db_user = "neon-proxy"
db_password = "neon-proxy-pass"
db_name = "neon-db-bestarch"


logger = create_logger(__name__)


def get_operator_public_keys() -> set[str]:
    keys = set()
    parent = pathlib.Path(__file__).parent
    for file_name in os.listdir(parent / "id.json"):
        file_path = os.path.join("id.json", file_name)
        with open(file_path) as f:
            kp_data: list[int] = json.load(f)
            kp = Keypair.from_bytes(kp_data)
            pubkey = str(kp.pubkey())
            keys.add(pubkey)
    return keys


def main():
    operator_keys: set[str] = get_operator_public_keys()

    with SSHTunnelForwarder(
        (ssh_host, ssh_port),
        ssh_username=ssh_user,
        ssh_password=ssh_password,
        ssh_pkey=ssh_private_key_path,
        remote_bind_address=(db_host, db_port),
    ) as tunnel:
        conn = psycopg2.connect(
            dbname=db_name, user=db_user, password=db_password, host="127.0.0.1", port=tunnel.local_bind_port
        )
        cur = conn.cursor()

        cur.execute(
            """
                SELECT operator, COUNT(*) AS tx_count
                FROM solana_transaction_costs
                GROUP BY operator;
            """,
        )
        rows = cur.fetchall()

        distribution = dict()
        for row in rows:
            solana_public_key = base58.b58encode(bytes(row[0])).decode("utf-8")
            distribution[solana_public_key] = row[1]

        cur.close()
        conn.close()

        logger.info(pprint.pformat(distribution))

        assert set(distribution.keys()) == operator_keys, operator_keys.difference(set(distribution.keys()))

        height = list(distribution.values())
        plt.bar(
            x=range(1, len(height) + 1),
            height=height,
        )
        plt.show()


if __name__ == "__main__":
    main()
