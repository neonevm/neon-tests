pragma solidity >=0.5.12;

contract Increase_storage {
    mapping(address => mapping(uint256 => uint256)) data;
    uint256 count = 0;

    constructor(){
        inc();
    }

    function inc() public {
        uint256 n = count +  32;

        while (count < n){
            data[msg.sender][count] = uint256(count);
            count = count + 1;
        }
    }
}