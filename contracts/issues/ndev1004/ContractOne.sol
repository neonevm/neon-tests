pragma solidity >=0.8.0;

/**
 * @title NDEV-1004: neon-evm incorrectly handles the exit reason of the failed sub CALL, causing incorrect execution flow against the Ethereum specification
 */

contract ContractOne {
    mapping(address => uint256) public addressBalances;

    function deposit() public payable {
        addressBalances[msg.sender] += msg.value;
    }
}
