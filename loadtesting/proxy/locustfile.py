









class BaseResizingTasksSet(NeonProxyTasksSet):
    """Implements resize accounts base pipeline tasks"""

    _buffer: tp.Optional[tp.List] = None
    contract_name: tp.Optional[str] = None
    version: tp.Optional[str] = None

    @task(1)
    @execute_before("task_block_number", "task_keeps_balance")
    def task_deploy_contract(self) -> None:
        """Deploy contract"""
        self.log.info(f"`{self.contract_name}`: deploy contract.")
        contract, _ = self.deploy_contract(self.contract_name, self.version, self.account)
        if not contract:
            self.log.error(f"`{self.contract_name}` contract deployment failed.")
            return
        self._buffer.append(contract)

    def task_resize(self, item: str) -> None:
        """Account resize"""
        if self._buffer:
            contract = random.choice(self._buffer)
            if hasattr(contract.functions, "get") and item == "dec":
                if contract.functions.get().call() <= 1:
                    self.log.info(
                        f"Can't {item}rease contract `{str(contract.address)[:8]}`, counter is zero. Do increase."
                    )
                    item = "inc"
            func = getattr(contract.functions, item)
            self.log.info(f"`{self.contract_name}`: {item}rease in contract `{str(contract.address)[:8]}`.")
            try:
                tx = func().buildTransaction(
                    {
                        "from": self.account.address,
                        "nonce": self.web3_client.eth.get_transaction_count(self.account.address),
                        "gasPrice": self.web3_client.gas_price(),
                    }
                )
                getattr(self.web3_client, f"{item}_account")(self.account, tx)
            except web3.exceptions.ContractLogicError as e:
                if "execution reverted" not in e.args:
                    raise
            return
        self.log.debug(f"no `{self.contract_name}` contracts found, account {item}rease canceled.")


class ERC20BaseTasksSet(NeonProxyTasksSet):
    """Implements ERC20 base pipeline tasks"""

    contract_name: tp.Optional[str] = None
    version: tp.Optional[str] = None
    _buffer: tp.Optional[tp.Dict] = None
    _erc20wrapper_client: tp.Optional[ERC20Wrapper] = None
    _sol_client: tp.Any = None

    def on_start(self) -> None:
        super(ERC20BaseTasksSet, self).on_start()

    def task_deploy_contract(self) -> None:
        """Deploy ERC20 or ERC20Wrapper contract"""
        self.log.info(f"Deploy `{self.contract_name.lower()}` contract.")
        amount_range = pow(10, 15)
        amount = random.randint(amount_range, amount_range + pow(10, 3))
        contract = getattr(self, f"_deploy_{self.contract_name.lower()}_contract")(amount=amount)
        if not contract:
            self.log.info(f"{self.contract_name} contract deployment failed {contract}")
            return
        self._buffer.setdefault(self.account.address, {}).update(
            {contract.address: {"contract": contract, "amount": amount}}
        )

    def task_send_tokens(self) -> None:
        """Send ERC20/ERC20Wrapped tokens"""
        contracts = self._buffer.get(self.account.address)

        if contracts:
            contract_address = random.choice(list(contracts.keys()))
            contract = contracts[contract_address]["contract"]
            if contracts[contract_address]["amount"] < 1:
                self.log.info(f"low balance on contract: {contracts[contract_address]}, skip transfer")
                del contracts[contract_address]
                return
            recipient = random.choice(self.user.environment.shared.accounts)
            self.log.info(
                f"Send `{self.contract_name.lower()}` tokens from contract {str(contract.address)[-8:]} to {str(recipient.address)[-8:]}."
            )
            tx_receipt = self.web3_client.send_erc20(self.account, recipient, 1, contract.address, abi=contract.abi)
            if tx_receipt:
                tx_receipt = dict(tx_receipt)  # AttributeDict -> dict
                tx_receipt["contractAddress"] = contract.address
                self._buffer[self.account.address][contract.address]["amount"] -= 1
                recipient_contracts = self._buffer.get(recipient.address, {})
                recipient_contract = recipient_contracts.get(contract.address, {})
                if not recipient_contract:
                    recipient_contract.update({"contract": contract, "amount": 0})
                recipient_contract["amount"] += 1
                self._buffer.setdefault(recipient.address, {}).update({contract.address: recipient_contract})
            return tx_receipt
        self.log.info(f"no `{self.contract_name.upper()}` contracts found, send is cancel.")

    def _deploy_erc20_contract(self, amount: int) -> "web3._utils.datatypes.Contract":
        """Deploy ERC20 contract"""
        contract, _ = self.deploy_contract(self.contract_name, self.version, self.account, constructor_args=[amount])
        return contract

    def _deploy_erc20wrapper_contract(self, amount: int) -> "web3._utils.datatypes.Contract":
        """Deploy ERC20Wrapped contract"""
        symbol = "".join(random.sample(string.ascii_uppercase, 3))
        erc20wrapper_client = ERC20Wrapper(
            self.web3_client,
            self.faucet,
            name=f"Test {symbol}",
            symbol=symbol,
            sol_client=self._sol_client,
            account=self.account,
        )
        erc20wrapper_client.mint_tokens(
            self.account,
            self.account.address,
            amount=amount,
        )
        return erc20wrapper_client.contract





@tag("erc20")
class ERC20TasksSet(ERC20BaseTasksSet):
    """Implements ERC20 base pipeline tasks"""

    def on_start(self) -> None:
        super(ERC20TasksSet, self).on_start()
        self.version = ERC20_VERSION
        self.contract_name = "ERC20"
        self._buffer = self.user.environment.shared.erc20_contracts

    @task(2)
    @execute_before("task_block_number")
    def task_deploy_contract(self) -> None:
        """Deploy ERC20 contract"""
        super(ERC20TasksSet, self).task_deploy_contract()

    @task(6)
    @execute_before("task_block_number")
    def task_send_erc20(self) -> tp.Union[None, web3.datastructures.AttributeDict]:
        """Send ERC20 tokens"""
        return super(ERC20TasksSet, self).task_send_tokens()


@tag("erc20one")
class ERC20OneContractTasksSet(ERC20BaseTasksSet):
    """Implements ERC20 base pipeline tasks"""
    def on_start(self) -> None:
        super().on_start()
        self.version = ERC20_VERSION
        self.contract_name = "ERC20"
        self._buffer = self.user.environment.shared.erc20_contracts

    @execute_before("task_block_number")
    def task_send_erc20(self) -> tp.Union[None, web3.datastructures.AttributeDict]:
        """Send ERC20 tokens"""


@tag("spl")
class ERC20SPLTasksSet(ERC20BaseTasksSet):
    """Implements ERC20Wrapped base pipeline tasks"""

    _sol_client: tp.Optional["solana.rpc.api.Client"] = None

    def on_start(self) -> None:
        super(ERC20SPLTasksSet, self).on_start()
        self.version = ERC20_WRAPPER_VERSION
        self.contract_name = "erc20wrapper"
        self._buffer = self.user.environment.shared.erc20_wrapper_contracts
        self._sol_client = Client(self.credentials["solana_url"])

    @task(2)
    @execute_before("task_block_number", "task_keeps_balance")
    def task_deploy_contract(self) -> None:
        """Deploy ERC20Wrapper contract"""
        super(ERC20SPLTasksSet, self).task_deploy_contract()

    @task(6)
    @execute_before("task_block_number", "task_keeps_balance")
    def task_send_erc20_wrapped(self) -> None:
        """Send ERC20 tokens"""
        return super(ERC20SPLTasksSet, self).task_send_tokens()


@tag("counter")
@tag("contract")
class CounterTasksSet(BaseResizingTasksSet):
    """Implements Counter contracts base pipeline tasks"""

    def on_start(self) -> None:
        super(CounterTasksSet, self).on_start()
        self._buffer = self.user.environment.shared.counter_contracts
        self.contract_name = "Counter"
        self.version = COUNTER_VERSION

    @task(4)
    @execute_before("task_block_number", "task_keeps_balance")
    def task_increase_counter(self) -> None:
        """Accounts increase"""
        super(CounterTasksSet, self).task_resize("inc")

    @task(2)
    @execute_before("task_block_number", "task_keeps_balance")
    def task_decrease_counter(self) -> None:
        """Accounts decrease"""
        super(CounterTasksSet, self).task_resize("dec")


@tag("withdraw")
class WithDrawTasksSet(NeonProxyTasksSet):
    """Implements withdraw tokens to Solana tasks"""

    _contract_name: str = "NeonToken"
    _version: str = NEON_TOKEN_VERSION

    @task
    @execute_before("task_block_number", "task_keeps_balance")
    def task_withdraw_tokens(self) -> None:
        """withdraw Ethereum tokens to Solana"""
        keys = Keypair.generate()
        contract_interface = self._compile_contract_interface(self.contract_name, self.version)
        erc20wrapper_address = self.credentials.get("neon_erc20wrapper_address")
        if erc20wrapper_address:
            self.log.info(f"withdraw tokens to Solana from {self.account.address[:8]}")
            contract = self.web3_client.eth.contract(address=erc20wrapper_address, abi=contract_interface["abi"])
            amount = self.web3_client._web3.toWei(1, "ether")
            instruction_tx = contract.functions.withdraw(bytes(keys.public_key)).buildTransaction(
                {
                    "from": self.account.address,
                    "nonce": self.web3_client.eth.get_transaction_count(self.account.address),
                    "gasPrice": self.web3_client.gas_price(),
                    "value": amount,
                }
            )
            result = self.web3_client.withdraw_tokens(self.account, instruction_tx)
            if not (result and result.get("status")):
                self.log.error(f"withdrawing tokens is failed, transaction result: {result}")
            return
        self.log.error(f"No Neon erc20wrapper address in passed credentials, can't generate contract.")


@tag("uniswap")
class UniswapTransaction(NeonProxyTasksSet):
    def on_start(self) -> None:
        super(UniswapTransaction, self).on_start()
        signer = self.user.environment.uniswap["signer"]
        token_a = self.user.environment.uniswap["tokenA"]
        token_b = self.user.environment.uniswap["tokenB"]
        token_c = self.user.environment.uniswap["tokenC"]

        for token in [token_a, token_b, token_c]:
            self.log.info(f"Transfer erc token to account: {self.account.address}")
            trx = token.functions.transfer(self.account.address, web3.Web3.toWei(1000, "ether")).buildTransaction(
                {
                    "from": signer.address,
                    "nonce": self.web3_client.eth.get_transaction_count(signer.address),
                    "gasPrice": self.web3_client.gas_price(),
                }
            )
            self.web3_client.send_transaction(signer, trx)

            self.log.info(f"Approve token by account {self.account.address}")
            trx = token.functions.approve(
                self.user.environment.uniswap["router"].address, MAX_UINT_256
            ).buildTransaction(
                {
                    "from": self.account.address,
                    "nonce": self.web3_client.get_nonce(self.account.address),
                    "gasPrice": self.web3_client.gas_price(),
                }
            )
            self.web3_client.send_transaction(self.account, trx)

    def _send_swap_trx(self, trx):
        self.web3_client.send_transaction(self.account, trx, gas_multiplier=1.1)

    @statistics_collector("Direct swap")
    def _send_direct_swap_trx(self, trx):
        return self._send_swap_trx(trx)

    @statistics_collector("Swap 2 pools")
    def _send_2pools_swap_trx(self, trx):
        return self._send_swap_trx(trx)

    @task
    def task_swap_direct(self):
        router = self.user.environment.uniswap["router"]
        token_a = self.user.environment.uniswap["tokenA"]
        token_b = self.user.environment.uniswap["tokenB"]
        self.log.info("Swap token direct")
        swap_trx = router.functions.swapExactTokensForTokens(
            web3.Web3.toWei(1, "ether"),
            0,
            random.sample([token_a.address, token_b.address], 2),
            self.account.address,
            MAX_UINT_256,
        ).buildTransaction(
            {
                "from": self.account.address,
                "nonce": self.web3_client.get_nonce(self.account.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        self._send_direct_swap_trx(swap_trx)

    @task
    def task_swap_two_pools(self):
        router = self.user.environment.uniswap["router"]
        token_a = self.user.environment.uniswap["tokenA"]
        token_b = self.user.environment.uniswap["tokenB"]
        token_c = self.user.environment.uniswap["tokenC"]
        self.log.info("Swap token via 2 pools")
        swap_trx = router.functions.swapExactTokensForTokens(
            web3.Web3.toWei(1, "ether"),
            0,
            [token_a.address, token_b.address, token_c.address],
            self.account.address,
            MAX_UINT_256,
        ).buildTransaction(
            {
                "from": self.account.address,
                "nonce": self.web3_client.get_nonce(self.account.address),
                "gasPrice": self.web3_client.gas_price(),
            }
        )
        self._send_2pools_swap_trx(swap_trx)


class NeonPipelineUser(User):
    """Class represents a base Neon pipeline by one user"""

    tasks = {
        CounterTasksSet: 3,
        ERC20TasksSet: 1,
        ERC20SPLTasksSet: 2,
        NeonTasksSet: 10,
        # WithDrawTasksSet: 5,  Disable this, because withdraw instruction changed
        UniswapTransaction: 5,
    }
