pragma solidity >=0.5.12;

contract  string_setter {
    string public text;


    function get() public view returns (string memory) {
        return text;
    }

    function set(string memory new_text) public payable {
        text = new_text;
    }
}