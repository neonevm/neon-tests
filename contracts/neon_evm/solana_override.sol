pragma solidity >=0.5.12;

contract solana_override {
    mapping(address => mapping(uint256 => uint256)) public data;

    function update_data_map(uint256 store_value) public {
        data[msg.sender][0] = uint256(store_value);
    }
}
