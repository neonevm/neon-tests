pragma solidity ^0.8.0;

contract DeployRecursionFactory {
    address [] public firstContractAddresses;
    address [] public secondContractAddresses;
    address [] public thirdContractAddresses;
    uint private depth;
    uint private depthCounter;
    event FirstContractDeployed(address addr);
    event SecondContractDeployed(address addr);
    event ThirdContractDeployed(address addr);
    constructor(uint _depth) {
        setDepth(_depth);
    }

    function deployFirstContract() public {
        if (depthCounter < depth) {
            depthCounter+=1;
            address firstContract = address(new FirstContract(address(this)));
            emit FirstContractDeployed(firstContract);
            firstContractAddresses.push(firstContract);
        }
    }

    function setDepth(uint _depth) public {
        depth = _depth;
        depthCounter = 0;
    }

    function getFirstDeployedContractCount() public view returns (uint count) {
        return firstContractAddresses.length;
    }
    function getSecondDeployedContractCount() public view returns (uint count) {
        return secondContractAddresses.length;
    }
    function getThirdDeployedContractCount() public view returns (uint count) {
        return thirdContractAddresses.length;
    }

    function deploySecondContractViaCreate2(string memory stringSalt) public returns (address secondContract){
        if (depthCounter < depth) {
        depthCounter+=1;
        secondContract = _deploySecondContractViaCreate2(stringSalt);
        }
        return secondContract;
        }

        function deployFirstContractViaCreate() public returns (address firstContract){
        if (depthCounter < depth) {
        depthCounter+=1;
        firstContract = _deployFirstContractViaCreate();
        }
        return firstContract;
        }

    function _deploySecondContractViaCreate2(string memory stringSalt) public returns (address secondContract){
        bytes memory bytecode = type(SecondContract).creationCode;
        bytecode = abi.encodePacked(bytecode, abi.encode(address(this), stringSalt));

        bytes32 salt = keccak256(abi.encodePacked(stringSalt));
        assembly {
            secondContract := create2(0, add(bytecode, 32), mload(bytecode), salt)
        }
        secondContractAddresses.push(secondContract);
        emit SecondContractDeployed(secondContract);
    }
    function _deployThirdContractViaCreate2(string memory stringSalt) public returns (address thirdContract){
        bytes memory bytecode = type(ThirdContract).creationCode;
        bytecode = abi.encodePacked(bytecode, abi.encode(address(this), stringSalt));

        bytes32 salt = keccak256(abi.encodePacked(stringSalt));
        assembly {
            thirdContract := create2(0, add(bytecode, 32), mload(bytecode), salt)
        }
        thirdContractAddresses.push(thirdContract);
        emit ThirdContractDeployed(thirdContract);
    }
    function _deployFirstContractViaCreate() public returns (address firstContract){
        bytes memory bytecode = type(FirstContract).creationCode;
        bytecode = abi.encodePacked(bytecode, abi.encode(address(this)));
        assembly {
            firstContract := create(0, add(bytecode, 0x20), mload(bytecode))
        }
        firstContractAddresses.push(firstContract);
        emit FirstContractDeployed(firstContract);
    }

    function deployViaCreate2Twice(string memory stringSalt) public {
        _deployThirdContractViaCreate2(stringSalt);
        _deployThirdContractViaCreate2(stringSalt);
    }

}

contract FirstContract {
    constructor(address _factoryAddress) {
        address(_factoryAddress).call(abi.encodeWithSignature("deployFirstContract()"));
    }
}

contract SecondContract {
    constructor(address _factoryAddress, string memory stringSalt) {
        address(_factoryAddress).call{gas: 19135420}(abi.encodeWithSignature("deploySecondContractViaCreate2(string)", stringSalt));
    }

}

contract ThirdContract {
    function doSomething() public returns (uint result) {
        return 1;
    }
}

contract RecursionCaller1 {
    uint public depth;
    uint private depthCounter;
    address private contract2;
    event SecondContractCalled(bool result);


    constructor(uint _depth, address _contract2, bool setDepthThroughContract2) {
        contract2 = _contract2;
        if (setDepthThroughContract2){
          address(contract2).call(abi.encodeWithSignature("callContract1SetDepth(address,uint)", address(this), _depth));
        }
        else {
            setDepth(_depth);
        }
    }

    function setDepth(uint _depth) public {
        depth = _depth;
        depthCounter = 0;
    }
    function callContract2() public {
        if (depthCounter < depth) {
            depthCounter+=1;
            (bool success, ) = address(contract2).call(abi.encodeWithSignature("callContract1Recursion(address)", address(this)));
            emit SecondContractCalled(success);
        }
    }

}

contract RecursionCaller2 {
    function callContract1Recursion(address _address) public {
        address(_address).call(abi.encodeWithSignature("callContract2()"));
    }
    function callContract1SetDepth(address _address, uint depth) public {
        address(_address).call(abi.encodeWithSignature("setDepth(uint)",depth));

    }
}