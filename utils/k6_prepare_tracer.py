import web3
import random
import base58

from utils.consts import InputTestConstants
from utils.storage_contract import StorageContract
from utils.erc20 import ERC20
from utils.erc20wrapper import ERC20Wrapper
from utils.accounts import EthAccounts
from utils.solana_client import SolanaClient
from solders.keypair import Keypair


class TracerDataProducer:
    def __init__(self, web3_client, faucet, solana_url, evm_loader, account_seed_version, bank_account, eth_bank_account):
        self.faucet = faucet
        self.web3_client = web3_client
        self.evm_loader = evm_loader
        self.bank_account = self.account_from_private_key(bank_account)
        if eth_bank_account:
            self.eth_bank_account = self.web3_client.eth.account.from_key(eth_bank_account)
        else:
            self.eth_bank_account = None
        self.account_manager = EthAccounts(web3_client, faucet, self.eth_bank_account)
        self.sol_client = SolanaClient(
            solana_url,
            account_seed_version,
        )


    def prepare_tracer(self, transfers_number, contracts_calls_number):
        try:
            self.neon_transfer_data(transfers_number=transfers_number)
            self.erc20_transfer_data(transfers_number=transfers_number)
            self.erc20_wrapped_transfer_data(transfers_number=transfers_number)
            self.storage_contract_data(calls_number=contracts_calls_number)
            self.event_caller_contract_data(calls_number=contracts_calls_number)
            self.iterative_tx_contract_data(calls_number=contracts_calls_number)
        except Exception as e:
            print(f"Error in prepare_tracer: {e}")
        finally:
            self.dump_data()
        

    def erc20_transfer_data(self, transfers_number):
        account_owner = self.get_account()
        transfer_amount = random.random() 
        
        print("ERC20 contract deployment...")
        erc20_contract = ERC20(
            self.web3_client,
            self.faucet,
            owner=account_owner,
            amount=web3.Web3.to_wei(10000000000, "ether"),
        )
        
        print("ERC20 transfers...")
        for i in range(transfers_number):
            try:
                account_receiver = self.get_account(balance=0)
                receipt = erc20_contract.transfer(erc20_contract.owner, account_receiver, transfer_amount)
                print(f"ERC20 transfer {i}, receipt status: ", receipt["status"])
            except Exception as e:
                print(f"Error in erc20_transfer_data: {e}") 

    def neon_transfer_data(self, transfers_number):
        transfer_amount = random.random()
        print("Neon transfers...")
        for i in range(transfers_number):       
            try:
                sender_account = self.get_account()
                recipient_account = self.get_account(balance=0)
                receipt = self.web3_client.send_neon(sender_account, recipient_account, transfer_amount)
                print(f"Neon transfer {i}, receipt status: ", receipt["status"])
            except Exception as e:
                print(f"Error in neon_transfer_data: {e}") 

    def erc20_wrapped_transfer_data(self, transfers_number):
        account_owner = self.get_account(balance=1000)
        transfer_amount = random.random()
        
        erc20_wrapper = ERC20Wrapper(
            self.web3_client,
            self.faucet,
            "Test Token",
            "TTW",
            self.sol_client,
            solana_account=Keypair(),
            account=account_owner,
            mintable=True,
        )
        print("ERC20 wrapped contract deployment...")
        erc20_wrapper.deploy_wrapper(True)
        erc20_wrapper.mint_tokens(account_owner, account_owner.address, 18446744073709551615)
        
        print("ERC20 wrapped transfers...")
        for i in range(transfers_number):
            try:
                account_receiver = self.get_account(balance=0)
                receipt = erc20_wrapper.transfer(erc20_wrapper.account, account_receiver, transfer_amount)
                print(f"ERC20 wrapped transfer {i}, receipt status: ", receipt["status"])
            except Exception as e:
                print(f"Error in erc20_transfer_data: {e}") 

    def storage_contract_data(self, calls_number):
        account_owner = self.get_account()
        print("Storage contract deployment...")
        contract, _ = self.web3_client.deploy_and_get_contract(
        "common/StorageSoliditySource",
            "0.8.8",
            account_owner,
            contract_name="Storage",
            constructor_args=[],    
        )
        storage_contract = StorageContract(self.web3_client, contract)

        print("Storage contract calls...")
        for i in range(calls_number):
            try:
                sender_account = self.get_account()
                store_value = random.randint(0, 100)
                tx_obj, _, receipt = storage_contract.call_storage(sender_account, store_value, "blockNumber")
                print(f"Storage contract call {i}, receipt status: ", receipt["status"])
            except Exception as e:
                print(f"Error in call storage contract functions: {e}") 

    def event_caller_contract_data(self, calls_number):
        account_owner = self.get_account()
        
        print("Events caller/callee contracts deployment...")
        contract, _ = self.web3_client.deploy_and_get_contract("common/EventsCheckerCaller", 
                                                               "0.8.15", 
                                                               account=account_owner)
        _, contract_deploy_tx = self.web3_client.deploy_and_get_contract("common/EventsCheckerCallee", 
                                                                         "0.8.15", 
                                                                         account=account_owner)
        for i in range(calls_number):
            try:
                sender_account = self.get_account()
                tx = self.web3_client.make_raw_tx(from_=sender_account)
                instruction_tx = contract.functions.emitAllEventsAndCallContractCalleeWithEvent(
                    contract_deploy_tx["contractAddress"]).build_transaction(tx)
                receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
                print(f"Event caller contract call {i}, receipt status: ", receipt["status"])
            except Exception as e:
                print(f"Error in call event caller contract functions: {e}")    

    def iterative_tx_contract_data(self, calls_number):
        account_owner = self.get_account()
        
        print("Iterative tx contract deployment...")
        contract, _ = self.web3_client.deploy_and_get_contract("common/Counter", "0.8.10", account=account_owner)
        
        print("Iterative tx contract calls...")
        for i in range(calls_number):
            try:
                sender_account = self.get_account()
                tx = self.web3_client.make_raw_tx(sender_account)
                instruction_tx = contract.functions.moreInstructionWithLogs(0, 1000).build_transaction(tx)
                receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
                print(f"Iterative tx contract call {i}, receipt status: ", receipt["status"])
            except Exception as e:
                print(f"Error in call iterative tx contract functions: {e}") 

    def dump_data(self):
        pass

    def account_from_private_key(self, private_key):
        key = base58.b58decode(private_key)
        account = Keypair.from_bytes(key)
        return account
    
    def get_account(self, balance=InputTestConstants.NEW_USER_REQUEST_AMOUNT.value):
        return self.account_manager.create_account(balance=balance)
