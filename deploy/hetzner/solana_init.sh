#!/bin/bash


# Install docker
sudo apt-get remove docker docker-engine docker.io containerd runc
sudo apt-get update
sudo apt-get -y install ca-certificates curl gnupg lsb-release pbzip2
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update


# Tune instance for Solana requirements(must be applied before start services)
sudo bash -c "cat >/etc/sysctl.d/20-solana-udp-buffers.conf<<EOF
# Increase UDP buffer size
net.core.rmem_default = 134217728
net.core.rmem_max = 134217728
net.core.wmem_default = 134217728
net.core.wmem_max = 134217728
EOF"
sysctl -p /etc/sysctl.d/20-solana-udp-buffers.conf

sudo bash -c "cat >/etc/sysctl.d/20-solana-mmaps.conf<<EOF
# Increase memory mapped files limit
vm.max_map_count = 1000000
EOF"
sysctl -p /etc/sysctl.d/20-solana-mmaps.conf

bash -c "cat >/etc/security/limits.d/90-solana-nofiles.conf<<EOF
# Increase process file descriptor count limit
* - nofile 1000000
EOF"


# Install docker-compose
sudo apt-get -y install docker-ce docker-ce-cli containerd.io
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

export REVISION=${proxy_image_tag}
export NEON_EVM_COMMIT=${neon_evm_commit}
export FAUCET_COMMIT=${faucet_model_commit}
export DOCKERHUB_ORG_NAME=${dockerhub_org_name}
export PROXY_IMAGE_NAME="neon-proxy.py"

# Receive docker-compose file and create override file
cd /opt
curl -O https://raw.githubusercontent.com/${dockerhub_org_name}/neon-proxy.py/${proxy_model_commit}/docker-compose/docker-compose-ci.yml
cat > docker-compose-ci.override.yml<<EOF
version: "3"
services:
  solana:
    ports:
      - "8899:8899"
      - "8900:8900"
    networks:
      - net
  neon-core-api:
    container_name: neon-core-api
    restart: unless-stopped
    hostname: neon_api
    entrypoint:
      /opt/neon-api -H 0.0.0.0:8085
    environment:
      RUST_BACKTRACE: 1
      RUST_LOG: debug
      NEON_API_LISTENER_ADDR: 0.0.0.0:8085
      SOLANA_URL: http://solana:8899
      EVM_LOADER: 53DfF883gyixYNXnM7s5xhdeyV8mVk9T4i2hGV9vG9io
      SOLANA_KEY_FOR_CONFIG: BMp6gEnveANdvSvspESJUrNczuHz1GF5UQKjVLCkAZih
      COMMITMENT: confirmed
      NEON_DB_CLICKHOUSE_URLS: "http://45.250.253.36:8123;http://45.250.253.38:8123"
    image: $DOCKERHUB_ORG_NAME/evm_loader:$NEON_EVM_COMMIT
    ports:
    - "8085:8085"
    expose:
    - "8085"
    networks:
      - net
  neon-core-rpc:
    restart: unless-stopped
    container_name: neon-core-rpc
    hostname: neon_core_rpc
    entrypoint: /opt/neon-rpc /opt/libs/current
    environment:
      RUST_BACKTRACE: full
      RUST_LOG: neon=debug
      NEON_API_LISTENER_ADDR: 0.0.0.0:3100
      SOLANA_URL: http://solana:8899
      EVM_LOADER: 53DfF883gyixYNXnM7s5xhdeyV8mVk9T4i2hGV9vG9io
      NEON_TOKEN_MINT: HPsV9Deocecw3GeZv1FkAPNCBRfuVyfw9MMwjwRe1xaU
      NEON_CHAIN_ID: 111
      COMMITMENT: confirmed
      NEON_DB_CLICKHOUSE_URLS: "http://45.250.253.36:8123;http://45.250.253.38:8123"
      NEON_DB_INDEXER_HOST: 45.250.253.32
      NEON_DB_INDEXER_PORT: 5432
      NEON_DB_INDEXER_DATABASE: indexer
      NEON_DB_INDEXER_USER: postgres
      NEON_DB_INDEXER_PASSWORD: "vUlpDyAP0gA98R5Bu"
      KEYPAIR: /opt/operator-keypairs/id.json
      FEEPAIR: /opt/operator-keypairs/id.json
    image: $DOCKERHUB_ORG_NAME/evm_loader:$NEON_EVM_COMMIT
    ports:
      - "3100:3100"
    expose:
      - "3100"
    networks:
      - net
EOF


# wake up Solana
docker-compose -f docker-compose-ci.yml -f docker-compose-ci.override.yml pull solana
docker-compose -f docker-compose-ci.yml -f docker-compose-ci.override.yml up -d solana neon-core-api neon-core-rpc
