pragma solidity ^0.8.10;

contract ALT {
    mapping(uint => uint) arr;

    constructor(uint _count) {
        fill(_count);
    }

    function fill(uint N) public returns (uint256){
        for (uint i=0; i < N - 7; i++){
            arr[i] = i + 1;
        }
        return N - 7;
    }
}