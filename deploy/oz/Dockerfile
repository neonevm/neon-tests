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
RUN apt update && apt install -y software-properties-common python-dev curl git && \
# Install latest Node.js
curl -fsSL https://deb.nodesource.com/setup_current.x | bash - && \
apt install -y nodejs && \
# Install py3.8 from deadsnakes repository and pip from standard ubuntu packages
add-apt-repository ppa:deadsnakes/ppa && apt update && \
apt install -y python3.8 python3-pip && \
pip3 install click==8.0.3


COPY . /opt
COPY ./deploy/oz/run-full-test-suite.sh /opt
WORKDIR /opt

RUN chmod a+x run-full-test-suite.sh && \
# Update oz contracts
git submodule init && git submodule update && \
# Install oz tests requirements
python3 clickfile.py requirements -d devel && \
npm install --save-dev hardhat

ENTRYPOINT [ "./run-full-test-suite.sh" ]