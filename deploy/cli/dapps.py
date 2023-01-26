import os
import glob
import json
import subprocess
import typing as tp
import pathlib

import tabulate
from paramiko.client import SSHClient
from scp import SCPClient
from solana.transaction import Signature

from deploy.cli import faucet as faucet_cli
from utils.web3client import NeonWeb3Client
from utils.solana_client import SolanaClient


NEON_COST = 0.25

TF_CWD = "deploy/aws"

TF_ENV = {
    "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY"),
    "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID"),
    "AWS_S3_BUCKET": os.environ.get("AWS_S3_BUCKET", "neon-tests-dapps"),
    "AWS_REGION": os.environ.get("AWS_REGION", "us-east-2"),
    "TF_VAR_branch": "develop",
    "TF_VAR_proxy_container_tag": os.environ.get("NEON_PROXY_TAG", "latest"),
    "TF_VAR_neon_evm_container_tag": os.environ.get("NEON_EVM_TAG", "latest"),
    "TF_VAR_faucet_container_tag": os.environ.get("NEON_FAUCET_TAG", "latest"),
    "TF_STATE_KEY": f"neon-tests/{os.environ.get('GITHUB_RUN_ID', '0')}",
}

TF_ENV.update(
    {
        "TF_BACKEND_CONFIG": f"-backend-config=\"bucket={TF_ENV['AWS_S3_BUCKET']}\" "
        f"-backend-config=\"key={TF_ENV['TF_STATE_KEY']}\" "
        f"-backend-config=\"region={TF_ENV['AWS_REGION']}\" ",
    }
)


def set_github_env(envs: tp.Dict, upper=True) -> None:
    """Set environment for github action"""
    path = os.getenv("GITHUB_ENV", str())
    if os.path.exists(path):
        with open(path, "a") as env_file:
            for key, value in envs.items():
                env_file.write(f"\n{key.upper() if upper else key}={str(value)}")


def get_solana_ip() -> str:
    solana_ip = subprocess.run(
        "terraform output --json | jq -r '.solana_ip.value'",
        shell=True,
        env=TF_ENV,
        cwd="deploy/aws",
        stdout=subprocess.PIPE,
        text=True
    ).stdout.strip()
    if isinstance(solana_ip, bytes):
        solana_ip = solana_ip.decode()
    return solana_ip


def get_proxy_ip() -> str:
    proxy_ip = subprocess.run(
        "terraform output --json | jq -r '.proxy_ip.value'",
        shell=True,
        env=TF_ENV,
        cwd="deploy/aws",
        stdout=subprocess.PIPE,
        text=True
    ).stdout.strip()
    if isinstance(proxy_ip, bytes):
        proxy_ip = proxy_ip.decode()
    return proxy_ip


def deploy_infrastructure() -> dict:
    subprocess.check_call(f"terraform init {TF_ENV['TF_BACKEND_CONFIG']}", shell=True, env=TF_ENV, cwd=TF_CWD)
    subprocess.check_call("terraform apply --auto-approve=true", shell=True, env=TF_ENV, cwd=TF_CWD)
    proxy_ip = get_proxy_ip()
    solana_ip = get_solana_ip()
    infra = dict(solana_ip=solana_ip, proxy_ip=proxy_ip)
    set_github_env(infra)
    return infra


def destroy_infrastructure():
    subprocess.run(f"terraform init {TF_ENV['TF_BACKEND_CONFIG']}", shell=True, env=TF_ENV, cwd=TF_CWD)
    subprocess.run("terraform destroy --auto-approve=true", shell=True, env=TF_ENV, cwd=TF_CWD)


def download_remote_docker_logs():
    subprocess.run(f"terraform init {TF_ENV['TF_BACKEND_CONFIG']}", shell=True, env=TF_ENV, cwd=TF_CWD)
    proxy_ip = get_proxy_ip()
    solana_ip = get_solana_ip()

    home_path = os.environ.get("HOME")
    artifact_logs = "./logs"
    ssh_key = "/tmp/dapps-stand"
    os.mkdir(artifact_logs)
    if not os.path.exists(f"{home_path}/.ssh"):
        os.mkdir(f"{home_path}/.ssh")
    
    subprocess.run(
       f'ssh-keyscan -H {solana_ip} >> {home_path}/.ssh/known_hosts', shell=True)
    subprocess.run(
       f'ssh-keyscan -H {proxy_ip} >> {home_path}/.ssh/known_hosts', shell=True)
    ssh_client = SSHClient()
    ssh_client.load_system_host_keys()
    ssh_client.connect(solana_ip, username='ubuntu',
                       key_filename=ssh_key, timeout=120)

    upload_service_logs(ssh_client, "solana", artifact_logs)

    ssh_client.connect(proxy_ip, username='ubuntu',
                       key_filename=ssh_key, timeout=120)
    services = ["postgres", "dbcreation", "indexer", "proxy", "faucet"]
    for service in services:
        upload_service_logs(ssh_client, service, artifact_logs)


def upload_service_logs(ssh_client, service, artifact_logs):
    scp_client = SCPClient(transport=ssh_client.get_transport())
    print(f"Upload logs for service: {service}")
    ssh_client.exec_command(f"touch /tmp/{service}.log.bz2")
    stdin, stdout, stderr = ssh_client.exec_command(
        f'sudo docker logs {service} 2>&1 | pbzip2 -f > /tmp/{service}.log.bz2')
    print(stdout.read())
    print(stderr.read())
    scp_client.get(f'/tmp/{service}.log.bz2', artifact_logs)


def prepare_accounts(count, amount) -> tp.List:
    network = {
        "proxy_url": f"http://{os.environ.get('PROXY_IP')}:9090/solana",
        "network_id": 111,
        "solana_url": f"http://{os.environ.get('SOLANA_IP')}:8899/",
        "faucet_url": f"http://{os.environ.get('PROXY_IP')}:3333/",
    }
    accounts = faucet_cli.prepare_wallets_with_balance(network, count, amount)
    if os.environ.get("CI"):
        set_github_env(dict(accounts=",".join(accounts)))
    return accounts


def get_solana_accounts_in_tx(eth_transaction):
    web3_client = NeonWeb3Client(os.environ.get("PROXY_URL"), os.environ.get("CHAIN_ID", 111))
    sol_client = SolanaClient(os.environ.get("SOLANA_URL"))
    trx = web3_client.get_solana_trx_by_neon(eth_transaction)
    tr = sol_client.get_transaction(Signature.from_string(trx["result"][0]), max_supported_transaction_version=0)
    if tr.value.transaction.transaction.message.address_table_lookups:
        alt = tr.value.transaction.transaction.message.address_table_lookups
        return len(alt[0].writable_indexes) + len(alt[0].readonly_indexes), len(trx["result"])
    else:
        return len(tr.value.transaction.transaction.message.account_keys), len(trx["result"])


def print_report(directory):
    headers = ["Action", "Fee", "Cost in $", "Accounts", "TRx"]
    out = {}
    reports = {}
    for path in glob.glob(str(pathlib.Path(directory) / "*-report.json")):
        with open(path, "r") as f:
            rep = json.load(f)
            reports[rep["name"]] = rep["actions"]

    for app in reports:
        out[app] = []
        for action in reports[app]:
            accounts, trx = get_solana_accounts_in_tx(action["tx"])
            row = [action["name"]]
            fee = int(action["usedGas"]) * int(action["gasPrice"]) / 1000000000000000000
            row.append(fee)
            row.append(fee * NEON_COST)
            row.append(accounts)
            row.append(trx)
            out[app].append(row)

    for app in out:
        print(f"Cost report for \"{app.title()}\" dApp")
        print("----------------------------------------")
        print(tabulate.tabulate(out[app], headers, tablefmt="simple_grid"))
