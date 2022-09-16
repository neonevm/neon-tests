#!/bin/bash

### Clean infrastructure by terraform
export TF_VAR_branch="develop"
export TFSTATE_BUCKET="nl-neon-tests-dapps"
export TFSTATE_KEY="neon-tests/${GITHUB_RUN_ID}"
export TFSTATE_REGION="us-east-2"
export TF_BACKEND_CONFIG="-backend-config="bucket=${TFSTATE_BUCKET}" -backend-config="key=${TFSTATE_KEY}" -backend-config="region=${TFSTATE_REGION}""

export TF_VAR_proxy_container_tag=${NEON_PROXY_TAG}
export TF_VAR_neon_evm_container_tag=${NEON_EVM_TAG}
export TF_VAR_faucet_container_tag=${NEON_FAUCET_TAG}

terraform init $TF_BACKEND_CONFIG
terraform destroy --auto-approve=true