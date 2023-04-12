pragma solidity ^0.8.4;

contract basefeeCaller {
    uint256 public baseFee;

    constructor() {
        baseFee = block.basefee; // get the current BASEFEE value
    }


}