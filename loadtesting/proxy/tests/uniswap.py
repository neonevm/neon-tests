UNISWAP_REPO_URL = "https://github.com/gigimon/Uniswap-V2-NEON.git"
UNISWAP_TMP_DIR = "/tmp/uniswap-neon"
MAX_UINT_256 = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF


@events.test_start.add_listener
def deploy_uniswap(environment: "locust.env.Environment", **kwargs):
    # 1. git clone repo with uniswap
    # 2. deploy 3 erc20 contracts
    # 3. deploy uniswap and create pairs
    # 4. make liquidities

    if environment.parsed_options.exclude_tags and "uniswap" in environment.parsed_options.exclude_tags:
        return

    if environment.parsed_options.tags and "uniswap" not in environment.parsed_options.tags:
        return
    LOG.info("Start deploy Uniswap")
    base_cwd = os.getcwd()
    uniswap_path = pathlib.Path(UNISWAP_TMP_DIR)
    if not uniswap_path.exists():
        shutil.rmtree(UNISWAP_TMP_DIR, ignore_errors=True)
        subprocess.call(f"git clone {UNISWAP_REPO_URL} {uniswap_path}", shell=True)
        os.chdir(uniswap_path)
        subprocess.call("npm install", shell=True)
    os.chdir(uniswap_path)

    neon_client = NeonWeb3Client(environment.credentials["proxy_url"], environment.credentials["network_id"])
    faucet = Faucet(environment.credentials["faucet_url"])

    eth_account = neon_client.create_account()
    faucet.request_neon(eth_account.address, 10000)

    erc20_contracts = {"tokenA": "", "tokenB": "", "tokenC": "", "weth": ""}
    LOG.info("Deploy ERC20 tokens for Uniswap")
    for token in erc20_contracts:
        erc_contract, _ = neon_client.deploy_and_get_contract(
            str(uniswap_path / "contracts/v2-core/test/ERC20.sol"),
            account=eth_account,
            version="0.5.16",
            constructor_args=[web3.Web3.toWei(10000000000, "ether")],
        )
        erc20_contracts[token] = erc_contract
    LOG.info("Deploy Uniswap factory")
    uniswap2_factory, _ = neon_client.deploy_and_get_contract(
        str(uniswap_path / "contracts/v2-core/UniswapV2Factory.sol"),
        account=eth_account,
        version="0.5.16",
        constructor_args=[eth_account.address],
    )
    LOG.info("Deploy Uniswap router")
    uniswap2_router, _ = neon_client.deploy_and_get_contract(
        str(uniswap_path / "contracts/v2-periphery/UniswapV2Router02.sol"),
        account=eth_account,
        version="0.6.6",
        import_remapping={"@uniswap": str(uniswap_path / "node_modules/@uniswap")},
        constructor_args=[uniswap2_factory.address, erc20_contracts["weth"].address],
    )
    LOG.info(f'Create pair1 {erc20_contracts["tokenA"].address} <-> {erc20_contracts["tokenB"].address}')
    pair1_transaction = uniswap2_factory.functions.createPair(
        erc20_contracts["tokenA"].address, erc20_contracts["tokenB"].address
    ).buildTransaction(
        {
            "from": eth_account.address,
            "nonce": neon_client.eth.get_transaction_count(eth_account.address),
            "gasPrice": neon_client.gas_price(),
        }
    )
    neon_client.send_transaction(eth_account, pair1_transaction)
    LOG.info(f'Create pair2 {erc20_contracts["tokenB"].address} <-> {erc20_contracts["tokenC"].address}')
    pair2_transaction = uniswap2_factory.functions.createPair(
        erc20_contracts["tokenB"].address, erc20_contracts["tokenC"].address
    ).buildTransaction(
        {
            "from": eth_account.address,
            "nonce": neon_client.eth.get_transaction_count(eth_account.address),
            "gasPrice": neon_client.gas_price(),
        }
    )
    neon_client.send_transaction(eth_account, pair2_transaction)

    pair1_address = uniswap2_factory.functions.getPair(
        erc20_contracts["tokenA"].address, erc20_contracts["tokenB"].address
    ).call()
    pair2_address = uniswap2_factory.functions.getPair(
        erc20_contracts["tokenB"].address, erc20_contracts["tokenC"].address
    ).call()

    pair_contract_interface = helpers.get_contract_interface(
        str(uniswap_path / "contracts/v2-core/UniswapV2Pair.sol"), version="0.5.16"
    )

    pair1_contract = neon_client.eth.contract(address=pair1_address, abi=pair_contract_interface["abi"])
    pair2_contract = neon_client.eth.contract(address=pair2_address, abi=pair_contract_interface["abi"])

    for token in erc20_contracts:
        c = erc20_contracts[token]
        tr = c.functions.approve(uniswap2_router.address, MAX_UINT_256).buildTransaction(
            {
                "from": eth_account.address,
                "nonce": neon_client.eth.get_transaction_count(eth_account.address),
                "gasPrice": neon_client.gas_price(),
            }
        )
        neon_client.send_transaction(eth_account, tr)

    LOG.info("Add liquidities to pools")
    tr = uniswap2_router.functions.addLiquidity(
        erc20_contracts["tokenA"].address,
        erc20_contracts["tokenB"].address,
        web3.Web3.toWei(1000000, "ether"),
        web3.Web3.toWei(1000000, "ether"),
        0,
        0,
        eth_account.address,
        0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
    ).buildTransaction(
        {
            "from": eth_account.address,
            "nonce": neon_client.eth.get_transaction_count(eth_account.address),
            "gasPrice": neon_client.gas_price(),
        }
    )
    neon_client.send_transaction(eth_account, tr)
    tr = uniswap2_router.functions.addLiquidity(
        erc20_contracts["tokenB"].address,
        erc20_contracts["tokenC"].address,
        web3.Web3.toWei(1000000, "ether"),
        web3.Web3.toWei(1000000, "ether"),
        0,
        0,
        eth_account.address,
        0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF,
    ).buildTransaction(
        {
            "from": eth_account.address,
            "nonce": neon_client.eth.get_transaction_count(eth_account.address),
            "gasPrice": neon_client.gas_price(),
        }
    )
    neon_client.send_transaction(eth_account, tr)
    os.chdir(base_cwd)
    environment.uniswap = {
        "signer": eth_account,
        "router": uniswap2_router,
        "factory": uniswap2_factory,
        "pair1": pair1_contract,
        "pair2": pair2_contract,
    }
    environment.uniswap.update(erc20_contracts)
