pragma solidity >=0.8.0;

contract ContractTwo {
    function deposit() public payable {}

    function getBalance() public view returns (uint256) {
        return address(this).balance;
    }

    function depositOnContractOne(address _contractOne) public {
        bytes memory payload = abi.encodeWithSignature("deposit()");
        (bool success, ) = _contractOne.call{value: 1, gas: 100000}(payload);
        require(!success);
    }
}
