from eth_account.signers.local import LocalAccount

from utils import web3client


class ERC20:
    def __init__(
            self,
            web3_client: web3client.NeonWeb3Client,
            faucet,
            owner=None,
            name="Test Token",
            symbol="TT"
    ):
        self.web3_client = web3_client
        self.owner = owner
        if self.owner is None:
            self.owner = web3_client.create_account()
            faucet.request_neon(self.owner.address, 300)
        self.initial_balance = 1000000
        self.contract = self.deploy(name, symbol)

    def _make_tx_object(self, from_address):
        tx = {
            "from": from_address,
            "nonce": self.web3_client.eth.get_transaction_count(from_address),
            "gasPrice": self.web3_client.gas_price(),
        }
        return tx

    def deploy(self, name, symbol):
        contract, contract_deploy_tx = self.web3_client.deploy_and_get_contract(
            "EIPs/ERC20/ERC20",
            "0.8.8",
            self.owner,
            constructor_args=[name, symbol, self.initial_balance],
        )
        return contract

    def get_balance(self, address):
        if isinstance(address, LocalAccount):
            address = address.address
        return self.contract.functions.balanceOf(address).call()

    def transfer(self, signer, address_to, amount):
        tx = self._make_tx_object(signer.address)
        if isinstance(address_to, LocalAccount):
            address_to = address_to.address
        instruction_tx = self.contract.functions.transfer(address_to, amount).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp
