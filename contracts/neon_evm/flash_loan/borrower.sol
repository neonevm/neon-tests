// SPDX-License-Identifier: MIT
pragma solidity ^0.8.12;

contract LoanBorrower {


    receive() external payable {}

    function executeFlashLoan(uint256 amount) external payable{
        payable(msg.sender).transfer(amount);
    }
}