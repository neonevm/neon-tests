import os
import subprocess


TF_ENV = {
    "TF_VAR_branch": "develop",
    "TFSTATE_BUCKET": "neon-tests-dapps",
    "TFSTATE_KEY": f"neon-tests/{os.environ.get('GITHUB_RUN_ID', '0')}",
    "TFSTATE_REGION": "us-east-2",
    "TF_VAR_proxy_container_tag": os.environ.get("NEON_PROXY_TAG", "latest"),
    "TF_VAR_neon_evm_container_tag": os.environ.get("NEON_EVM_TAG", "latest"),
    "TF_VAR_faucet_container_tag": os.environ.get("NEON_FAUCET_TAG", "latest"),
}

TF_ENV["TF_BACKEND_CONFIG"] = f"-backend-config=\"{TF_ENV['TFSTATE_BUCKET']}\" -backend-config=\"key={TF_ENV['TFSTATE_KEY']}\" -backend-config=\"region={TF_ENV['TFSTATE_REGION']}\""


def deploy_infrastructure() -> dict:
    subprocess.run(f"terraform init {TF_ENV['TF_BACKEND_CONFIG']}", shell=True, env=TF_ENV, cwd="deploy/aws")
    subprocess.run("terraform apply --auto-approve=true", shell=True, env=TF_ENV, cwd="deploy/aws")
    proxy_ip = subprocess.run("terraform output --json | jq -r '.proxy_ip.value' >> $GITHUB_ENV",
                              shell=True, env=TF_ENV, cwd="deploy/aws")
    solana_ip = subprocess.run("terraform output --json | jq -r '.solana_ip.value' >> $GITHUB_ENV",
                               shell=True, env=TF_ENV, cwd="deploy/aws")
    subprocess.run(f'echo "SOLANA_IP={solana_ip} >> $GITHUB_ENV')
    subprocess.run(f'echo "PROXY_IP={proxy_ip} >> $GITHUB_ENV')

    return {
        "solana_ip": solana_ip,
        "proxy_ip": proxy_ip
    }


def destroy_infrastructure():
    subprocess.run(f"terraform init {TF_ENV['TF_BACKEND_CONFIG']}", shell=True, env=TF_ENV, cwd="deploy/aws")
    subprocess.run("terraform destroy --auto-approve=true", shell=True, env=TF_ENV, cwd="deploy/aws")
