pragma solidity >=0.5.12;

contract hello_world {
    uint public num = 5;
    string public text = "Hello World!";

    function call_hello_world() public view returns (string memory) {
        return text;
    }
}