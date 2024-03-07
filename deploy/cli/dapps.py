import os
import glob
import json
import re
import subprocess
import sys
import typing as tp
import pathlib
import logging

import tabulate
from paramiko.client import SSHClient
from scp import SCPClient

from deploy.cli.network_manager import NetworkManager

from solana.transaction import Signature
from deploy.cli import faucet as faucet_cli
from utils.web3client import NeonChainWeb3Client
from utils.solana_client import SolanaClient
from utils.prices import get_neon_price
from python_terraform import Terraform


TFSTATE_BUCKET = os.environ.get("TFSTATE_BUCKET")
TFSTATE_KEY_PREFIX = os.environ.get("TFSTATE_KEY_PREFIX")
TFSTATE_REGION = os.environ.get("TFSTATE_REGION")
TF_STATE_KEY = f"{TFSTATE_KEY_PREFIX}neon-tests-{os.environ.get('GITHUB_RUN_ID', '0')}"
TF_BACKEND_CONFIG = {"bucket": TFSTATE_BUCKET, "key": TF_STATE_KEY, "region": TFSTATE_REGION}

os.environ["TF_VAR_branch"] = "develop"
os.environ["TF_VAR_proxy_image_tag"] = os.environ.get("NEON_PROXY_TAG", "latest")
os.environ["TF_VAR_proxy_model_commit"] = os.environ.get("PROXY_MODEL_COMMIT", "develop")
os.environ["TF_VAR_run_number"] = os.environ.get("GITHUB_RUN_ID", "0")
os.environ["TF_VAR_neon_evm_commit"] = os.environ.get("NEON_EVM_TAG", "latest")
os.environ["TF_VAR_faucet_model_commit"] = os.environ.get("NEON_FAUCET_TAG", "latest")
os.environ["TF_VAR_dockerhub_org_name"] = os.environ.get("DOCKERHUB_ORG_NAME", "neonlabsorg")
terraform = Terraform(working_dir=pathlib.Path(__file__).parent.parent / "hetzner")
NETWORK_MANAGER = NetworkManager()

REPORT_HEADERS = ["Action", "Fee", "Cost in $", "Accounts", "TRx", "Estimated Gas", "Used Gas", "Used % of EG"]


def set_github_env(envs: tp.Dict, upper=True) -> None:
    """Set environment for github action"""
    path = os.getenv("GITHUB_ENV", str())
    if os.path.exists(path):
        with open(path, "a") as env_file:
            for key, value in envs.items():
                env_file.write(f"\n{key.upper() if upper else key}={str(value)}")


def deploy_infrastructure() -> dict:
    terraform.init(backend_config=TF_BACKEND_CONFIG)
    return_code, stdout, stderr = terraform.apply(skip_plan=True)
    print(f"code: {return_code}")
    print(f"stdout: {stdout}")
    print(f"stderr: {stderr}")
    with open(f"terraform.log", "w") as file:
        file.write(stdout)
        file.write(stderr)
    if return_code != 0:
        print("Terraform infrastructure is not built correctly")
        sys.exit(1)
    output = terraform.output(json=True)
    print(f"output: {output}")
    proxy_ip = output["proxy_ip"]["value"]
    solana_ip = output["solana_ip"]["value"]

    infra = dict(solana_ip=solana_ip, proxy_ip=proxy_ip)
    set_github_env(infra)
    return infra


def destroy_infrastructure():
    log = logging.getLogger()
    log.handlers = []
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)4s %(name)4s [%(filename)s:%(lineno)s - %(funcName)s()] %(levelname)4s %(message)4s"
    )
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.INFO)

    def format_tf_output(output):
        return re.sub(r"(?m)^", " " * TF_OUTPUT_OFFSET, str(output))

    TF_OUTPUT_OFFSET = 16
    terraform.init(backend_config=TF_BACKEND_CONFIG)
    tf_destroy = terraform.apply("-destroy", skip_plan=True)
    log.info(format_tf_output(tf_destroy))


def download_remote_docker_logs():
    proxy_ip = os.environ.get("PROXY_IP")
    solana_ip = os.environ.get("SOLANA_IP")

    home_path = os.environ.get("HOME")
    artifact_logs = "./logs"
    ssh_key = "/tmp/ci-stands"
    os.mkdir(artifact_logs)
    if not os.path.exists(f"{home_path}/.ssh"):
        os.mkdir(f"{home_path}/.ssh")

    subprocess.run(f"ssh-keyscan -H {solana_ip} >> {home_path}/.ssh/known_hosts", shell=True)
    subprocess.run(f"ssh-keyscan -H {proxy_ip} >> {home_path}/.ssh/known_hosts", shell=True)

    ssh_client = SSHClient()
    ssh_client.load_system_host_keys()
    ssh_client.connect(solana_ip, username="root", key_filename=ssh_key, timeout=120)

    upload_service_logs(ssh_client, "solana", artifact_logs)

    ssh_client.connect(proxy_ip, username="root", key_filename=ssh_key, timeout=120)
    services = ["postgres", "dbcreation", "indexer", "proxy", "faucet"]
    for service in services:
        upload_service_logs(ssh_client, service, artifact_logs)


def upload_service_logs(ssh_client, service, artifact_logs):
    scp_client = SCPClient(transport=ssh_client.get_transport())
    print(f"Upload logs for service: {service}")
    ssh_client.exec_command(f"touch /tmp/{service}.log.bz2")
    stdin, stdout, stderr = ssh_client.exec_command(
        f"sudo docker logs {service} 2>&1 | pbzip2 -f > /tmp/{service}.log.bz2"
    )
    print(stdout.read())
    print(stderr.read())
    scp_client.get(f"/tmp/{service}.log.bz2", artifact_logs)


def prepare_accounts(network_name, count, amount) -> tp.List:
    network = NETWORK_MANAGER.get_network_object(network_name)
    accounts = faucet_cli.prepare_wallets_with_balance(network, count, amount)
    if os.environ.get("CI"):
        set_github_env(dict(accounts=",".join(accounts)))
    return accounts


def get_solana_accounts_in_tx(eth_transaction):
    network = os.environ.get("NETWORK")
    solana_url = NETWORK_MANAGER.get_network_param(network, "solana_url")
    proxy_url = NETWORK_MANAGER.get_network_param(network, "proxy_url")
    sol_client = SolanaClient(solana_url)
    web3_client = NeonChainWeb3Client(proxy_url)
    trx = web3_client.get_solana_trx_by_neon(eth_transaction)
    tr = sol_client.get_transaction(Signature.from_string(trx["result"][0]), max_supported_transaction_version=0)
    if tr.value.transaction.transaction.message.address_table_lookups:
        alt = tr.value.transaction.transaction.message.address_table_lookups
        return len(alt[0].writable_indexes) + len(alt[0].readonly_indexes), len(trx["result"])
    else:
        return len(tr.value.transaction.transaction.message.account_keys), len(trx["result"])


def prepare_report_data(directory):
    proxy_url = NETWORK_MANAGER.get_network_param(os.environ.get("NETWORK"), "proxy_url")
    web3_client = NeonChainWeb3Client(proxy_url)
    out = {}
    reports = {}
    for path in glob.glob(str(pathlib.Path(directory) / "*-report.json")):
        with open(path, "r") as f:
            rep = json.load(f)
            if type(rep) is list:
                for r in rep:
                    if "actions" in r:
                        reports[r["name"]] = r["actions"]
            else:
                if "actions" in rep:
                    reports[rep["name"]] = rep["actions"]

    for app in reports:
        out[app] = []
        for action in reports[app]:
            accounts, trx = get_solana_accounts_in_tx(action["tx"])
            tx = web3_client.get_transaction_by_hash(action["tx"])
            estimated_gas = int(tx.gas) if tx and tx.gas else None
            used_gas = int(action["usedGas"])
            row = [action["name"]]
            fee = used_gas * int(action["gasPrice"]) / 1000000000000000000
            used_gas_percentage = round(used_gas * 100 / estimated_gas, 2) if estimated_gas else None
            row.append(fee)
            row.append(fee * get_neon_price())
            row.append(accounts)
            row.append(trx)
            row.append(estimated_gas)
            row.append(used_gas)
            row.append(used_gas_percentage)
            out[app].append(row)
    return out


def print_report(data):
    report_content = ""
    for app in data:
        report_content += f'Cost report for "{app.title()}" dApp\n'
        report_content += "----------------------------------------\n"
        report_content += tabulate.tabulate(data[app], REPORT_HEADERS, tablefmt="simple_grid") + "\n"

    print(report_content)
    return report_content


def format_report_for_github_comment(data):
    headers = "| " + " | ".join(REPORT_HEADERS) + " |\n"
    headers += "| --- | --- | --- | --- | --- | --- | --- |--- |\n"
    report_content = ""

    for app in data:
        report_content += f'\nCost report for "{app.title()}" dApp\n\n'
        report_content += headers
        for action_data in data[app]:
            report_content += "| " + " | ".join([str(item) for item in action_data]) + " | " + "\n"
    return report_content
