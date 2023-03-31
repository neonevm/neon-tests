pragma solidity ^0.8.0;

contract FirstContract {
    address [] public secondContractAddresses;
    address [] public thirdContractAddresses;
    uint private depth;
    uint private depthCounter;
    event SecondContractDeployed(address addr);
    event ThirdContractDeployed(address addr);
    constructor(uint _depth) {
        setDepth(_depth);
    }

    function deploySecondContract() public {
        if (depthCounter < depth) {
            depthCounter+=1;
            address secondContract = address(new SecondContract(address(this)));
            emit SecondContractDeployed(secondContract);
            secondContractAddresses.push(secondContract);
        }
    }

    function setDepth(uint _depth) public {
        depth = _depth;
        depthCounter = 0;
    }

    function getSecondDeployedContractCount() public view returns (uint count) {
        return secondContractAddresses.length;
    }
    function getThirdDeployedContractCount() public view returns (uint count) {
        return thirdContractAddresses.length;
    }
    function deployThirdContractViaCreate2(string memory stringSalt) public returns (address thirdContract){
        if (depthCounter < depth) {
        depthCounter+=1;
        thirdContract = _deployThirdContractViaCreate2(stringSalt);
        }
        return thirdContract;
        }

    function _deployThirdContractViaCreate2(string memory stringSalt) public returns (address thirdContract){
        bytes memory bytecode = type(ThirdContract).creationCode;
        bytecode = abi.encodePacked(bytecode, abi.encode(address(this)));
        bytecode = abi.encodePacked(bytecode, abi.encode(stringSalt));
        bytes32 salt = keccak256(abi.encodePacked(stringSalt));
        assembly {
            thirdContract := create2(0, add(bytecode, 32), mload(bytecode), salt)
        }
        thirdContractAddresses.push(thirdContract);
        emit ThirdContractDeployed(thirdContract);
    }

    function deployViaCreate2Twice(string memory stringSalt) public {
        _deployThirdContractViaCreate2(stringSalt);
        _deployThirdContractViaCreate2(stringSalt);
    }

}

contract SecondContract {
    address public firstContract;

    constructor(address _firstContractAddress) {
        address(_firstContractAddress).call(abi.encodeWithSignature("deploySecondContract()"));
    }
}

contract ThirdContract {
    address public firstContract;

    constructor(address _firstContractAddress, string memory stringSalt) {
        address(_firstContractAddress).call(abi.encodeWithSignature("deployThirdContractViaCreate2(string)", stringSalt));
    }

}
