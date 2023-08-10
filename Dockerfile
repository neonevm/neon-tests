FROM ubuntu:20.04

ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV NETWORK_NAME "full_test_suite"
ENV PROXY_URL ""
ENV NETWORK_ID ""
ENV FAUCET_URL ""
ENV SOLANA_URL ""
ENV FTS_JOBS_NUMBER 8
ENV FTS_USERS_NUMBER 15
ENV DUMP_ENVS True
ENV REQUEST_AMOUNT 20000
ARG DEBIAN_FRONTEND=noninteractive

# Install common dependencies
RUN apt update && \
    apt upgrade -y && \
    apt install -y software-properties-common python-dev curl git && \
# Install 18.x Node.js
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt install -y nodejs && \
# Install py3.10 from deadsnakes repository and pip from standard ubuntu packages
    add-apt-repository ppa:deadsnakes/ppa && apt update && \
    apt install -y python3.10 python3.10-distutils

RUN update-alternatives --install /usr/bin/python3 python /usr/bin/python3.10 2
RUN update-alternatives --install /usr/bin/python3 python /usr/bin/python3.8 1

# Install allure
RUN apt install default-jdk -y && \
    curl -o allure-2.21.0.tgz -Ls https://repo.maven.apache.org/maven2/io/qameta/allure/allure-commandline/2.21.0/allure-commandline-2.21.0.tgz && \
    tar -zxvf allure-2.21.0.tgz -C /opt/  && \
    ln -s /opt/allure-2.21.0/bin/allure /usr/bin/allure

# Install UI libs
RUN apt install -y libxkbcommon0 \
    libxdamage1 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    xvfb

COPY ./deploy/requirements/* /opt/
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10
RUN pip3 install -r /opt/prod.txt -r /opt/ui.txt
COPY ./deploy/oz/run-full-test-suite.sh /opt/neon-tests/

WORKDIR /opt/neon-tests
ADD ./ /opt/neon-tests
RUN python3 ./clickfile.py update-contracts

# Install UI requirements
RUN python3 ./clickfile.py requirements -d ui

ARG OZ_BRANCH=master

RUN chmod a+x run-full-test-suite.sh && \
# Update oz contracts
    git submodule init && git submodule update && \
    git submodule sync --recursive  && \
    git submodule update --init --recursive --remote && \
    git -C compatibility/openzeppelin-contracts checkout origin/${OZ_BRANCH}  && \
# Install oz tests requirements
    python3 clickfile.py requirements -d devel && \
    npm install --save-dev hardhat

# Download solc separatly as hardhat implementation is flucky
ENV DOWNLOAD_PATH="/root/.cache/hardhat-nodejs/compilers-v2/linux-amd64" \
    REPOSITORY_PATH="https://binaries.soliditylang.org/linux-amd64" \
    SOLC_BINARY="solc-linux-amd64-v0.7.6+commit.7338295f"
RUN mkdir -p ${DOWNLOAD_PATH} && \
    curl -o ${DOWNLOAD_PATH}/${SOLC_BINARY} ${REPOSITORY_PATH}/${SOLC_BINARY} && \
    curl -o ${DOWNLOAD_PATH}/list.json ${REPOSITORY_PATH}/list.json && \
    chmod -R 755 ${DOWNLOAD_PATH}

COPY deploy/infra/compile_contracts.sh compatibility/openzeppelin-contracts
RUN cd compatibility/openzeppelin-contracts npm set audit false
RUN cd compatibility/openzeppelin-contracts && npm ci
RUN cd compatibility/openzeppelin-contracts && ./compile_contracts.sh