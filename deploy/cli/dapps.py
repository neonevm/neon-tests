import os
import subprocess
import typing as tp

from deploy.cli import faucet as faucet_cli

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


def get_github_envs() -> tp.Dict:
    """Read environments from GITHUB_ENV"""
    path = os.getenv("GITHUB_ENV", str())
    if os.path.exists(path):
        with open(path, "r") as env_file:
            envs = env_file.read().split("\n")
            return dict([env.split("=") for env in envs])


def deploy_infrastructure() -> dict:
    subprocess.check_call(f"terraform init {TF_ENV['TF_BACKEND_CONFIG']}", shell=True, env=TF_ENV, cwd=TF_CWD)
    subprocess.check_call("terraform apply --auto-approve=true", shell=True, env=TF_ENV, cwd=TF_CWD)
    proxy_ip = subprocess.run(
        "terraform output --json | jq -r '.proxy_ip.value'",
        shell=True,
        env=TF_ENV,
        cwd="deploy/aws",
        stdout=subprocess.PIPE,
    ).stdout.strip()
    solana_ip = subprocess.run(
        "terraform output --json | jq -r '.solana_ip.value'",
        shell=True,
        env=TF_ENV,
        cwd="deploy/aws",
        stdout=subprocess.PIPE,
    ).stdout.strip()
    infra = dict(solana_ip=solana_ip, proxy_ip=proxy_ip)
    set_github_env(infra)
    return infra


def destroy_infrastructure():
    subprocess.run(f"terraform init {TF_ENV['TF_BACKEND_CONFIG']}", shell=True, env=TF_ENV, cwd=TF_CWD)
    subprocess.run("terraform destroy --auto-approve=true", shell=True, env=TF_ENV, cwd=TF_CWD)


def prepare_accounts(count, amount):
    print(f"{30*'_'} Readed envs: {get_github_envs()}")
    #network = {
    #    "proxy_url": f"http://{os.environ.get('PROXY_IP')}:9090/solana",
    #    "network_id": 111,
    #    "solana_url": f"http://{os.environ.get('SOLANA_IP')}:8899/",
    #    "faucet_url": f"http://{os.environ.get('PROXY_IP')}:3333/",
    #}
    #accounts = faucet_cli.prepare_wallets_with_balance(network, count, amount)
    #if os.environ.get("CI"):
    #    subprocess.run(f'echo "::set-output name=accounts::{",".join(accounts)}"')
