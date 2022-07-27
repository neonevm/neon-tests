# Quick reference

* **Maintained by:**: The [Neon Labs company](https://neon-labs.org/)
* **Where to get help**: [Dicscord channel](https://discord.com/channels/839825320639332362), [Twitter](https://twitter.com/neonlabsorg), [GitHub](https://github.com/neonlabsorg)

# Supported tags and respective `Dockerfile` links

* [develop](https://github.com/neonlabsorg/neon-tests/deploy/oz/Dockerfile)

# Quick reference
* **Where to file issues**: https://github.com/neonlabsorg/neon-compatibility/issues
* **Supported architectures**: ([more info](https://github.com/docker-library/official-images#architectures-other-than-amd64)) [`amd64`](https://hub.docker.com/r/amd64/node/), [`arm32v6`](https://hub.docker.com/r/arm32v6/node/), [`arm32v7`](https://hub.docker.com/r/arm32v7/node/), [`arm64v8`](https://hub.docker.com/r/arm64v8/node/), [`ppc64le`](https://hub.docker.com/r/ppc64le/node/), [`s390x`](https://hub.docker.com/r/s390x/node/)
* **Published image artifact details**: 
* **Image updates**: [official image repo's `full_test_suite` label](https://github.com/neonlabsorg/neon-compatibility/pulls?q=label%3Afull_test_suite)
* **Source of this description**: [docs repo's `full_test_suite/` directory](https://github.com/neonlabsorg/neon-compatibility/tree/develop/full_test_suite) ([history](https://github.com/neonlabsorg/neon-compatibility/commits/develop/full_test_suite))

## What is Neon Full Test Suite?

Neon Full Test Suite contains and run a big variety of different tests to check if all the tests are passed successfully. Currently it checks if the actual count is greater than predefined threshold.

### Example output
```
...
Full test passing - 1734
Full test threshold - 1700
Check if 1734 is greater or equeal 1700
...
```

## How to use this image

It can be used with the `docker-compose.yml` file.
As an option you can define your own configuration as the `.env` file and pass it with --env-file docker-compose option.

#### Running docker-compose

```sh
$ docker-compose -f docker-compose.yml --env-file night.env pull
$ docker-compose -f docker-compose.yml --env-file night.env up
```

This reference present two `.env` configurations: for night stand and for local workspace

### local.env

```ini
NETWORK_NAME=local
PROXY_URL=http://proxy:9090/solana
NETWORK_ID=111
REQUEST_AMOUNT=20000
FAUCET_URL=http://faucet:3333/request_neon
USE_FAUCET=true
SOLANA_URL=http://solana:8899
USERS_NUMBER=15
JOBS_NUMBER=8
```

#### docker-compose.yml
```yaml
version: "3"

services:
  full_test_suite:
    container_name: full_test_suite
    image: neonlabsorg/full_test_suite:583-full-test-suite
    entrypoint: ./run-full-test-suite.sh 2>&1
    environment:
      - NETWORK_NAME=${NETWORK_NAME}
      - PROXY_URL=${PROXY_URL}
      - NETWORK_ID=${NETWORK_ID}
      - REQUEST_AMOUNT=${REQUEST_AMOUNT}
      - FAUCET_URL=${FAUCET_URL}
      - USE_FAUCET=${USE_FAUCET}
      - SOLANA_URL=${SOLANA_URL}
      - USERS_NUMBER=${USERS_NUMBER}
      - JOBS_NUMBER=${JOBS_NUMBER}

    networks:
      - net

networks:
  net:
    external: yes
    name: local
```


# Image Variants

* [develop](https://hub.docker.com/layers/195749203/neonlabsorg/full_test_suite/develop/images/sha256-de8ae2d4e4f31779f1960ce013f3de9135c0a19b6c5052c3ec2644247c50e01c?context=repo)

License

View license information for [Full Test Suite](https://github.com/neonlabsorg/neon-compatibility/blob/develop/LICENSE) in [neonlabsorg/neon-compatibility](https://github.com/neonlabsorg/neon-compatibility/) project.

As with all Docker images, these likely also contain other software which may be under other licenses (such as Bash, etc from the base distribution, along with any direct or indirect dependencies of the primary software being contained).

Some additional license information which was able to be auto-detected might be found in the repo-info repository's node/ directory.

As for any pre-built image usage, it is the image user's responsibility to ensure that any use of this image complies with any relevant licenses for all software contained within.