pragma solidity >=0.7.0;
pragma abicoder v2;

import "./erc20_for_spl.sol";

contract multipleActionsERC20 {
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

}
