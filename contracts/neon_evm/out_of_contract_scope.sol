pragma solidity 0.8.12;


contract SaveNumber {
    bytes32[64] public b;
    uint256 public non_zero_number;
    uint256 public new_var;

    function saveNumberToVar(uint256 number) public {
        new_var = non_zero_number + number;
        non_zero_number = number;
    }
}
