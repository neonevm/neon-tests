// SPDX-License-Identifier: MIT
pragma solidity ^0.8.12;


contract LoanLender {
    uint256 public balance_before;
    uint256 public balance_after;

    constructor() payable {}

    function deposit() external payable {}

    receive() external payable {}


    function flashLoan(address borrower, uint256 amount) external payable {
        require(amount > 0, "Amount must be greater than 0");

        uint256 bbalance_before = address(this).balance;
        require(bbalance_before >= amount, "Not enough liquidity");

        (bool success,) = borrower.call{value: amount}(
            abi.encodeWithSignature("executeFlashLoan(uint256)", amount));

        require(success, "not success");
        require(address(this).balance == bbalance_before, "Loan not returned");
    }

    function powAmount(uint256 amount, uint256 n) public  returns(uint256)  {
        uint256 cbalance_before = address(this).balance;

        uint256 base = amount;
        uint256 pow_amount = 1;

        for (uint256 i = 0; i < n; i++) {
            pow_amount *= base;
        }

        uint256 cbalance_after = address(this).balance;
        return pow_amount;
    }
}