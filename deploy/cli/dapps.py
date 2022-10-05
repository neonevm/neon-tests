import os
import subprocess


TF_ENV = {
    "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY"),
    "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID"),
    "AWS_S3_BUCKET": os.environ.get("AWS_S3_BUCKET", "neon-tests-dapps"),
    "AWS_REGION": os.environ.get("AWS_REGION", "us-east-2"),
    "TF_VAR_branch": "develop",
    "TFSTATE_KEY": f"neon-tests/{os.environ.get('GITHUB_RUN_ID', '0')}",
    "TF_VAR_proxy_container_tag": os.environ.get("NEON_PROXY_TAG", "latest"),
    "TF_VAR_neon_evm_container_tag": os.environ.get("NEON_EVM_TAG", "latest"),
    "TF_VAR_faucet_container_tag": os.environ.get("NEON_FAUCET_TAG", "latest"),
}

TF_ENV.update(
    {
        "TF_BACKEND_CONFIG": f"-backend-config=\"bucket={TF_ENV['AWS_S3_BUCKET']}\" "
        f"-backend-config=\"key={TF_ENV['TFSTATE_KEY']}\" "
        f"-backend-config=\"region={TF_ENV['AWS_REGION']}\" ",
        "TFSTATE_BUCKET": TF_ENV["AWS_S3_BUCKET"],
        "TFSTATE_REGION": TF_ENV["AWS_REGION"],
    }
)


def deploy_infrastructure() -> dict:
    subprocess.run(f"terraform init {TF_ENV['TF_BACKEND_CONFIG']}", shell=True, env=TF_ENV, cwd="deploy/aws")
    subprocess.run("terraform apply --auto-approve=true", shell=True, env=TF_ENV, cwd="deploy/aws")
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
    subprocess.run(f'echo "SOLANA_IP={solana_ip} >> $GITHUB_ENV')
    subprocess.run(f"export SOLANA_IP={solana_ip}")
    subprocess.run(f'echo "PROXY_IP={proxy_ip} >> $GITHUB_ENV')
    subprocess.run(f"export PROXY_IP={proxy_ip}")

    return {"solana_ip": solana_ip, "proxy_ip": proxy_ip}


def destroy_infrastructure():
    subprocess.run(f"terraform init {TF_ENV['TF_BACKEND_CONFIG']}", shell=True, env=TF_ENV, cwd="deploy/aws")
    subprocess.run("terraform destroy --auto-approve=true", shell=True, env=TF_ENV, cwd="deploy/aws")
