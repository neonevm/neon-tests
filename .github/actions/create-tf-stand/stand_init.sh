#!/bin/bash

# Install docker
sudo apt-get update
sudo apt-get -y install docker.io
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod a+x /usr/local/bin/docker-compose
sudo chmod 666 /var/run/docker.sock

sudo apt-get -y install pbzip2

cd /tmp

whoami
pwd

echo "Print envs for debug"
echo "REVISION=$REVISION"
echo "SOLANA_URL=$SOLANA_URL"
echo "SOLANA_WS_URL=$SOLANA_WS_URL"
echo "NEON_EVM_COMMIT=$NEON_EVM_COMMIT"
echo "FAUCET_COMMIT=$FAUCET_COMMIT"
echo "CI_PP_SOLANA_URL=$CI_PP_SOLANA_URL"
echo "DOCKERHUB_ORG_NAME=$DOCKERHUB_ORG_NAME"
echo "DEVNET_SOLANA_URL=$DEVNET_SOLANA_URL"

export REVISION=$REVISION
export SOLANA_URL=$SOLANA_URL
export SOLANA_WS_URL=$SOLANA_WS_URL
export NEON_EVM_COMMIT=$NEON_EVM_COMMIT
export FAUCET_COMMIT=$FAUCET_COMMIT
export CI_PP_SOLANA_URL=$CI_PP_SOLANA_URL
export DOCKERHUB_ORG_NAME=$DOCKERHUB_ORG_NAME
export DEVNET_SOLANA_URL=$DEVNET_SOLANA_URL

cat > docker-compose-ci.override.yml<<EOF
version: "3"

services:
  solana:
    container_name: solana
    environment:
      DEVNET_SOLANA_URL: $DEVNET_SOLANA_URL
    ports:
      - "8899:8899"
      - "9900:9900"
      - "8900:8900"
      - "8001:8001"
      - "8001-8009:8001-8009/udp"
  
  nginx:
    image: nginx:latest
    ports:
      - "8080:8080"
    expose:
      - 8080
    hostname: nginx
    container_name: nginx
    volumes:
        - /var/log/nginx:/var/log/nginx
        - /tmp/nginx.conf:/etc/nginx/nginx.conf
    networks:
      - net
    entrypoint: >
      /bin/sh -c "echo 'Nginx Configuration:' && cat /etc/nginx/nginx.conf && nginx -g 'daemon off;'"

  proxy:
    container_name: proxy
    environment:
      SOLANA_URL: $SOLANA_URL
      SOLANA_WS_URL: $SOLANA_WS_URL
    ports:
      - "9090:9090"

  faucet:
    container_name: faucet
    environment:
      SOLANA_URL: $SOLANA_URL
    ports:
      - "3333:3333"

  indexer:
    container_name: indexer
    environment:
      SOLANA_URL: $SOLANA_URL
      SOLANA_WS_URL: $SOLANA_WS_URL

  postgres:
    container_name: postgres

  dbcreation:
    container_name: dbcreation
EOF

# wake up Solana
docker-compose -f docker-compose-ci.yml -f docker-compose-ci.override.yml up -d nginx solana

# Get list of services
SERVICES=$(docker-compose -f docker-compose-ci.yml -f docker-compose-ci.override.yml config --services | grep -vP "solana|gas_tank|neon_test_invoke_program_loader")

# Pull latest versions
docker-compose -f docker-compose-ci.yml -f docker-compose-ci.override.yml pull $SERVICES

function wait_service() {
  local SERVICE=$1
  local URL=$2
  local DATA=$3
  local RESULT=$4
  local SHOW_DOCKER_LOGS_IF_FAIL=$5

  # Max attepts is 100 (each for 2 seconds)
  local MAX_COUNT=100
  local CURRENT_ATTEMPT=1

  local CHECK_COMMAND="curl $URL -s -X POST -H 'Content-Type: application/json' -d '$DATA' | grep -cF '$RESULT'"

  while [[ $CURRENT_ATTEMPT -lt $MAX_COUNT ]]
  do
    echo "$SERVICE attempt: $CURRENT_ATTEMPT" 1>&2
    local CHECK_COMMAND_RESULT=$(eval $CHECK_COMMAND)
    echo $CHECK_COMMAND_RESULT >> /tmp/output.txt
    if [[ "$CHECK_COMMAND_RESULT" == "1" ]]; then
      echo "$SERVICE is up" 1>&2
      break
    fi

    ((CURRENT_ATTEMPT=CURRENT_ATTEMPT+1))
    sleep 2
  done;

  if [[ $CURRENT_ATTEMPT -eq $MAX_COUNT ]]; then
      echo ""
      echo "Service $SERVICE failed to respond as expected after $MAX_COUNT attempts."
      if [[ "$SHOW_DOCKER_LOGS_IF_FAIL" == "show_docker_logs_if_fail" ]]; then
        docker ps -a
        docker ps -a --format "{{.ID}} {{.Names}}" | while read -r id name; do
          echo ""
          echo "Logs for container: $name"
          docker logs "$id"
          echo ""
        done
      fi
      exit 1
  fi
}

# Check if Solana is available
SOLANA_DATA='{"jsonrpc":"2.0","id":1,"method":"getHealth"}'
SOLANA_RESULT='"ok"'
SOLANA_URL="http://localhost:8080"
wait_service "solana" $SOLANA_URL $SOLANA_DATA $SOLANA_RESULT


# Up all services
docker-compose -f docker-compose-ci.yml -f docker-compose-ci.override.yml up -d $SERVICES


# Check if Proxy is available
PROXY_URL="http://localhost:9090/solana"
PROXY_DATA='{"jsonrpc":"2.0","method":"eth_getBlockByNumber","params":["latest", false],"id":1}'
PROXY_RESULT='"number"'

wait_service "proxy" $PROXY_URL "$PROXY_DATA" $PROXY_RESULT "show_docker_logs_if_fail"
