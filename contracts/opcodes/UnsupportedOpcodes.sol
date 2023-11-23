pragma solidity ^0.8.4;

contract UnsupportedOpcodes {

    function baseFee() public returns (uint256){
        return block.basefee;
    }

    function coinbase() public returns (address){
        return block.coinbase;
    }

    function difficulty() public returns (uint256){
        return block.difficulty;
    }

    function gaslimit() public returns (uint256){
        return block.gaslimit;
    }

    function gasLeft() public returns (uint256){
        return gasleft();
    }
}