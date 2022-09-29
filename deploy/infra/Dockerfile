FROM python:3.8.10-slim-buster

ENV HOME_DIR /neon-tests

COPY . ${HOME_DIR}
COPY ./deploy/infra/devbox/install-packages /usr/local/bin

# Install Tools:
RUN apt-get update && apt-get install -y --no-install-recommends git vim mc curl less rsync ssh unzip \
# Install C libraries
&& install-packages \
    libffi6 \
    libssh2-1 \
    libxml2 \
    libxslt1.1 \
    libssl1.1;

# C Build dependencies
ENV PIP_BUILD_DEPENDENCIES \
    gcc make \
    libffi-dev \
    libssh2-1-dev \
    libxml2-dev \
    libxslt1-dev \
    libssl-dev \
    libzmq3-dev \
    zlib1g-dev

ENV PATH /usr/local/bin:${PATH}

# PIP Build dependencies and several helpful packages:
RUN apt-get update && apt-get install -qy --no-install-recommends ${PIP_BUILD_DEPENDENCIES} ;

# Install PIP requirements
RUN python3 -m ensurepip \
  && pip install -U --upgrade-strategy=only-if-needed wheel pip pip-tools \
  && pip install --upgrade \
  -r ${HOME_DIR}/deploy/requirements/prod.txt \
  -r ${HOME_DIR}/deploy/requirements/devel.txt \
  -r ${HOME_DIR}/deploy/requirements/ui.txt \
  #-r ${HOME_DIR}/deploy/requirements/nodeps.txt \
  --src=/usr/local/lib/python3.8/site-packages ;

# Fixes for ctypes.cdll.LoadLibrary:
# They must go after cleanup, or `apt-get purge $PIP_BUILD_DEPENDENCIES`
# will destroy symlinks while removing libssh-dev.
RUN [ ! -L "/usr/lib/x86_64-linux-gnu/libssh2.so" ] || ln -sf libssh2.so.1 /usr/lib/x86_64-linux-gnu/libssh2.so


# Install tfenv fo terraform using in devbox
RUN git clone --depth=1 https://github.com/tfutils/tfenv.git ~/.tfenv \
  && echo 'export PATH="$HOME/.tfenv/bin:$PATH"' >> ~/.bash_profile \
  && ln -s ~/.tfenv/bin/* /usr/local/bin

# Cleanup:
## Git cache saves ~ 1min on pip-sync
RUN find /usr/local/lib/python3.8/site-packages -name .git | xargs rm -rf \
  && apt-get -y autoremove && rm -rf /var/lib/apt/lists/* \
  && rm -rf /usr/local/bin/__pycache__ \
  && find /usr/local/lib/python3.8 -name __pycache__ | xargs rm -rf \
  && rm -rf /root/.cache;

RUN cd ${HOME_DIR} && git submodule init && git submodule update

ENV PYTHONPATH ${HOME_DIR}
WORKDIR ${HOME_DIR}

EXPOSE 8089/tcp
