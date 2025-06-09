pragma solidity >=0.5.12;

contract solana_override {
    bytes32[64] public a;
    uint256 public b = 0;
    mapping(address => mapping(uint256 => uint256)) public data;

    function update_b(uint256 store_value) public {
        b = store_value;
    }

    function update_data(uint256 size, uint256 value) public {
        uint n = 0;
        while (n < size) {
            data[msg.sender][n] = value;
            n = n + 1;
        }
    }

    function send_neon(address recipient, uint256 amount) public payable {
        (bool success, ) = recipient.call{value: amount}("");
        require(success, "Failed transfer");
    }
}
