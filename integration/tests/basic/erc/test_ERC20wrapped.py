import random

import allure
import pytest
import web3
from solana.rpc.types import TokenAccountOpts, TxOpts
from solana.transaction import Transaction
from spl.token import instructions
from spl.token.constants import TOKEN_PROGRAM_ID

from integration.tests.basic.helpers.assert_message import ErrorMessage
from integration.tests.basic.helpers.basic import BaseMixin
from utils import metaplex
from utils.helpers import gen_hash_of_block, wait_condition

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
UINT64_LIMIT = 18446744073709551615
MAX_TOKENS_AMOUNT = 1000000000000000

NO_ENOUGH_GAS_PARAMS = [
    ({"gas_price": 0}, "transaction underpriced"),
    ({"gas": 0}, "gas limit reached"),
]


@allure.feature("ERC Verifications")
@allure.story(
    "ERC20SPL: Tests for contracts created by createErc20ForSplMintable and createErc20ForSpl calls"
)
class TestERC20wrapperContract(BaseMixin):
    @pytest.fixture
    def restore_balance(self, erc20_spl_mintable):
        yield
        default_value = MAX_TOKENS_AMOUNT
        current_balance = erc20_spl_mintable.contract.functions.balanceOf(
            erc20_spl_mintable.account.address
        ).call()
        if current_balance > default_value:
            erc20_spl_mintable.burn(
                erc20_spl_mintable.account,
                erc20_spl_mintable.account.address,
                current_balance - default_value,
            )
        else:
            erc20_spl_mintable.mint_tokens(
                erc20_spl_mintable.account,
                erc20_spl_mintable.account.address,
                default_value - current_balance,
            )

    def test_metaplex_data_mintable(self, erc20_spl_mintable):
        mint_key = erc20_spl_mintable.contract.functions.findMintAccount().call()
        metaplex.wait_account_info(self.sol_client, mint_key)
        metadata = metaplex.get_metadata(self.sol_client, mint_key)
        assert metadata["data"]["name"] == erc20_spl_mintable.name
        assert metadata["data"]["symbol"] == erc20_spl_mintable.symbol
        assert metadata["is_mutable"] is False

    def test_metaplex_data(self, erc20_spl):
        metaplex.wait_account_info(self.sol_client, erc20_spl.token_mint.pubkey)
        metadata = metaplex.get_metadata(self.sol_client, erc20_spl.token_mint.pubkey)
        assert metadata["data"]["name"] == erc20_spl.name
        assert metadata["data"]["symbol"] == erc20_spl.symbol
        assert metadata["is_mutable"] is True

    @pytest.mark.parametrize("mintable", [True, False])
    def test_balanceOf(self, erc20_spl, erc20_spl_mintable, mintable):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        transfer_amount = random.randint(0, 100)
        initial_balance = erc20.contract.functions.balanceOf(
            self.recipient_account.address
        ).call()
        self.web3_client.send_erc20(
            erc20.account,
            self.recipient_account,
            transfer_amount,
            erc20.contract.address,
            abi=erc20.contract.abi,
        )
        assert (
            erc20.contract.functions.balanceOf(self.recipient_account.address).call()
            == initial_balance + transfer_amount
        )

    @pytest.mark.parametrize("mintable", [True, False])
    @pytest.mark.parametrize(
        "block_len, expected_exception",
        [(20, web3.exceptions.InvalidAddress), (5, web3.exceptions.ValidationError)],
    )
    def test_balanceOf_with_incorrect_address(
        self, erc20_spl_mintable, erc20_spl, block_len, expected_exception, mintable
    ):
        address = gen_hash_of_block(block_len)
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        with pytest.raises(expected_exception):
            return erc20.contract.functions.balanceOf(address).call()

    def test_mint_to_self(self, erc20_spl_mintable, restore_balance):
        balance_before = erc20_spl_mintable.contract.functions.balanceOf(
            erc20_spl_mintable.account.address
        ).call()
        amount = random.randint(1, MAX_TOKENS_AMOUNT)
        erc20_spl_mintable.mint_tokens(
            erc20_spl_mintable.account, erc20_spl_mintable.account.address, amount
        )
        balance_after = erc20_spl_mintable.contract.functions.balanceOf(
            erc20_spl_mintable.account.address
        ).call()
        assert balance_after == balance_before + amount

    def test_mint_to_another_account(self, erc20_spl_mintable, new_account):
        amount = random.randint(1, MAX_TOKENS_AMOUNT)
        erc20_spl_mintable.mint_tokens(
            erc20_spl_mintable.account, new_account.address, amount
        )
        balance_after = erc20_spl_mintable.contract.functions.balanceOf(
            new_account.address
        ).call()
        assert balance_after == amount

    def test_mint_by_no_minter_role(self, erc20_spl_mintable):
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match=ErrorMessage.MUST_HAVE_MINTER_ROLE_ERC20.value,
        ):
            erc20_spl_mintable.mint_tokens(
                self.recipient_account, self.recipient_account.address, 0
            )

    @pytest.mark.parametrize(
        "address_to, expected_exception, msg",
        [
            (20, web3.exceptions.InvalidAddress, ErrorMessage.INVALID_ADDRESS.value),
            (
                ZERO_ADDRESS,
                web3.exceptions.ContractLogicError,
                str.format(ErrorMessage.ZERO_ACCOUNT_ERC20.value, "mint to"),
            ),
        ],
    )
    def test_mint_with_incorrect_address(
        self, erc20_spl_mintable, address_to, expected_exception, msg
    ):
        address_to = (
            gen_hash_of_block(address_to) if isinstance(address_to, int) else address_to
        )
        with pytest.raises(expected_exception, match=msg):
            erc20_spl_mintable.mint_tokens(erc20_spl_mintable.account, address_to, 10)

    def test_mint_with_too_big_amount(self, erc20_spl_mintable):
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match="total mint amount exceeds uint64 max",
        ):
            erc20_spl_mintable.mint_tokens(
                erc20_spl_mintable.account,
                erc20_spl_mintable.account.address,
                UINT64_LIMIT,
            )

    @pytest.mark.parametrize("param, msg", NO_ENOUGH_GAS_PARAMS)
    def test_mint_no_enough_gas(self, erc20_spl_mintable, param, msg):
        with pytest.raises(ValueError, match=msg):
            erc20_spl_mintable.mint_tokens(
                erc20_spl_mintable.account,
                erc20_spl_mintable.account.address,
                1,
                **param,
            )

    def test_totalSupply(self, erc20_spl):
        total_before = erc20_spl.contract.functions.totalSupply().call()
        amount = random.randint(0, 10000)
        erc20_spl.claim(
            erc20_spl.account, bytes(erc20_spl.solana_associated_token_acc), amount
        )

        total_after = erc20_spl.contract.functions.totalSupply().call()
        assert total_after == total_before, "Total supply is not correct"

    def test_totalSupply_mintable(self, erc20_spl_mintable):
        total_before = erc20_spl_mintable.contract.functions.totalSupply().call()
        amount = random.randint(0, 10000)
        erc20_spl_mintable.mint_tokens(
            erc20_spl_mintable.account, erc20_spl_mintable.account.address, amount
        )
        total_after = erc20_spl_mintable.contract.functions.totalSupply().call()
        assert total_before + amount == total_after, "Total supply is not correct"

    @pytest.mark.parametrize("mintable", [True, False])
    def test_decimals(self, erc20_spl_mintable, erc20_spl, mintable):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        decimals = erc20.contract.functions.decimals().call()
        assert decimals == erc20.decimals

    @pytest.mark.parametrize("mintable", [True, False])
    def test_symbol(self, erc20_spl_mintable, erc20_spl, mintable):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        symbol = erc20.contract.functions.symbol().call()
        assert symbol == erc20.symbol

    @pytest.mark.parametrize("mintable", [True, False])
    def test_name(self, erc20_spl_mintable, erc20_spl, mintable):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        name = erc20.contract.functions.name().call()
        assert name == erc20.name

    @pytest.mark.parametrize("mintable", [True, False])
    def test_burn(self, erc20_spl_mintable, erc20_spl, restore_balance, mintable):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        balance_before = erc20.contract.functions.balanceOf(
            erc20.account.address
        ).call()
        total_before = erc20.contract.functions.totalSupply().call()
        amount = random.randint(0, 1000)
        erc20.burn(erc20.account, erc20.account.address, amount)
        balance_after = erc20.contract.functions.balanceOf(erc20.account.address).call()
        total_after = erc20.contract.functions.totalSupply().call()

        assert balance_after == balance_before - amount
        assert total_after == total_before - amount

    @pytest.mark.parametrize("mintable", [True, False])
    @pytest.mark.parametrize(
        "block_len, expected_exception, msg",
        [
            (20, web3.exceptions.InvalidAddress, ErrorMessage.INVALID_ADDRESS.value),
            (25, web3.exceptions.InvalidAddress, "is invalid"),
            (
                ZERO_ADDRESS,
                web3.exceptions.ContractLogicError,
                str.format(ErrorMessage.ZERO_ACCOUNT_ERC20.value, "burn from"),
            ),
        ],
    )
    def test_burn_incorrect_address(
        self,
        erc20_spl_mintable,
        erc20_spl,
        block_len,
        expected_exception,
        msg,
        mintable,
    ):
        address = (
            gen_hash_of_block(block_len) if isinstance(block_len, int) else block_len
        )
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        with pytest.raises(expected_exception, match=msg):
            erc20.burn(erc20.account, address, 1)

    @pytest.mark.parametrize("mintable", [True, False])
    def test_burn_more_than_total_supply(self, erc20_spl_mintable, erc20_spl, mintable):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        total = erc20.contract.functions.totalSupply().call()
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match=str.format(ErrorMessage.AMOUNT_EXCEEDS_BALANCE_ERC20.value, "burn"),
        ):
            erc20.burn(erc20.account, erc20.account.address, total + 1)

    @pytest.mark.parametrize("mintable", [True, False])
    @pytest.mark.parametrize("param, msg", NO_ENOUGH_GAS_PARAMS)
    def test_burn_no_enough_gas(
        self, erc20_spl_mintable, erc20_spl, param, msg, mintable
    ):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        with pytest.raises(ValueError, match=msg):
            erc20.burn(erc20.account, erc20.account.address, 1, **param)

    @pytest.mark.parametrize("mintable", [True, False])
    def test_burnFrom(
        self, erc20_spl_mintable, erc20_spl, new_account, restore_balance, mintable
    ):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        balance_before = erc20.contract.functions.balanceOf(
            erc20.account.address
        ).call()
        total_before = erc20.contract.functions.totalSupply().call()
        amount = random.randint(0, 1000)
        erc20.approve(erc20.account, new_account.address, amount)
        erc20.burn_from(
            signer=new_account, from_address=erc20.account.address, amount=amount
        )

        balance_after = erc20.contract.functions.balanceOf(erc20.account.address).call()
        total_after = erc20.contract.functions.totalSupply().call()
        assert balance_after == balance_before - amount
        assert total_after == total_before - amount

    @pytest.mark.parametrize("mintable", [True, False])
    def test_burnFrom_without_allowance(
        self, erc20_spl_mintable, erc20_spl, new_account, mintable
    ):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match=ErrorMessage.INSUFFICIENT_ALLOWANCE_ERC20.value,
        ):
            erc20.burn_from(new_account, erc20.account.address, 10)

    @pytest.mark.parametrize("mintable", [True, False])
    def test_burnFrom_more_than_allowanced(
        self, erc20_spl_mintable, erc20_spl, new_account, mintable
    ):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        amount = 2
        erc20.approve(erc20.account, new_account.address, amount)
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match=ErrorMessage.INSUFFICIENT_ALLOWANCE_ERC20.value,
        ):
            erc20.burn_from(new_account, erc20.account.address, amount + 1)

    @pytest.mark.parametrize("mintable", [True, False])
    def test_burnFrom_incorrect_address(self, erc20_spl_mintable, erc20_spl, mintable):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        with pytest.raises(web3.exceptions.InvalidAddress):
            erc20.burn_from(erc20.account, gen_hash_of_block(20), 1)

    @pytest.mark.parametrize("mintable", [True, False])
    @pytest.mark.parametrize("param, msg", NO_ENOUGH_GAS_PARAMS)
    def test_burnFrom_no_enough_gas(
        self, erc20_spl_mintable, erc20_spl, new_account, param, msg, mintable
    ):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        erc20.approve(erc20.account, new_account.address, 1)
        with pytest.raises(ValueError, match=msg):
            erc20.burn_from(new_account, erc20.account.address, 1, **param)

    @pytest.mark.parametrize("mintable", [True, False])
    def test_approve_more_than_total_supply(
        self, erc20_spl_mintable, erc20_spl, new_account, mintable
    ):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        amount = erc20.contract.functions.totalSupply().call() + 1
        erc20.approve(erc20.account, new_account.address, amount)
        allowance = erc20.contract.functions.allowance(
            erc20.account.address, new_account.address
        ).call()
        assert allowance == amount

    @pytest.mark.parametrize("mintable", [True, False])
    @pytest.mark.parametrize(
        "block_len, expected_exception, msg",
        [
            (20, web3.exceptions.InvalidAddress, ErrorMessage.INVALID_ADDRESS.value),
            (
                ZERO_ADDRESS,
                web3.exceptions.ContractLogicError,
                str.format(ErrorMessage.ZERO_ACCOUNT_ERC20.value, "approve to"),
            ),
        ],
    )
    def test_approve_incorrect_address(
        self,
        erc20_spl_mintable,
        erc20_spl,
        block_len,
        expected_exception,
        msg,
        mintable,
    ):
        address = (
            gen_hash_of_block(block_len) if isinstance(block_len, int) else block_len
        )
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        with pytest.raises(expected_exception, match=msg):
            erc20.approve(erc20.account, address, 1)

    @pytest.mark.parametrize("mintable", [True, False])
    @pytest.mark.parametrize("param, msg", NO_ENOUGH_GAS_PARAMS)
    def test_approve_no_enough_gas(
        self, erc20_spl_mintable, erc20_spl, param, msg, mintable
    ):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        with pytest.raises(ValueError, match=msg):
            erc20.approve(erc20.account, erc20.account.address, 1, **param)

    @pytest.mark.parametrize("mintable", [True, False])
    def test_allowance_incorrect_address(self, erc20_spl_mintable, erc20_spl, mintable):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        with pytest.raises(web3.exceptions.InvalidAddress):
            erc20.contract.functions.allowance(
                erc20.account.address, gen_hash_of_block(20)
            ).call()

    @pytest.mark.parametrize("mintable", [True, False])
    def test_allowance_for_new_account(
        self, erc20_spl_mintable, erc20_spl, new_account, mintable
    ):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        allowance = erc20.contract.functions.allowance(
            new_account.address, erc20.account.address
        ).call()
        assert allowance == 0

    @pytest.mark.parametrize("mintable", [True, False])
    def test_transfer(
        self, erc20_spl_mintable, erc20_spl, new_account, restore_balance, mintable
    ):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        balance_acc1_before = erc20.contract.functions.balanceOf(
            erc20.account.address
        ).call()
        balance_acc2_before = erc20.contract.functions.balanceOf(
            new_account.address
        ).call()
        total_before = erc20.contract.functions.totalSupply().call()
        amount = random.randint(1, 1000)
        erc20.transfer(erc20.account, new_account.address, amount)
        balance_acc1_after = erc20.contract.functions.balanceOf(
            erc20.account.address
        ).call()
        balance_acc2_after = erc20.contract.functions.balanceOf(
            new_account.address
        ).call()
        total_after = erc20.contract.functions.totalSupply().call()
        assert balance_acc1_after == balance_acc1_before - amount
        assert balance_acc2_after == balance_acc2_before + amount
        assert total_before == total_after

    @pytest.mark.parametrize("mintable", [True, False])
    @pytest.mark.parametrize(
        "block_len, expected_exception, msg",
        [
            (20, web3.exceptions.InvalidAddress, ErrorMessage.INVALID_ADDRESS.value),
            (
                ZERO_ADDRESS,
                web3.exceptions.ContractLogicError,
                str.format(ErrorMessage.ZERO_ACCOUNT_ERC20.value, "transfer to"),
            ),
        ],
    )
    def test_transfer_incorrect_address(
        self,
        erc20_spl_mintable,
        erc20_spl,
        block_len,
        expected_exception,
        msg,
        mintable,
    ):
        address = (
            gen_hash_of_block(block_len) if isinstance(block_len, int) else block_len
        )
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        with pytest.raises(expected_exception, match=msg):
            erc20.transfer(erc20.account, address, 1)

    @pytest.mark.parametrize("mintable", [True, False])
    def test_transfer_more_than_balance(self, erc20_spl_mintable, erc20_spl, mintable):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        balance = erc20.contract.functions.balanceOf(erc20.account.address).call()
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match=str.format(
                ErrorMessage.AMOUNT_EXCEEDS_BALANCE_ERC20.value, "transfer"
            ),
        ):
            erc20.transfer(erc20.account, erc20.account.address, balance + 1)

    @pytest.mark.parametrize("mintable", [True, False])
    @pytest.mark.parametrize("param, msg", NO_ENOUGH_GAS_PARAMS)
    def test_transfer_no_enough_gas(
        self, erc20_spl_mintable, erc20_spl, param, msg, mintable
    ):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        with pytest.raises(ValueError, match=msg):
            erc20.transfer(erc20.account, erc20.account.address, 1, **param)

    @pytest.mark.parametrize("mintable", [True, False])
    def test_transferFrom(
        self, erc20_spl_mintable, erc20_spl, new_account, restore_balance, mintable
    ):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        balance_acc1_before = erc20.contract.functions.balanceOf(
            erc20.account.address
        ).call()
        balance_acc2_before = erc20.contract.functions.balanceOf(
            new_account.address
        ).call()
        total_before = erc20.contract.functions.totalSupply().call()
        amount = random.randint(1, 10000)
        erc20.approve(erc20.account, new_account.address, amount)
        erc20.transfer_from(
            new_account, erc20.account.address, new_account.address, amount
        )
        balance_acc1_after = erc20.contract.functions.balanceOf(
            erc20.account.address
        ).call()
        balance_acc2_after = erc20.contract.functions.balanceOf(
            new_account.address
        ).call()
        total_after = erc20.contract.functions.totalSupply().call()
        assert balance_acc1_after == balance_acc1_before - amount
        assert balance_acc2_after == balance_acc2_before + amount
        assert total_before == total_after

    @pytest.mark.parametrize("mintable", [True, False])
    def test_transferFrom_without_allowance(
        self, erc20_spl_mintable, erc20_spl, new_account, mintable
    ):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match=ErrorMessage.INSUFFICIENT_ALLOWANCE_ERC20.value,
        ):
            erc20.transfer_from(
                signer=new_account,
                address_from=erc20.account.address,
                address_to=new_account.address,
                amount=10,
            )

    @pytest.mark.parametrize("mintable", [True, False])
    def test_transferFrom_more_than_allowanced(
        self, erc20_spl_mintable, erc20_spl, new_account, mintable
    ):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        amount = 2
        erc20.approve(erc20.account, new_account.address, amount)
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match=ErrorMessage.INSUFFICIENT_ALLOWANCE_ERC20.value,
        ):
            erc20.transfer_from(
                signer=new_account,
                address_from=erc20.account.address,
                address_to=new_account.address,
                amount=amount + 1,
            )

    @pytest.mark.parametrize("mintable", [True, False])
    def test_transferFrom_incorrect_address(
        self, erc20_spl_mintable, erc20_spl, mintable
    ):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        with pytest.raises(web3.exceptions.InvalidAddress):
            erc20.transfer_from(
                signer=erc20.account,
                address_from=erc20.account.address,
                address_to=gen_hash_of_block(20),
                amount=1,
            )

    @pytest.mark.parametrize("mintable", [True, False])
    def test_transferFrom_more_than_balance(
        self, erc20_spl_mintable, erc20_spl, new_account, mintable
    ):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        amount = erc20.contract.functions.balanceOf(erc20.account.address).call() + 1
        erc20.approve(erc20.account, new_account.address, amount)
        with pytest.raises(
            web3.exceptions.ContractLogicError,
            match=str.format(
                ErrorMessage.AMOUNT_EXCEEDS_BALANCE_ERC20.value, "transfer"
            ),
        ):
            erc20.transfer_from(
                signer=new_account,
                address_from=erc20.account.address,
                address_to=new_account.address,
                amount=amount,
            )

    @pytest.mark.parametrize("mintable", [True, False])
    @pytest.mark.parametrize("param, msg", NO_ENOUGH_GAS_PARAMS)
    def test_transferFrom_no_enough_gas(
        self, erc20_spl_mintable, erc20_spl, new_account, param, msg, mintable
    ):
        erc20 = erc20_spl_mintable if mintable else erc20_spl
        erc20.approve(erc20.account, new_account.address, 1)
        with pytest.raises(ValueError, match=msg):
            erc20.transfer_from(
                new_account, erc20.account.address, new_account.address, 1, **param
            )

    @pytest.mark.parametrize("mintable", [True, False])
    def test_transferSolana(
        self,
        erc20_spl_mintable,
        erc20_spl,
        sol_client,
        solana_associated_token_erc20,
        solana_associated_token_mintable_erc20,
        mintable,
    ):
        if mintable:
            erc20 = erc20_spl_mintable
            acc, token_mint, solana_address = solana_associated_token_mintable_erc20
        else:
            erc20 = erc20_spl
            acc, token_mint, solana_address = solana_associated_token_erc20

        amount = random.randint(10000, 1000000)
        sol_balance_before = sol_client.get_balance(acc.public_key).value
        contract_balance_before = erc20.contract.functions.balanceOf(
            erc20.account.address
        ).call()

        opts = TokenAccountOpts(token_mint)
        token_data = sol_client.get_token_accounts_by_owner_json_parsed(
            acc.public_key, opts
        ).value[0]
        token_balance_before = token_data.account.data.parsed["info"]["tokenAmount"][
            "amount"
        ]
        erc20.transfer_solana(erc20.account, bytes(solana_address), amount)
        wait_condition(
            lambda: int(
                sol_client.get_token_accounts_by_owner_json_parsed(acc.public_key, opts)
                .value[0]
                .account.data.parsed["info"]["tokenAmount"]["amount"]
            )
            > int(token_balance_before)
        )

        sol_balance_after = sol_client.get_balance(acc.public_key).value
        token_data = sol_client.get_token_accounts_by_owner_json_parsed(
            acc.public_key, opts
        ).value[0]
        token_balance_after = token_data.account.data.parsed["info"]["tokenAmount"][
            "amount"
        ]
        contract_balance_after = erc20.contract.functions.balanceOf(
            erc20.account.address
        ).call()

        assert (
            int(token_balance_after) - int(token_balance_before) == amount
        ), "Token balance for sol account is not correct"
        assert (
            contract_balance_before - contract_balance_after == amount
        ), "Contract balance is not correct"
        assert sol_balance_after == sol_balance_before, "Sol balance is changed"

    @pytest.mark.parametrize("mintable", [True, False])
    def test_approveSolana(
        self,
        erc20_spl_mintable,
        erc20_spl,
        sol_client,
        solana_associated_token_mintable_erc20,
        solana_associated_token_erc20,
        mintable,
    ):
        if mintable:
            erc20 = erc20_spl_mintable
            acc, token_mint, solana_address = solana_associated_token_mintable_erc20
        else:
            erc20 = erc20_spl
            acc, token_mint, solana_address = solana_associated_token_erc20

        amount = random.randint(10000, 1000000)
        opts = TokenAccountOpts(token_mint)
        erc20.approve_solana(erc20.account, bytes(acc.public_key), amount)
        wait_condition(
            lambda: len(
                sol_client.get_token_accounts_by_delegate_json_parsed(
                    acc.public_key, opts
                ).value
            )
            > 0
        )
        token_account = (
            sol_client.get_token_accounts_by_delegate_json_parsed(acc.public_key, opts)
            .value[0]
            .account
        )
        assert (
            int(token_account.data.parsed["info"]["delegatedAmount"]["amount"])
            == amount
        )
        assert (
            int(token_account.data.parsed["info"]["delegatedAmount"]["decimals"])
            == erc20.decimals
        )

    @pytest.mark.parametrize("mintable", [True, False])
    def test_claim(
        self,
        erc20_spl_mintable,
        sol_client,
        solana_associated_token_mintable_erc20,
        solana_associated_token_erc20,
        erc20_spl,
        pytestconfig,
        mintable,
    ):
        if mintable:
            acc, token_mint, solana_address = solana_associated_token_mintable_erc20
            erc20 = erc20_spl_mintable
        else:
            acc, token_mint, solana_address = solana_associated_token_erc20
            erc20 = erc20_spl
        balance_before = erc20.contract.functions.balanceOf(
            erc20.account.address
        ).call()
        sent_amount = random.randint(10, 1000)
        erc20.transfer_solana(erc20.account, bytes(solana_address), sent_amount)
        trx = Transaction()
        trx.add(
            instructions.approve(
                instructions.ApproveParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=solana_address,
                    delegate=sol_client.get_erc_auth_address(
                        erc20.account.address,
                        erc20.contract.address,
                        pytestconfig.environment.evm_loader,
                    ),
                    owner=acc.public_key,
                    amount=sent_amount,
                    signers=[],
                )
            )
        )
        sol_client.send_transaction(
            trx, acc, opts=TxOpts(skip_preflight=False, skip_confirmation=False)
        )

        claim_amount = random.randint(10, sent_amount)
        erc20.claim(erc20.account, bytes(solana_address), claim_amount)
        balance_after = erc20.contract.functions.balanceOf(erc20.account.address).call()

        assert (
            balance_after == balance_before - sent_amount + claim_amount
        ), "Balance is not correct"

    @pytest.mark.parametrize("mintable", [True, False])
    def test_claimTo(
        self,
        erc20_spl_mintable,
        erc20_spl,
        sol_client,
        solana_associated_token_mintable_erc20,
        solana_associated_token_erc20,
        pytestconfig,
        new_account,
        mintable,
    ):
        if mintable:
            acc, token_mint, solana_address = solana_associated_token_mintable_erc20
            erc20 = erc20_spl_mintable
        else:
            acc, token_mint, solana_address = solana_associated_token_erc20
            erc20 = erc20_spl
        user1_balance_before = erc20.contract.functions.balanceOf(
            erc20.account.address
        ).call()
        user2_balance_before = erc20.contract.functions.balanceOf(
            new_account.address
        ).call()
        sent_amount = random.randint(10, 1000)
        erc20.transfer_solana(erc20.account, bytes(solana_address), sent_amount)
        trx = Transaction()
        trx.add(
            instructions.approve(
                instructions.ApproveParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=solana_address,
                    delegate=sol_client.get_erc_auth_address(
                        erc20.account.address,
                        erc20.contract.address,
                        pytestconfig.environment.evm_loader,
                    ),
                    owner=acc.public_key,
                    amount=sent_amount,
                    signers=[],
                )
            )
        )
        sol_client.send_transaction(
            trx, acc, opts=TxOpts(skip_preflight=False, skip_confirmation=False)
        )

        claim_amount = random.randint(10, sent_amount)
        erc20.claim_to(
            erc20.account, bytes(solana_address), new_account.address, claim_amount
        )
        user1_balance_after = erc20.contract.functions.balanceOf(
            erc20.account.address
        ).call()
        user2_balance_after = erc20.contract.functions.balanceOf(
            new_account.address
        ).call()

        assert (
            user1_balance_after == user1_balance_before - sent_amount
        ), "User1 balance is not correct"
        assert (
            user2_balance_after == user2_balance_before + claim_amount
        ), "User2 balance is not correct"


@allure.feature("ERC Verifications")
@allure.story("ERC20SPL: Tests for multiple actions in one transaction")
class TestMultipleActionsForERC20(BaseMixin):
    def make_tx_object(self):
        tx = {
            "from": self.sender_account.address,
            "nonce": self.web3_client.eth.get_transaction_count(
                self.sender_account.address
            ),
            "gasPrice": self.web3_client.gas_price(),
        }
        return tx

    def test_mint_transfer_burn(self, multiple_actions_erc20):
        acc, contract = multiple_actions_erc20
        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()
        mint_amount = random.randint(10, 100000000)
        transfer_amount = random.randint(1, mint_amount - 1)
        burn_amount = random.randint(1, mint_amount - transfer_amount)

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mintTransferBurn(
            mint_amount, acc.address, transfer_amount, burn_amount
        ).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert (
            user_balance == transfer_amount + user_balance_before
        ), "User balance is not correct"
        assert (
            contract_balance
            == mint_amount - transfer_amount - burn_amount + contract_balance_before
        ), "Contract balance is not correct"

    def test_mint_transfer_transfer_one_recipient(self, multiple_actions_erc20):
        acc, contract = multiple_actions_erc20
        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()
        mint_amount = random.randint(10, 100000000)
        transfer_amount_1 = random.randint(1, mint_amount - 1)
        transfer_amount_2 = random.randint(1, mint_amount - transfer_amount_1)

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mintTransferTransfer(
            mint_amount, acc.address, transfer_amount_1, acc.address, transfer_amount_2
        ).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert (
            user_balance == transfer_amount_1 + transfer_amount_2 + user_balance_before
        ), "User balance is not correct"
        assert (
            contract_balance
            == mint_amount
            - transfer_amount_1
            - transfer_amount_2
            + contract_balance_before
        ), "Contract balance is not correct"

    def test_mint_transfer_transfer_different_recipients(
        self, multiple_actions_erc20, new_account
    ):
        acc_1, contract = multiple_actions_erc20
        acc_2 = new_account
        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc_1.address).call()

        mint_amount = random.randint(10, 100000000)
        transfer_amount_1 = random.randint(1, mint_amount - 1)
        transfer_amount_2 = random.randint(1, mint_amount - transfer_amount_1)

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mintTransferTransfer(
            mint_amount,
            acc_1.address,
            transfer_amount_1,
            acc_2.address,
            transfer_amount_2,
        ).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_1_balance = contract.functions.balance(acc_1.address).call()
        user_2_balance = contract.functions.balance(acc_2.address).call()

        assert (
            user_1_balance == transfer_amount_1 + user_balance_before
        ), "User 1 balance is not correct"
        assert user_2_balance == transfer_amount_2, "User 2 balance is not correct"
        assert (
            contract_balance
            == mint_amount
            - transfer_amount_1
            - transfer_amount_2
            + contract_balance_before
        ), "Contract balance is not correct"

    def test_transfer_mint_burn(self, multiple_actions_erc20):
        acc, contract = multiple_actions_erc20
        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()
        mint_amount_1 = random.randint(10, 100000000)
        mint_amount_2 = random.randint(10, 100000000)
        transfer_amount = random.randint(1, mint_amount_1)
        burn_amount = random.randint(1, mint_amount_1 + mint_amount_2 - transfer_amount)

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mint(mint_amount_1).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        tx = self.make_tx_object()
        instruction_tx = contract.functions.transferMintBurn(
            acc.address, transfer_amount, mint_amount_2, burn_amount
        ).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert (
            contract_balance
            == mint_amount_1
            + mint_amount_2
            - transfer_amount
            - burn_amount
            + contract_balance_before
        ), "Contract balance is not correct"
        assert (
            user_balance == transfer_amount + user_balance_before
        ), "User balance is not correct"

    def test_transfer_mint_transfer_burn(self, multiple_actions_erc20):
        acc, contract = multiple_actions_erc20
        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()
        mint_amount_1 = random.randint(10, 100000000)
        mint_amount_2 = random.randint(10, 100000000)
        transfer_amount_1 = random.randint(1, mint_amount_1)
        transfer_amount_2 = random.randint(
            1, mint_amount_1 + mint_amount_2 - transfer_amount_1
        )
        burn_amount = random.randint(
            1, mint_amount_1 + mint_amount_2 - transfer_amount_1 - transfer_amount_2
        )

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mint(mint_amount_1).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        tx = self.make_tx_object()
        instruction_tx = contract.functions.transferMintTransferBurn(
            acc.address,
            transfer_amount_1,
            mint_amount_2,
            transfer_amount_2,
            burn_amount,
        ).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

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
        acc, contract = multiple_actions_erc20
        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()
        mint_amount = random.randint(10, 100000000)
        burn_amount = random.randint(1, mint_amount - 1)
        transfer_amount = mint_amount - burn_amount

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mintBurnTransfer(
            mint_amount,
            burn_amount,
            acc.address,
            transfer_amount,
        ).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()
        assert (
            user_balance == transfer_amount + user_balance_before
        ), "User balance is not correct"
        assert (
            contract_balance == contract_balance_before
        ), "Contract balance is not correct"

    def test_mint_mint(self, multiple_actions_erc20):
        acc, contract = multiple_actions_erc20
        mint_amount1 = random.randint(10, 100000000)
        mint_amount2 = random.randint(10, 100000000)
        contract_balance_before = contract.functions.contractBalance().call()

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mintMint(
            mint_amount1,
            mint_amount2,
        ).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        assert (
            contract_balance == contract_balance_before + mint_amount1 + mint_amount2
        ), "Contract balance is not correct"

    def test_mint_mint_transfer_transfer(self, multiple_actions_erc20):
        acc, contract = multiple_actions_erc20
        mint_amount1 = random.randint(10, 100000000)
        mint_amount2 = random.randint(10, 100000000)
        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mintMintTransferTransfer(
            mint_amount1, mint_amount2, acc.address
        ).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()
        assert (
            user_balance == user_balance_before + mint_amount1 + mint_amount2
        ), "User balance is not correct"
        assert (
            contract_balance == contract_balance_before
        ), "Contract balance is not correct"

    def test_burn_transfer_burn_transfer(self, multiple_actions_erc20):
        acc, contract = multiple_actions_erc20
        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()

        mint_amount = random.randint(10, 100000000)
        burn_amount_1 = random.randint(1, mint_amount - 2)
        transfer_amount_1 = random.randint(1, mint_amount - burn_amount_1 - 2)
        burn_amount_2 = random.randint(
            1, mint_amount - burn_amount_1 - transfer_amount_1 - 1
        )
        transfer_amount_2 = random.randint(
            1, mint_amount - burn_amount_1 - transfer_amount_1 - burn_amount_2
        )

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mint(mint_amount).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        tx = self.make_tx_object()
        instruction_tx = contract.functions.burnTransferBurnTransfer(
            burn_amount_1,
            acc.address,
            transfer_amount_1,
            burn_amount_2,
            acc.address,
            transfer_amount_2,
        ).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

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
        acc, contract = multiple_actions_erc20
        contract_balance_before = contract.functions.contractBalance().call()
        user_balance_before = contract.functions.balance(acc.address).call()

        mint_amount_1 = random.randint(10, 100000000)
        burn_amount = random.randint(1, mint_amount_1)
        mint_amount_2 = random.randint(10, 100000000)
        transfer_amount = random.randint(
            mint_amount_1 - burn_amount, mint_amount_1 - burn_amount + mint_amount_2
        )

        tx = self.make_tx_object()
        instruction_tx = contract.functions.mint(mint_amount_1).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        tx = self.make_tx_object()
        instruction_tx = contract.functions.burnMintTransfer(
            burn_amount, mint_amount_2, acc.address, transfer_amount
        ).buildTransaction(tx)
        self.web3_client.send_transaction(self.sender_account, instruction_tx)

        contract_balance = contract.functions.contractBalance().call()
        user_balance = contract.functions.balance(acc.address).call()

        assert (
            contract_balance
            == mint_amount_1
            + mint_amount_2
            - transfer_amount
            - burn_amount
            + contract_balance_before
        ), "Contract balance is not correct"
        assert (
            user_balance == transfer_amount + user_balance_before
        ), "User balance is not correct"
