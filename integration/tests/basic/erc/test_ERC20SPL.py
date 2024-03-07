import random

import allure
import pytest
import web3
from solana.rpc.types import TokenAccountOpts, TxOpts
from solana.transaction import Transaction
from spl.token import instructions
from spl.token.constants import TOKEN_PROGRAM_ID

from utils import metaplex
from utils.consts import ZERO_ADDRESS
from utils.helpers import gen_hash_of_block, wait_condition, create_invalid_address
from utils.web3client import NeonChainWeb3Client
from utils.solana_client import SolanaClient
from utils.accounts import EthAccounts

UINT64_LIMIT = 18446744073709551615
MAX_TOKENS_AMOUNT = 1000000000000000

NO_ENOUGH_GAS_PARAMS = [
    ({"gas_price": 1000}, "transaction underpriced"),
    ({"gas": 10}, "gas limit reached"),
]


@allure.feature("ERC Verifications")
@allure.story("ERC20SPL: Tests for ERC20ForSPL contract")
@pytest.mark.usefixtures("accounts", "web3_client", "sol_client")
class TestERC20SPL:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    sol_client: SolanaClient

    @pytest.fixture(scope="class")
    def erc20_contract(self, erc20_spl):
        return erc20_spl

    @pytest.fixture()
    def restore_balance(self, erc20_contract):
        pass

    def test_metaplex_data(self, erc20_contract):
        metaplex.wait_account_info(self.sol_client, erc20_contract.token_mint.pubkey)
        metadata = metaplex.get_metadata(self.sol_client, erc20_contract.token_mint.pubkey)
        assert metadata["data"]["name"] == erc20_contract.name
        assert metadata["data"]["symbol"] == erc20_contract.symbol
        assert metadata["is_mutable"] is True

    def test_balanceOf(self, erc20_contract):
        recipient_account = self.accounts[1]
        transfer_amount = random.randint(0, 100)
        initial_balance = erc20_contract.get_balance(recipient_account)
        erc20_contract.transfer(erc20_contract.account, recipient_account, transfer_amount)
        assert erc20_contract.get_balance(recipient_account) == initial_balance + transfer_amount

    def test_totalSupply(self, erc20_contract):
        total_before = erc20_contract.contract.functions.totalSupply().call()
        amount = random.randint(0, 10000)
        erc20_contract.claim(erc20_contract.account, bytes(erc20_contract.solana_associated_token_acc), amount)
        total_after = erc20_contract.contract.functions.totalSupply().call()
        assert total_after == total_before, "Total supply is not correct"

    def test_decimals(self, erc20_contract):
        decimals = erc20_contract.contract.functions.decimals().call()
        assert decimals == erc20_contract.decimals

    def test_symbol(self, erc20_contract):
        symbol = erc20_contract.contract.functions.symbol().call()
        assert symbol == erc20_contract.symbol

    def test_name(self, erc20_contract):
        name = erc20_contract.contract.functions.name().call()
        assert name == erc20_contract.name

    def test_burn(self, erc20_contract, restore_balance):
        balance_before = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()
        total_before = erc20_contract.contract.functions.totalSupply().call()
        amount = random.randint(0, 1000)
        erc20_contract.burn(erc20_contract.account, amount)
        balance_after = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()
        total_after = erc20_contract.contract.functions.totalSupply().call()

        assert balance_after == balance_before - amount
        assert total_after == total_before - amount

    def test_burn_more_than_exist(
        self,
        erc20_contract,
    ):
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match="0x96ab19c8",  # AmountExceedsBalance error
        ):
            erc20_contract.burn(self.accounts[2], 1000)

    def test_burn_more_than_total_supply(self, erc20_contract):
        total = erc20_contract.contract.functions.totalSupply().call()
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match="0x96ab19c8",  # AmountExceedsBalance error
        ):
            erc20_contract.burn(erc20_contract.account, total + 1)

    @pytest.mark.parametrize("param, msg", NO_ENOUGH_GAS_PARAMS)
    def test_burn_no_enough_gas(self, erc20_contract, param, msg):
        with pytest.raises(ValueError, match=msg):
            erc20_contract.burn(erc20_contract.account, 1, **param)

    def test_burnFrom(self, erc20_contract, restore_balance):
        new_account = self.accounts[0]
        balance_before = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()
        total_before = erc20_contract.contract.functions.totalSupply().call()
        amount = random.randint(0, 1000)
        erc20_contract.approve(erc20_contract.account, new_account.address, amount)
        erc20_contract.burn_from(signer=new_account, from_address=erc20_contract.account.address, amount=amount)

        balance_after = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()
        total_after = erc20_contract.contract.functions.totalSupply().call()
        assert balance_after == balance_before - amount
        assert total_after == total_before - amount

    def test_burnFrom_without_allowance(self, erc20_contract):
        new_account = self.accounts.create_account()
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match="0x65ba6fc3",  # InvalidAllowance error
        ):
            erc20_contract.burn_from(new_account, erc20_contract.account.address, 10)

    def test_burnFrom_more_than_allowanced(self, erc20_contract):
        new_account = self.accounts.create_account()
        amount = 2
        erc20_contract.approve(erc20_contract.account, new_account.address, amount)
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match="0x65ba6fc3",  # InvalidAllowance error
        ):
            erc20_contract.burn_from(new_account, erc20_contract.account.address, amount + 1)

    @pytest.mark.parametrize("param, msg", NO_ENOUGH_GAS_PARAMS)
    def test_burnFrom_no_enough_gas(self, erc20_contract, param, msg):
        new_account = self.accounts[0]
        erc20_contract.approve(erc20_contract.account, new_account.address, 1)
        with pytest.raises(ValueError, match=msg):
            erc20_contract.burn_from(new_account, erc20_contract.account.address, 1, **param)

    def test_approve_more_than_total_supply(self, erc20_contract):
        new_account = self.accounts[0]
        amount = erc20_contract.contract.functions.totalSupply().call() + 1
        erc20_contract.approve(erc20_contract.account, new_account.address, amount)
        allowance = erc20_contract.contract.functions.allowance(
            erc20_contract.account.address, new_account.address
        ).call()
        assert allowance == amount

    @pytest.mark.parametrize(
        "block_len, expected_exception, msg",
        [
            (
                ZERO_ADDRESS,
                web3.exceptions.ContractLogicError,
                "0x7138356f",  # EmptyAddress error
            ),
        ],
    )
    def test_approve_incorrect_address(self, erc20_contract, block_len, expected_exception, msg):
        address = create_invalid_address(block_len) if isinstance(block_len, int) else block_len
        with pytest.raises(expected_exception, match=msg):
            erc20_contract.approve(erc20_contract.account, address, 1)

    @pytest.mark.parametrize("param, msg", NO_ENOUGH_GAS_PARAMS)
    def test_approve_no_enough_gas(self, erc20_contract, param, msg):
        with pytest.raises(ValueError, match=msg):
            erc20_contract.approve(erc20_contract.account, erc20_contract.account.address, 1, **param)

    def test_allowance_incorrect_address(self, erc20_contract):
        with pytest.raises(web3.exceptions.InvalidAddress):
            erc20_contract.contract.functions.allowance(erc20_contract.account.address, create_invalid_address()).call()

    def test_allowance_for_new_account(self, erc20_contract):
        new_account = self.accounts.create_account()
        allowance = erc20_contract.contract.functions.allowance(
            new_account.address, erc20_contract.account.address
        ).call()
        assert allowance == 0

    def test_transfer(self, erc20_contract, restore_balance):
        new_account = self.accounts.create_account()
        balance_acc1_before = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()
        balance_acc2_before = erc20_contract.contract.functions.balanceOf(new_account.address).call()
        total_before = erc20_contract.contract.functions.totalSupply().call()
        amount = random.randint(1, 1000)
        erc20_contract.transfer(erc20_contract.account, new_account.address, amount)
        balance_acc1_after = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()
        balance_acc2_after = erc20_contract.contract.functions.balanceOf(new_account.address).call()
        total_after = erc20_contract.contract.functions.totalSupply().call()
        assert balance_acc1_after == balance_acc1_before - amount
        assert balance_acc2_after == balance_acc2_before + amount
        assert total_before == total_after

    @pytest.mark.parametrize(
        "block_len, expected_exception, msg",
        [
            (
                ZERO_ADDRESS,
                web3.exceptions.ContractLogicError,
                "0x7138356f",  # EmptyAddress error
            ),
        ],
    )
    def test_transfer_incorrect_address(self, erc20_contract, block_len, expected_exception, msg):
        address = gen_hash_of_block(block_len) if isinstance(block_len, int) else block_len
        with pytest.raises(expected_exception, match=msg):
            erc20_contract.transfer(erc20_contract.account, address, 1)

    def test_transfer_more_than_balance(self, erc20_contract):
        balance = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match="0x96ab19c8",  # AmountExceedsBalance error
        ):
            erc20_contract.transfer(erc20_contract.account, erc20_contract.account.address, balance + 1)

    @pytest.mark.parametrize("param, msg", NO_ENOUGH_GAS_PARAMS)
    def test_transfer_no_enough_gas(self, erc20_contract, param, msg):
        with pytest.raises(ValueError, match=msg):
            erc20_contract.transfer(erc20_contract.account, erc20_contract.account.address, 1, **param)

    def test_transferFrom(self, erc20_contract, restore_balance):
        new_account = self.accounts.create_account()
        balance_acc1_before = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()
        balance_acc2_before = erc20_contract.contract.functions.balanceOf(new_account.address).call()
        total_before = erc20_contract.contract.functions.totalSupply().call()
        amount = random.randint(1, 10000)
        erc20_contract.approve(erc20_contract.account, new_account.address, amount)
        erc20_contract.transfer_from(new_account, erc20_contract.account.address, new_account.address, amount)
        balance_acc1_after = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()
        balance_acc2_after = erc20_contract.contract.functions.balanceOf(new_account.address).call()
        total_after = erc20_contract.contract.functions.totalSupply().call()
        assert balance_acc1_after == balance_acc1_before - amount
        assert balance_acc2_after == balance_acc2_before + amount
        assert total_before == total_after

    def test_transferFrom_without_allowance(self, erc20_contract):
        new_account = self.accounts.create_account()
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match="0x65ba6fc3",  # InvalidAllowance error
        ):
            erc20_contract.transfer_from(
                signer=new_account,
                address_from=erc20_contract.account.address,
                address_to=new_account.address,
                amount=10,
            )

    def test_transferFrom_more_than_allowanced(self, erc20_contract):
        new_account = self.accounts.create_account()
        amount = 2
        erc20_contract.approve(erc20_contract.account, new_account.address, amount)
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match="0x65ba6fc3",  # InvalidAllowance error
        ):
            erc20_contract.transfer_from(
                signer=new_account,
                address_from=erc20_contract.account.address,
                address_to=new_account.address,
                amount=amount + 1,
            )

    def test_transferFrom_incorrect_address(self, erc20_contract):
        with pytest.raises(web3.exceptions.InvalidAddress):
            erc20_contract.transfer_from(
                signer=erc20_contract.account,
                address_from=erc20_contract.account.address,
                address_to=create_invalid_address(),
                amount=1,
            )

    def test_transferFrom_more_than_balance(self, erc20_contract):
        new_account = self.accounts.create_account()
        amount = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call() + 1
        erc20_contract.approve(erc20_contract.account, new_account.address, amount)
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match="0x96ab19c8",  # AmountExceedsBalance error
        ):
            erc20_contract.transfer_from(
                signer=new_account,
                address_from=erc20_contract.account.address,
                address_to=new_account.address,
                amount=amount,
            )

    @pytest.mark.parametrize("param, msg", NO_ENOUGH_GAS_PARAMS)
    def test_transferFrom_no_enough_gas(self, erc20_contract, param, msg):
        new_account = self.accounts.create_account()
        erc20_contract.approve(erc20_contract.account, new_account.address, 1)
        with pytest.raises(ValueError, match=msg):
            erc20_contract.transfer_from(new_account, erc20_contract.account.address, new_account.address, 1, **param)

    def test_transferSolana(
        self,
        erc20_contract,
        sol_client,
        solana_associated_token_erc20,
    ):
        acc, token_mint, solana_address = solana_associated_token_erc20
        amount = random.randint(10000, 1000000)
        sol_balance_before = sol_client.get_balance(acc.public_key).value
        contract_balance_before = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()

        opts = TokenAccountOpts(token_mint)
        token_data = sol_client.get_token_accounts_by_owner_json_parsed(acc.public_key, opts).value[0]
        token_balance_before = token_data.account.data.parsed["info"]["tokenAmount"]["amount"]
        erc20_contract.transfer_solana(erc20_contract.account, bytes(solana_address), amount)
        wait_condition(
            lambda: int(
                sol_client.get_token_accounts_by_owner_json_parsed(acc.public_key, opts)
                .value[0]
                .account.data.parsed["info"]["tokenAmount"]["amount"]
            )
            > int(token_balance_before),
            timeout_sec=30,
        )

        sol_balance_after = sol_client.get_balance(acc.public_key).value
        token_data = sol_client.get_token_accounts_by_owner_json_parsed(acc.public_key, opts).value[0]
        token_balance_after = token_data.account.data.parsed["info"]["tokenAmount"]["amount"]
        contract_balance_after = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()

        assert (
            int(token_balance_after) - int(token_balance_before) == amount
        ), "Token balance for sol account is not correct"
        assert contract_balance_before - contract_balance_after == amount, "Contract balance is not correct"
        assert sol_balance_after == sol_balance_before, "Sol balance is changed"

    def test_approveSolana(
        self,
        erc20_contract,
        sol_client,
        solana_associated_token_erc20,
    ):
        acc, token_mint, solana_address = solana_associated_token_erc20
        amount = random.randint(10000, 1000000)
        opts = TokenAccountOpts(token_mint)
        erc20_contract.approve_solana(erc20_contract.account, bytes(acc.public_key), amount)
        wait_condition(
            lambda: len(sol_client.get_token_accounts_by_delegate_json_parsed(acc.public_key, opts).value) > 0,
            timeout_sec=30,
        )
        token_account = sol_client.get_token_accounts_by_delegate_json_parsed(acc.public_key, opts).value[0].account
        assert int(token_account.data.parsed["info"]["delegatedAmount"]["amount"]) == amount
        assert int(token_account.data.parsed["info"]["delegatedAmount"]["decimals"]) == erc20_contract.decimals

    def test_claim(
        self,
        erc20_contract,
        sol_client,
        solana_associated_token_erc20,
        pytestconfig,
    ):
        acc, token_mint, solana_address = solana_associated_token_erc20
        balance_before = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()
        sent_amount = random.randint(10, 1000)
        erc20_contract.transfer_solana(erc20_contract.account, bytes(solana_address), sent_amount)
        trx = Transaction()
        trx.add(
            instructions.approve(
                instructions.ApproveParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=solana_address,
                    delegate=sol_client.get_erc_auth_address(
                        erc20_contract.account.address,
                        erc20_contract.contract.address,
                        pytestconfig.environment.evm_loader,
                    ),
                    owner=acc.public_key,
                    amount=sent_amount,
                    signers=[],
                )
            )
        )
        sol_client.send_transaction(trx, acc, opts=TxOpts(skip_preflight=False, skip_confirmation=False))

        claim_amount = random.randint(10, sent_amount)
        erc20_contract.claim(erc20_contract.account, bytes(solana_address), claim_amount)
        balance_after = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()

        assert balance_after == balance_before - sent_amount + claim_amount, "Balance is not correct"

    def test_claimTo(self, erc20_contract, sol_client, solana_associated_token_erc20, pytestconfig):
        new_account = self.accounts.create_account()
        acc, token_mint, solana_address = solana_associated_token_erc20
        user1_balance_before = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()
        user2_balance_before = erc20_contract.contract.functions.balanceOf(new_account.address).call()
        sent_amount = random.randint(10, 1000)
        erc20_contract.transfer_solana(erc20_contract.account, bytes(solana_address), sent_amount)
        trx = Transaction()
        trx.add(
            instructions.approve(
                instructions.ApproveParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=solana_address,
                    delegate=sol_client.get_erc_auth_address(
                        erc20_contract.account.address,
                        erc20_contract.contract.address,
                        pytestconfig.environment.evm_loader,
                    ),
                    owner=acc.public_key,
                    amount=sent_amount,
                    signers=[],
                )
            )
        )
        sol_client.send_transaction(trx, acc, opts=TxOpts(skip_preflight=False, skip_confirmation=False))

        claim_amount = random.randint(10, sent_amount)
        erc20_contract.claim_to(erc20_contract.account, bytes(solana_address), new_account.address, claim_amount)
        user1_balance_after = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()
        user2_balance_after = erc20_contract.contract.functions.balanceOf(new_account.address).call()

        assert user1_balance_after == user1_balance_before - sent_amount, "User1 balance is not correct"
        assert user2_balance_after == user2_balance_before + claim_amount, "User2 balance is not correct"


@allure.feature("ERC Verifications")
@allure.story("ERC20SPL: Tests for ERC20ForSPLMintable contract")
@pytest.mark.usefixtures("accounts", "web3_client", "sol_client")
class TestERC20SPLMintable(TestERC20SPL):
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    sol_client: SolanaClient

    @pytest.fixture(scope="class")
    def erc20_contract(self, erc20_spl_mintable):
        return erc20_spl_mintable

    @pytest.fixture
    def restore_balance(self, erc20_spl_mintable):
        yield
        default_value = MAX_TOKENS_AMOUNT
        current_balance = erc20_spl_mintable.contract.functions.balanceOf(erc20_spl_mintable.account.address).call()
        if current_balance > default_value:
            erc20_spl_mintable.burn(
                erc20_spl_mintable.account,
                current_balance - default_value,
            )
        else:
            erc20_spl_mintable.mint_tokens(
                erc20_spl_mintable.account,
                erc20_spl_mintable.account.address,
                default_value - current_balance,
            )

    def test_owner(self, erc20_contract):
        owner = erc20_contract.contract.functions.owner().call()
        assert owner == erc20_contract.account.address

    @pytest.fixture()
    def return_ownership(self, erc20_contract, accounts):
        yield
        erc20_contract.transfer_ownership(accounts[2], erc20_contract.account.address)

    def test_transferOwnership(self, erc20_contract, accounts, return_ownership):
        erc20_contract.transfer_ownership(erc20_contract.account, accounts[2].address)
        owner = erc20_contract.contract.functions.owner().call()
        assert owner == accounts[2].address

    def test_metaplex_data(self, erc20_contract):
        mint_key = erc20_contract.contract.functions.findMintAccount().call()
        metaplex.wait_account_info(self.sol_client, mint_key)
        metadata = metaplex.get_metadata(self.sol_client, mint_key)
        assert metadata["data"]["name"] == erc20_contract.name
        assert metadata["data"]["symbol"] == erc20_contract.symbol
        assert metadata["data"]["uri"] == "http://uri.com"
        assert metadata["is_mutable"] is True

    def test_mint_to_self(self, erc20_contract, restore_balance):
        balance_before = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()
        amount = random.randint(1, MAX_TOKENS_AMOUNT)
        erc20_contract.mint_tokens(erc20_contract.account, erc20_contract.account.address, amount)
        balance_after = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()
        assert balance_after == balance_before + amount

    def test_mint_to_another_account(self, erc20_contract):
        new_account = self.accounts.create_account(0)
        amount = random.randint(1, MAX_TOKENS_AMOUNT)
        erc20_contract.mint_tokens(erc20_contract.account, new_account.address, amount)
        balance_after = erc20_contract.contract.functions.balanceOf(new_account.address).call()
        assert balance_after == amount

    def test_mint_by_no_minter_role(self, erc20_contract):
        recipient_account = self.accounts[1]
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match="^0x118cdaa7",  # OwnableUnauthorizedAccount error
        ):
            erc20_contract.mint_tokens(recipient_account, recipient_account.address, 0)

    @pytest.mark.parametrize(
        "address_to, expected_exception, msg",
        [
            (
                ZERO_ADDRESS,
                web3.exceptions.ContractLogicError,
                "0x7138356f",  # EmptyAddress error
            ),
        ],
    )
    def test_mint_with_incorrect_address(self, erc20_contract, address_to, expected_exception, msg):
        address_to = create_invalid_address(address_to) if isinstance(address_to, int) else address_to
        with pytest.raises(expected_exception, match=msg):
            erc20_contract.mint_tokens(erc20_contract.account, address_to, 10)

    def test_mint_with_too_big_amount(self, erc20_contract):
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match="0x679346bc",  # AmountExceedsUint64 error
        ):
            erc20_contract.mint_tokens(
                erc20_contract.account,
                erc20_contract.account.address,
                UINT64_LIMIT,
            )

    @pytest.mark.parametrize("param, msg", NO_ENOUGH_GAS_PARAMS)
    def test_mint_no_enough_gas(self, erc20_contract, param, msg):
        with pytest.raises(ValueError, match=msg):
            erc20_contract.mint_tokens(
                erc20_contract.account,
                erc20_contract.account.address,
                1,
                **param,
            )

    def test_totalSupply(self, erc20_contract):
        total_before = erc20_contract.contract.functions.totalSupply().call()
        amount = random.randint(0, 10000)
        erc20_contract.mint_tokens(erc20_contract.account, erc20_contract.account.address, amount)
        total_after = erc20_contract.contract.functions.totalSupply().call()
        assert total_before + amount == total_after, "Total supply is not correct"

    def test_transferSolana(self, sol_client, erc20_contract, solana_associated_token_mintable_erc20):
        acc, token_mint, solana_address = solana_associated_token_mintable_erc20
        amount = random.randint(10000, 1000000)
        sol_balance_before = sol_client.get_balance(acc.public_key).value
        contract_balance_before = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()

        opts = TokenAccountOpts(token_mint)
        token_data = sol_client.get_token_accounts_by_owner_json_parsed(acc.public_key, opts).value[0]
        token_balance_before = token_data.account.data.parsed["info"]["tokenAmount"]["amount"]
        erc20_contract.transfer_solana(erc20_contract.account, bytes(solana_address), amount)
        wait_condition(
            lambda: int(
                sol_client.get_token_accounts_by_owner_json_parsed(acc.public_key, opts)
                .value[0]
                .account.data.parsed["info"]["tokenAmount"]["amount"]
            )
            > int(token_balance_before),
            timeout_sec=30,
        )

        sol_balance_after = sol_client.get_balance(acc.public_key).value
        token_data = sol_client.get_token_accounts_by_owner_json_parsed(acc.public_key, opts).value[0]
        token_balance_after = token_data.account.data.parsed["info"]["tokenAmount"]["amount"]
        contract_balance_after = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()

        assert (
            int(token_balance_after) - int(token_balance_before) == amount
        ), "Token balance for sol account is not correct"
        assert contract_balance_before - contract_balance_after == amount, "Contract balance is not correct"
        assert sol_balance_after == sol_balance_before, "Sol balance is changed"

    def test_approveSolana(
        self,
        erc20_contract,
        sol_client,
        solana_associated_token_mintable_erc20,
    ):
        acc, token_mint, solana_address = solana_associated_token_mintable_erc20
        amount = random.randint(10000, 1000000)
        opts = TokenAccountOpts(token_mint)
        erc20_contract.approve_solana(erc20_contract.account, bytes(acc.public_key), amount)
        wait_condition(
            lambda: len(sol_client.get_token_accounts_by_delegate_json_parsed(acc.public_key, opts).value) > 0,
            timeout_sec=30,
        )
        token_account = sol_client.get_token_accounts_by_delegate_json_parsed(acc.public_key, opts).value[0].account
        assert int(token_account.data.parsed["info"]["delegatedAmount"]["amount"]) == amount
        assert int(token_account.data.parsed["info"]["delegatedAmount"]["decimals"]) == erc20_contract.decimals

    def test_claim(
        self,
        erc20_contract,
        sol_client,
        solana_associated_token_mintable_erc20,
        pytestconfig,
    ):
        acc, token_mint, solana_address = solana_associated_token_mintable_erc20
        balance_before = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()
        sent_amount = random.randint(10, 1000)
        erc20_contract.transfer_solana(erc20_contract.account, bytes(solana_address), sent_amount)
        trx = Transaction()
        trx.add(
            instructions.approve(
                instructions.ApproveParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=solana_address,
                    delegate=sol_client.get_erc_auth_address(
                        erc20_contract.account.address,
                        erc20_contract.contract.address,
                        pytestconfig.environment.evm_loader,
                    ),
                    owner=acc.public_key,
                    amount=sent_amount,
                    signers=[],
                )
            )
        )
        sol_client.send_transaction(trx, acc, opts=TxOpts(skip_preflight=False, skip_confirmation=False))

        claim_amount = random.randint(10, sent_amount)
        erc20_contract.claim(erc20_contract.account, bytes(solana_address), claim_amount)
        balance_after = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()

        assert balance_after == balance_before - sent_amount + claim_amount, "Balance is not correct"

    def test_claimTo(
        self,
        erc20_contract,
        sol_client,
        solana_associated_token_mintable_erc20,
        pytestconfig,
    ):
        acc, token_mint, solana_address = solana_associated_token_mintable_erc20
        new_account = self.accounts.create_account()
        user1_balance_before = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()
        user2_balance_before = erc20_contract.contract.functions.balanceOf(new_account.address).call()
        sent_amount = random.randint(10, 1000)
        erc20_contract.transfer_solana(erc20_contract.account, bytes(solana_address), sent_amount)
        trx = Transaction()
        trx.add(
            instructions.approve(
                instructions.ApproveParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=solana_address,
                    delegate=sol_client.get_erc_auth_address(
                        erc20_contract.account.address,
                        erc20_contract.contract.address,
                        pytestconfig.environment.evm_loader,
                    ),
                    owner=acc.public_key,
                    amount=sent_amount,
                    signers=[],
                )
            )
        )
        sol_client.send_transaction(trx, acc, opts=TxOpts(skip_preflight=False, skip_confirmation=False))

        claim_amount = random.randint(10, sent_amount)
        erc20_contract.claim_to(erc20_contract.account, bytes(solana_address), new_account.address, claim_amount)
        user1_balance_after = erc20_contract.contract.functions.balanceOf(erc20_contract.account.address).call()
        user2_balance_after = erc20_contract.contract.functions.balanceOf(new_account.address).call()

        assert user1_balance_after == user1_balance_before - sent_amount, "User1 balance is not correct"
        assert user2_balance_after == user2_balance_before + claim_amount, "User2 balance is not correct"


@allure.feature("ERC Verifications")
@allure.story("ERC20SPL: Tests for multiple actions in one transaction")
@pytest.mark.usefixtures("accounts", "web3_client", "sol_client")
class TestMultipleActionsForERC20:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts
    sol_client: SolanaClient

    def test_mint_transfer_burn(self, multiple_actions_erc20):
        sender_account = self.accounts[0]
        acc, contract = multiple_actions_erc20
        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()
        mint_amount = random.randint(10, 100000000)
        transfer_amount = random.randint(1, mint_amount - 1)
        burn_amount = random.randint(1, mint_amount - transfer_amount)

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.mintTransferBurn(
            mint_amount, acc.address, transfer_amount, burn_amount
        ).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert user_balance == transfer_amount + user_balance_before, "User balance is not correct"
        assert (
            contract_balance == mint_amount - transfer_amount - burn_amount + contract_balance_before
        ), "Contract balance is not correct"

    def test_mint_transfer_transfer_one_recipient(self, multiple_actions_erc20):
        sender_account = self.accounts[0]
        acc, contract = multiple_actions_erc20
        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()
        mint_amount = random.randint(10, 100000000)
        transfer_amount_1 = random.randint(1, mint_amount - 1)
        transfer_amount_2 = random.randint(1, mint_amount - transfer_amount_1)

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.mintTransferTransfer(
            mint_amount, acc.address, transfer_amount_1, acc.address, transfer_amount_2
        ).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert (
            user_balance == transfer_amount_1 + transfer_amount_2 + user_balance_before
        ), "User balance is not correct"
        assert (
            contract_balance == mint_amount - transfer_amount_1 - transfer_amount_2 + contract_balance_before
        ), "Contract balance is not correct"

    def test_mint_transfer_transfer_different_recipients(self, multiple_actions_erc20):
        new_account = self.accounts.create_account()
        sender_account = self.accounts[0]
        acc_1, contract = multiple_actions_erc20
        acc_2 = new_account
        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc_1.address).call()

        mint_amount = random.randint(10, 100000000)
        transfer_amount_1 = random.randint(1, mint_amount - 1)
        transfer_amount_2 = random.randint(1, mint_amount - transfer_amount_1)

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.mintTransferTransfer(
            mint_amount,
            acc_1.address,
            transfer_amount_1,
            acc_2.address,
            transfer_amount_2,
        ).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_1_balance = contract.functions.balance(acc_1.address).call()
        user_2_balance = contract.functions.balance(acc_2.address).call()

        assert user_1_balance == transfer_amount_1 + user_balance_before, "User 1 balance is not correct"
        assert user_2_balance == transfer_amount_2, "User 2 balance is not correct"
        assert (
            contract_balance == mint_amount - transfer_amount_1 - transfer_amount_2 + contract_balance_before
        ), "Contract balance is not correct"

    def test_transfer_mint_burn(self, multiple_actions_erc20):
        sender_account = self.accounts[0]
        acc, contract = multiple_actions_erc20
        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()
        mint_amount_1 = random.randint(10, 100000000)
        mint_amount_2 = random.randint(10, 100000000)
        transfer_amount = random.randint(1, mint_amount_1)
        burn_amount = random.randint(1, mint_amount_1 + mint_amount_2 - transfer_amount)

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.mint(mint_amount_1).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.transferMintBurn(
            acc.address, transfer_amount, mint_amount_2, burn_amount
        ).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert (
            contract_balance == mint_amount_1 + mint_amount_2 - transfer_amount - burn_amount + contract_balance_before
        ), "Contract balance is not correct"
        assert user_balance == transfer_amount + user_balance_before, "User balance is not correct"

    def test_transfer_mint_transfer_burn(self, multiple_actions_erc20):
        sender_account = self.accounts[0]
        acc, contract = multiple_actions_erc20
        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()
        mint_amount_1 = random.randint(10, 100000000)
        mint_amount_2 = random.randint(10, 100000000)
        transfer_amount_1 = random.randint(1, mint_amount_1)
        transfer_amount_2 = random.randint(1, mint_amount_1 + mint_amount_2 - transfer_amount_1)
        burn_amount = random.randint(1, mint_amount_1 + mint_amount_2 - transfer_amount_1 - transfer_amount_2)

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.mint(mint_amount_1).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.transferMintTransferBurn(
            acc.address,
            transfer_amount_1,
            mint_amount_2,
            transfer_amount_2,
            burn_amount,
        ).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert (
            contract_balance
            == mint_amount_1
            + mint_amount_2
            - transfer_amount_1
            - transfer_amount_2
            - burn_amount
            + contract_balance_before
        ), "Contract balance is not correct"
        assert (
            user_balance == transfer_amount_1 + transfer_amount_2 + user_balance_before
        ), "User balance is not correct"

    def test_mint_burn_transfer(self, multiple_actions_erc20):
        sender_account = self.accounts[0]
        acc, contract = multiple_actions_erc20
        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()
        mint_amount = random.randint(10, 100000000)
        burn_amount = random.randint(1, mint_amount - 1)
        transfer_amount = mint_amount - burn_amount

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.mintBurnTransfer(
            mint_amount,
            burn_amount,
            acc.address,
            transfer_amount,
        ).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()
        assert user_balance == transfer_amount + user_balance_before, "User balance is not correct"
        assert contract_balance == contract_balance_before, "Contract balance is not correct"

    def test_mint_mint(self, multiple_actions_erc20):
        sender_account = self.accounts[0]
        acc, contract = multiple_actions_erc20
        mint_amount1 = random.randint(10, 100000000)
        mint_amount2 = random.randint(10, 100000000)
        contract_balance_before = contract.functions.contractBalance().call()

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.mintMint(
            mint_amount1,
            mint_amount2,
        ).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        assert (
            contract_balance == contract_balance_before + mint_amount1 + mint_amount2
        ), "Contract balance is not correct"

    def test_mint_mint_transfer_transfer(self, multiple_actions_erc20):
        sender_account = self.accounts[0]
        acc, contract = multiple_actions_erc20
        mint_amount1 = random.randint(10, 100000000)
        mint_amount2 = random.randint(10, 100000000)
        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.mintMintTransferTransfer(
            mint_amount1, mint_amount2, acc.address
        ).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()
        assert user_balance == user_balance_before + mint_amount1 + mint_amount2, "User balance is not correct"
        assert contract_balance == contract_balance_before, "Contract balance is not correct"

    def test_burn_transfer_burn_transfer(self, multiple_actions_erc20):
        sender_account = self.accounts[0]
        acc, contract = multiple_actions_erc20
        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()

        mint_amount = random.randint(10, 100000000)
        burn_amount_1 = random.randint(1, mint_amount - 2)
        transfer_amount_1 = random.randint(1, mint_amount - burn_amount_1 - 2)
        burn_amount_2 = random.randint(1, mint_amount - burn_amount_1 - transfer_amount_1 - 1)
        transfer_amount_2 = random.randint(1, mint_amount - burn_amount_1 - transfer_amount_1 - burn_amount_2)

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.mint(mint_amount).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.burnTransferBurnTransfer(
            burn_amount_1,
            acc.address,
            transfer_amount_1,
            burn_amount_2,
            acc.address,
            transfer_amount_2,
        ).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()
        assert (
            contract_balance
            == mint_amount
            - transfer_amount_1
            - transfer_amount_2
            - burn_amount_1
            - burn_amount_2
            + contract_balance_before
        ), "Contract balance is not correct"
        assert (
            user_balance == transfer_amount_1 + transfer_amount_2 + user_balance_before
        ), "User balance is not correct"

    def test_burn_mint_transfer(self, multiple_actions_erc20):
        sender_account = self.accounts[0]
        acc, contract = multiple_actions_erc20
        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()

        mint_amount_1 = random.randint(10, 100000000)
        burn_amount = random.randint(1, mint_amount_1)
        mint_amount_2 = random.randint(10, 100000000)
        transfer_amount = random.randint(mint_amount_1 - burn_amount, mint_amount_1 - burn_amount + mint_amount_2)

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.mint(mint_amount_1).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)

        tx = self.web3_client.make_raw_tx(sender_account)
        instruction_tx = contract.functions.burnMintTransfer(
            burn_amount, mint_amount_2, acc.address, transfer_amount
        ).build_transaction(tx)
        self.web3_client.send_transaction(sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert (
            contract_balance == mint_amount_1 + mint_amount_2 - transfer_amount - burn_amount + contract_balance_before
        ), "Contract balance is not correct"
        assert user_balance == transfer_amount + user_balance_before, "User balance is not correct"
