import math

import pytest


def mint_and_approve(acc, client, coins, amounts, approve_to):
    for i in range(len(coins)):
        tx = client.make_raw_tx(acc.address)
        instruction_tx = coins[i].functions._mint_for_testing(acc.address, amounts[i]).build_transaction(tx)
        resp = client.send_transaction(acc, instruction_tx)
        assert resp["status"] == 1, "Mint failed"

        tx = client.make_raw_tx(acc.address)
        instruction_tx = coins[i].functions.approve(approve_to.address, amounts[i]).build_transaction(tx)
        resp = client.send_transaction(acc, instruction_tx)
        assert resp["status"] == 1, "Approve failed"


def add_liquidity_base_pool(acc, client, base_coins, pool, amount=10000000):
    mint_and_approve(acc, client, base_coins, [amount, amount, amount], pool)
    tx = client.make_raw_tx(acc.address)
    instruction_tx = pool.functions.add_liquidity([amount, amount, amount], 0).build_transaction(tx)
    resp = client.send_transaction(acc, instruction_tx)
    assert resp["status"] == 1, "Add liquidity failed"


class TestVyperCompatibility:

    @pytest.fixture
    def base_pool_erc20_for_spl(self, base_pool_and_token_erc20_for_spl):
        pool, _ = base_pool_and_token_erc20_for_spl
        return pool

    @pytest.fixture
    def base_pool_and_token_erc20_for_spl(self, web3_client, accounts, base_coins_erc20_for_spl):
        token = web3_client.read_vyper_file_and_deploy(
            accounts[0],
            "CurveTokenV1",
            [
                "Curve.fi",  # _name: String[64]
                "crvRenWSBTC",  # _symbol: String[32]
                18,  # _decimals: uint256
                0,  # _supply: uint256
            ],
        )
        pool = web3_client.compile_by_vyper_and_deploy(
            accounts[0],
            "StableSwapSBTC",
            [
                [
                    base_coins_erc20_for_spl[0].address,
                    base_coins_erc20_for_spl[1].address,
                    base_coins_erc20_for_spl[2].address,
                ],  # _coins: address[N_COINS],
                token.address,  # _pool_token: address,
                200,  # _A: uint256,
                4000000,  # _fee: uint256,
            ],
        )
        tx = web3_client.make_raw_tx(accounts[0].address)
        instruction_tx = token.functions.set_minter(pool.address).build_transaction(tx)
        resp = web3_client.send_transaction(accounts[0], instruction_tx)
        assert resp["status"] == 1, "Trx succeed"

        add_liquidity_base_pool(accounts[1], web3_client, base_coins_erc20_for_spl, pool)
        return pool, token

    @pytest.fixture
    def base_coins_erc20_for_spl(self, web3_client, accounts):
        coins_args = [
            ("Coin renBTC", "renBTC", 8, accounts[1].address),
            ("Coin wBTC", "wBTC", 8, accounts[1].address),
            ("Coin sBTC", "sBTC", 18, accounts[1].address),
        ]
        coins = []
        for coin_arg in coins_args:
            # coin, _ = web3_client.deploy_contract_by_file(
            #     contract_name="NeonErc20ForSpl", account=accounts[0], constructor_args=[*coin_arg]
            # )
            coin, _ = web3_client.deploy_and_get_contract(
                "curve/contracts/testing/NeonErc20ForSpl",
                version="0.7.0",
                account=accounts[0],
                constructor_args=[*coin_arg],
            )
            coin.functions.set_exchange_rate(1).call()
            coins.append(coin)
        return coins

    def test_token(self, base_coins_erc20_for_spl, base_pool_erc20_for_spl, accounts, web3_client):
        amounts = [10000000, 10000000, 10000000]
        mint_and_approve(accounts[1], web3_client, base_coins_erc20_for_spl, amounts, base_pool_erc20_for_spl)

        # add liquidity
        tx = web3_client.make_raw_tx(accounts[1].address)
        instruction_tx = base_pool_erc20_for_spl.functions.add_liquidity(
            [1000000, 1000000, 1000000], 0
        ).build_transaction(tx)
        resp = web3_client.send_transaction(accounts[1], instruction_tx)
        assert resp["status"] == 1, "Add liquidity failed"

        balances_bob0 = [coin.functions.balanceOf(accounts[1].address).call() for coin in base_coins_erc20_for_spl]
        print(f"{balances_bob0=}")
        exchange_amount = 100

        expected = base_pool_erc20_for_spl.functions.get_dy(0, 1, exchange_amount).call()
        print(expected)

        # exchange token
        tx = web3_client.make_raw_tx(accounts[1].address)
        instruction_tx = base_pool_erc20_for_spl.functions.exchange(0, 1, exchange_amount, 0).build_transaction(tx)
        resp = web3_client.send_transaction(accounts[1], instruction_tx)
        assert resp["status"] == 1, "Add liquidity failed"

        print(resp)

        balances_bob1 = [coin.functions.balanceOf(accounts[1].address).call() for coin in base_coins_erc20_for_spl]

        print(f"{balances_bob1=}")

        assert math.isclose(balances_bob1[0], balances_bob0[0] - exchange_amount, rel_tol=1)
        assert math.isclose(balances_bob1[1], balances_bob0[1] + expected, rel_tol=1)

    # def test_mint(self, erc20_vyper, accounts, web3_client):
    #     check_erc20_mint_function(web3_client, erc20_vyper, accounts[0])
    #
    # def test_transfer(self, erc20_vyper, accounts, web3_client):
    #     check_erc20_transfer_function(web3_client, erc20_vyper, accounts[0], accounts[1])
    #
    # def test_deploy_contract_by_contract(self, simple, forwarder, accounts, web3_client):
    #     tx = web3_client.make_raw_tx(accounts[0].address, estimate_gas=False)
    #     instr = forwarder.functions.deploy(simple.address, accounts[0].address).build_transaction(tx)
    #     resp = web3_client.send_transaction(accounts[0], instr)
    #     assert resp["status"] == 1
