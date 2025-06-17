// SPDX-License-Identifier: MIT

pragma solidity >=0.7.0;
pragma abicoder v2;

import "../external/neon-contracts/contracts/token/ERC20ForSpl/erc20_for_spl.sol";

contract NeonErc20ForSpl is ERC20ForSplMintable {
    string public _name;
    string public _symbol;
    uint8 public _decimals;
    uint256 public _totalSupply;

    uint256 public exchangeRateStored;
    uint256 public supplyRatePerBlock;
    uint256 public accrualBlockNumber;

    constructor(
        string memory name,
        string memory symbol,
        uint8 decimals_,
        address mint_authority
    ) ERC20ForSplMintable(name, symbol, decimals_, mint_authority) {
        _name = name;
        _symbol = symbol;
        _decimals = decimals_;
    }

    function redeem(uint256 redeemTokens) public returns (uint256) {
        uint256 value = (redeemTokens * exchangeRateStored) / 10 ** 18;
        bool success = this.transfer(msg.sender, value);
        require(success, "ERC20ForSpl: redeem failed");
        return 0;
    }

    function exchangeRateCurrent() public returns (uint256) {
        // Simulate blockchain write
        uint256 rate = exchangeRateStored;
        exchangeRateStored = rate;
        return rate;
    }

    function set_exchange_rate(uint256 rate) public {
        exchangeRateStored = rate;
        uint256 expected = (this.totalSupply() * exchangeRateStored) / 10 ** 18;
        uint256 actual = this.balanceOf(address(this));
        require(actual == 0, "ERC20ForSpl: non-zero balance");
        if (expected > actual) {
            this.mint(address(this), expected - actual);
        }
    }

    function _mint_for_testing(address account, uint256 amount) public {
        this.mint(account, amount);
    }
}
