pragma solidity >=0.5.12;

contract storage_checker {
    bytes32[64] public a;
    uint256 public b = 0; // sell 65
    uint256 public c = 0; // sell 66
    mapping(address => mapping(uint256 => uint256)) public data;

    function update_b(uint256 value) public {
        b = value;
    }
    function update_c(uint256 value) public {
        c = value;
    }

    function check_b() public view {
        require(b == 239, "Wrong var b value!");
    }

    function update_data(uint256 size, uint256 value) public {
        uint n = 0;
        while (n < size) {
            data[msg.sender][n] = value;
            n = n + 1;
        }
    }

    function check_data(uint256 size) public view {
        uint n = 0;
        while (n < size) {
            require(data[msg.sender][n] == 123, "Wrong data value!");
            n = n + 1;
        }
    }

    function send_neon(address recipient, uint256 amount) public payable {
        (bool success, ) = recipient.call{value: amount}("");
        require(success, "Failed transfer");
    }
}
