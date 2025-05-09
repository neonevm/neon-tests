ARG DOCKER_HUB_ORG_NAME
ARG BASE_IMAGE_TAG

FROM ${DOCKER_HUB_ORG_NAME}/neon_tests_base:${BASE_IMAGE_TAG}

ENV TZ=Europe/Moscow \
    NETWORK_NAME="full_test_suite" \
    PROXY_URL="" \
    NETWORK_ID="" \
    FAUCET_URL="" \
    SOLANA_URL="" \
    FTS_JOBS_NUMBER=8 \
    FTS_USERS_NUMBER=15 \
    DUMP_ENVS=True \
    REQUEST_AMOUNT=20000 \
    VIRTUAL_ENV=/.venv \
    PATH="$VIRTUAL_ENV/bin:$PATH"

RUN apt-get update && apt-get upgrade -y
# Add source code last as it's most likely to change
ADD ./ /opt/neon-tests
