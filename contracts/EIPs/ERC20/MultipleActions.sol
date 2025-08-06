pragma solidity >=0.7.0;

import {ERC20ForSplMintable} from "../../external/neon-contracts/contracts/token/ERC20ForSpl/erc20_for_spl.sol";

pragma abicoder v2;

contract MultipleActionsERC20 {
    uint256 data;
    ERC20ForSplMintable erc20;

    constructor(
        string memory _name,
        string memory _symbol,
        uint8 _decimals
    ) {
        erc20 = new ERC20ForSplMintable(
            _name,
            _symbol,
            _decimals,
            address(this)
        );
    }

    function getErc20Address() public view returns (address) {
        return address(erc20);
    }

    function balance(address who) public view returns (uint256) {
        return erc20.balanceOf(who);
    }

    function contractBalance() public view returns (uint256) {
        return erc20.balanceOf(address(this));
    }

    function mintTransferBurn(
        uint256 mint_amount,
        address transfer_to,
        uint256 transfer_amount,
        uint256 burn_amount
    ) public {
        erc20.mint(address(this), mint_amount);
        erc20.transfer(transfer_to, transfer_amount);
        erc20.burn(burn_amount);
    }

    function mintBurnTransfer(
        uint256 mint_amount,
        uint256 burn_amount,
        address transfer_to,
        uint256 transfer_amount
    ) public {
        erc20.mint(address(this), mint_amount);
        erc20.burn(burn_amount);
        erc20.transfer(transfer_to, transfer_amount);
    }

    function mintTransferTransfer(
        uint256 mint_amount,
        address transfer_to_1,
        uint256 transfer_amount_1,
        address transfer_to_2,
        uint256 transfer_amount_2
    ) public {
        erc20.mint(address(this), mint_amount);
        erc20.transfer(transfer_to_1, transfer_amount_1);
        erc20.transfer(transfer_to_2, transfer_amount_2);
    }

    function transferMintBurn(
        address transfer_to,
        uint256 transfer_amount,
        uint256 mint_amount,
        uint256 burn_amount
    ) public {
        erc20.transfer(transfer_to, transfer_amount);
        erc20.mint(address(this), mint_amount);
        erc20.burn(burn_amount);
    }

    function transferMintTransferBurn(
        address transfer_to,
        uint256 transfer_amount_1,
        uint256 mint_amount,
        uint256 transfer_amount_2,
        uint256 burn_amount
    ) public {
        erc20.transfer(transfer_to, transfer_amount_1);
        erc20.mint(address(this), mint_amount);
        erc20.transfer(transfer_to, transfer_amount_2);
        erc20.burn(burn_amount);
    }

    function burnTransferBurnTransfer(
        uint256 burn_amount_1,
        address transfer_to_1,
        uint256 transfer_amount_1,
        uint256 burn_amount_2,
        address transfer_to_2,
        uint256 transfer_amount_2
    ) public {
        erc20.burn(burn_amount_1);
        erc20.transfer(transfer_to_1, transfer_amount_1);
        erc20.burn(burn_amount_2);
        erc20.transfer(transfer_to_2, transfer_amount_2);
    }

    function mint(uint256 amount) public {
        erc20.mint(address(this), amount);
    }

    function burnMintTransfer(
        uint256 burn_amount,
        uint256 mint_amount,
        address transfer_to,
        uint256 transfer_amount
    ) public {
        erc20.burn(burn_amount);
        erc20.mint(address(this), mint_amount);
        erc20.transfer(transfer_to, transfer_amount);
    }

    function transferReadBalanceTransfer(
        uint256 transfer_amount,
        address transfer_to
    ) public {
        uint current_balance;
        uint balance_before = erc20.balanceOf(address(this));
        uint expected_balance = balance_before - transfer_amount;
        erc20.transfer(transfer_to, transfer_amount);
        for (uint256 i = 0; i < 50; i++) {
            current_balance = erc20.balanceOf(address(this));
            require(current_balance == expected_balance, "balance not updated");
        }
        erc20.transfer(transfer_to, transfer_amount);
    }

    function mintMint(
        uint256 mint_amount1,
        uint256 mint_amount2
    ) public {
        erc20.mint(address(this), mint_amount1);
        erc20.mint(address(this), mint_amount2);
    }

    function mintMintTransferTransfer(
        uint256 mint_amount1,
        uint256 mint_amount2,
        address transfer_to
    ) public {
        erc20.mint(address(this), mint_amount1);
        erc20.mint(address(this), mint_amount2);
        erc20.transfer(transfer_to, mint_amount1);
        erc20.transfer(transfer_to, mint_amount2);
    }


    function mintMintTransferTransferBurn(
        address transfer_to,
        uint256 mint_amount1,
        uint256 mint_amount2,
        uint256 transfer_amount_1,
        uint256 transfer_amount_2,
        uint256 burn_amount
    ) public {
        erc20.mint(address(this), mint_amount1);
        erc20.mint(address(this), mint_amount2);
        erc20.transfer(transfer_to, transfer_amount_1);
        erc20.transfer(transfer_to, transfer_amount_2);
        erc20.burn(burn_amount);
    }

    function transferFiveTimes(
        address transfer_to,
        uint256 transfer_amount_1,
        uint256 transfer_amount_2,
        uint256 transfer_amount_3,
        uint256 transfer_amount_4,
        uint256 transfer_amount_5
    ) public {
        erc20.transfer(transfer_to, transfer_amount_1);
        erc20.transfer(transfer_to, transfer_amount_2);
        erc20.transfer(transfer_to, transfer_amount_3);
        erc20.transfer(transfer_to, transfer_amount_4);
        erc20.transfer(transfer_to, transfer_amount_5);
    }

    function mintMintTransferTransferMintMintTransferTransfer( // 17 Solana transactions
        uint256 mint_amount1,
        uint256 mint_amount2,
        address transfer_to
    ) public {
        erc20.mint(address(this), mint_amount1);
        erc20.mint(address(this), mint_amount2);
        erc20.transfer(transfer_to, mint_amount1);
        erc20.transfer(transfer_to, mint_amount2);
        erc20.mint(address(this), mint_amount1);
        erc20.mint(address(this), mint_amount2);
        erc20.transfer(transfer_to, mint_amount1);
        erc20.transfer(transfer_to, mint_amount2);
    }

}
