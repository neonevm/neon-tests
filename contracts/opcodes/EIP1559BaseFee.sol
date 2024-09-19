pragma solidity ^0.8.7;

contract BaseFeeOpcode {
    event Log(uint256 baseFee);

    function baseFee() public returns (uint256) {
        return block.basefee;
    }
    function baseFeeTrx() public {
        uint256 baseFee =  block.basefee;
        emit Log(baseFee);
    }
}