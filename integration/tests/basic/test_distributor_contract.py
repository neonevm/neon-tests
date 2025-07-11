from eth_account.signers.local import LocalAccount
from web3.contract import Contract

from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client


class TestDistributorContract:
    def test_distribute_tx_affects_multiple_accounts(
        self,
        web3_client: NeonChainWeb3Client,
        accounts: EthAccounts,
    ):
        signer = accounts[0]
        contract, _ = web3_client.deploy_and_get_contract(
            contract="common/NeonDistributor.sol",
            version="0.8.12",
            account=signer,
        )
        wallets = self.generate_wallets(accounts)
        self._set_and_check_distributor_addresses(
            wallets=wallets,
            signer=signer,
            web3_client=web3_client,
            contract=contract,
        )

        amount_per_account = 1000
        tx = web3_client.make_raw_tx(from_=signer, amount=amount_per_account * len(wallets))
        tx = contract.functions.distribute_value().build_transaction(tx)
        receipt = web3_client.send_transaction(account=signer, transaction=tx)
        assert receipt["status"] == 1

        for account in wallets.values():
            balance = web3_client.get_balance(account)
            assert balance == amount_per_account

    @staticmethod
    def _set_and_check_distributor_addresses(
        wallets: dict[str, LocalAccount],
        signer: LocalAccount,
        web3_client: NeonChainWeb3Client,
        contract: Contract,
    ):
        nonce = web3_client.get_nonce(signer)

        for name, account in wallets.items():
            address = bytes.fromhex(account.address[2:])
            raw_tx = contract.functions.set_address(name, address).build_transaction({"nonce": nonce})
            receipt = web3_client.send_transaction(account=signer, transaction=raw_tx)
            assert receipt["status"] == 1
            nonce += 1

    @staticmethod
    def generate_wallets(accounts: EthAccounts) -> dict[str, LocalAccount]:
        names = [
            "alice",
            "bob",
            "carol",
            "dave",
            "erine",
            "eve",
            "frank",
            "mallory",
            "pat",
            "peggy",
            "trudy",
            "vanna",
        ]
        wallets = {name: accounts.create_account(balance=0) for i, name in enumerate(names)}
        return wallets
