import logging

import allure
from web3.types import TxReceipt

from utils import web3client, stats_collector

LOGGER = logging.getLogger(__name__)


class ERC721ForMetaplex:
    def __init__(
        self,
        web3_client: web3client.NeonChainWeb3Client,
        faucet,
        account=None,
        contract="../common/erc721_for_metaplex.sol",
        contract_name="ERC721ForMetaplex",
        contract_address=None,
    ):
        self.web3_client = web3_client
        self.account = account or web3_client.create_account_with_balance(faucet)
        if contract_address:
            self.contract = web3_client.get_deployed_contract(
                contract_address, contract_file=contract, contract_name=contract_name, solc_version="0.8.28"
            )
        else:
            self.contract = self.deploy(contract, contract_name)

    @allure.step("Deploy contract")
    def deploy(self, contract, contract_name):
        contract, _ = self.web3_client.deploy_and_get_contract(
            contract, "0.8.28", self.account, contract_name=contract_name
        )
        return contract

    @allure.step("Mint")
    @stats_collector.cost_report_from_receipt
    def mint(self, seed, to_address, uri, gas_price=None, gas=None, signer=None) -> int:
        signer = self.account if signer is None else signer
        tx = self.web3_client.make_raw_tx(signer, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.mint(seed, to_address, uri).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        ERC721ForMetaplex.receipt = resp  # save for @stats_collector.cost_report_from_receipt
        logs = self.contract.events.Transfer().process_receipt(resp)
        LOGGER.info(f"Event logs: {logs}")
        return logs[0]["args"]["tokenId"]

    @allure.step("Safe mint")
    def safe_mint(self, seed, to_address, uri, data=None, gas_price=None, gas=None, signer=None):
        signer = self.account if signer is None else signer
        tx = self.web3_client.make_raw_tx(signer.address, gas_price=gas_price, gas=gas)
        if data is None:
            instruction_tx = self.contract.functions.safeMint(seed, to_address, uri).build_transaction(tx)
        else:
            instruction_tx = self.contract.functions.safeMint(seed, to_address, uri, data).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        logs = self.contract.events.Transfer().process_receipt(resp)
        LOGGER.info(f"Event logs: {logs}")
        return logs[0]["args"]["tokenId"]

    @allure.step("Transfer from")
    @stats_collector.cost_report_from_receipt
    def transfer_from(self, address_from, address_to, token_id, signer, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.transferFrom(address_from, address_to, token_id).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    @allure.step("Safe transfer from")
    def safe_transfer_from(
        self, address_from, address_to, token_id, signer, data=None, gas_price=None, gas=None
    ) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer, gas_price=gas_price, gas=gas)
        if data is None:
            instruction_tx = self.contract.functions.safeTransferFrom(
                address_from, address_to, token_id
            ).build_transaction(tx)
        else:
            instruction_tx = self.contract.functions.safeTransferFrom(
                address_from, address_to, token_id, data
            ).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    @allure.step("Approve")
    @stats_collector.cost_report_from_receipt
    def approve(self, address_to, token_id, signer, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.approve(address_to, token_id).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    @allure.step("Set approval for all")
    def set_approval_for_all(self, operator, approved, signer, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.setApprovalForAll(operator, approved).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp

    @allure.step("Transfer solana from")
    def transfer_solana_from(self, from_address, to_address, token_id, signer, gas_price=None, gas=None) -> TxReceipt:
        tx = self.web3_client.make_raw_tx(signer, gas_price=gas_price, gas=gas)
        instruction_tx = self.contract.functions.transferSolanaFrom(
            from_address, to_address, token_id
        ).build_transaction(tx)
        resp = self.web3_client.send_transaction(signer, instruction_tx)
        return resp
