import os
import glob
import json
import subprocess
import typing as tp
import pathlib

import tabulate

from deploy.cli import faucet as faucet_cli

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


def deploy_infrastructure() -> dict:
    subprocess.check_call(f"terraform init {TF_ENV['TF_BACKEND_CONFIG']}", shell=True, env=TF_ENV, cwd=TF_CWD)
    subprocess.check_call("terraform apply --auto-approve=true", shell=True, env=TF_ENV, cwd=TF_CWD)
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
    infra = dict(solana_ip=solana_ip, proxy_ip=proxy_ip)
    set_github_env(infra)
    return infra


def destroy_infrastructure():
    subprocess.run(f"terraform init {TF_ENV['TF_BACKEND_CONFIG']}", shell=True, env=TF_ENV, cwd=TF_CWD)
    subprocess.run("terraform destroy --auto-approve=true", shell=True, env=TF_ENV, cwd=TF_CWD)


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


def print_report(directory):
    print("DIRECTORIES")
    print(os.listdir(str(pathlib.Path(directory))))
    print(subprocess.run(f"ls -la {directory}", shell=True))
    headers = ["Action", "Fee", "Cost in $"]
    out = {}
    reports = {}
    for path in glob.glob(str(pathlib.Path(directory) / "*-report.json")):
        with open(path, "r") as f:
            rep = json.load(f)
            reports[rep["name"]] = rep["actions"]

    for app in reports:
        out[app] = []
        for action in reports[app]:
            row = [action["name"]]
            fee = int(action["usedGas"]) * int(action["gasPrice"]) / 1000000000000000000
            row.append(fee)
            row.append(fee * NEON_COST)
            out[app].append(row)

    for app in out:
        print(f"Cost report for \"{app.title()}\" dApp")
        print("----------------------------------------")
        print(tabulate.tabulate(out[app], headers, tablefmt="simple_grid"))
