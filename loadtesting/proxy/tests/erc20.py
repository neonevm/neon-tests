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
