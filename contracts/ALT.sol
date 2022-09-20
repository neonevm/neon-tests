pragma solidity ^0.8.10;

contract ALT {
    mapping(uint => uint) arr;

    function fill(uint N) public {
        for (uint i=0; i < N; i++){
            arr[i] = i + 1;
        }
    }
}