pragma solidity >=0.5.12;

contract IncreaseStorage {
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
    function incWithoutALT() public {
        uint256 current_count = 0;
        uint256 n = 10;

        while (current_count < n){
            data[msg.sender][current_count] = uint256(count);
            current_count = current_count + 1;
        }
    }
}