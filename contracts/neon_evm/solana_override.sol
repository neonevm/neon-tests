pragma solidity >=0.5.12;

contract solana_override {
    bytes32[64] public a;
    uint256 public b = 0;

    function update_data(uint256 store_value) public {
        b = store_value;
    }

    function send_neon(address recipient, uint256 amount) public payable {
        (bool success, ) = recipient.call{value: amount}("");
        require(success, "Failed transfer");
    }
}
