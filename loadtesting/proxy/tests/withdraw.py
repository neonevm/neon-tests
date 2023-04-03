
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
            amount = self.web3_client._web3.to_wei(1, "ether")
            instruction_tx = contract.functions.withdraw(bytes(keys.public_key)).build_transaction(
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
