// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
// contract for checking returndatasize and returndatacopy opcodes
contract EIP211Checker {
    address dataProvider;
    event LogSize(uint size);
    event LogData(bytes data);

    event DPAddress(address dataProvider);

    constructor() {
        DataProvider dp = new DataProvider();
        dataProvider = address(dp);
        emit DPAddress(dataProvider);
    }

    function getReturnDataSize() public {
        address target = dataProvider;
        uint returnDataSize;
        bytes memory data = abi.encodeWithSignature("makeReturn()");
        assembly {
            let success := staticcall(gas(), target, add(data, 0x20), mload(data), 0, 0)
            returnDataSize := returndatasize()
        }
        emit LogSize(returnDataSize);
    }

    function _extractData(bytes memory returnData) private pure returns (bytes memory) {
        bytes memory result = new bytes(returnData.length);
        assembly {

        let size := returndatasize()
        let ptr := mload(0x40)
        mstore(ptr, size)
        result := add(ptr, 0x20)

        returndatacopy(result, 0, size)
        mstore(0x40, add(result, size))
        result := sub(result, 0x20)
        }
        return result;

    }

    function getReturnDataWithParams(uint _position, uint _size) public returns (bytes memory result) {
        bytes memory signature = abi.encodeWithSignature("makeReturn()");
        (, bytes memory returnData) = dataProvider.call(signature);
        result = new bytes(returnData.length);
        assembly {

        let size := returndatasize()
        let ptr := mload(0x40)
        mstore(ptr, size)
        result := add(ptr, 0x20)

        returndatacopy(result, _position, _size)
        mstore(0x40, add(result, _size))
        result := sub(result, 0x20)
        }
        emit LogData(result);
    }

    function getReturnDataForCall(string memory func) public returns (bytes memory data) {
        bytes memory signature = abi.encodeWithSignature("makeReturn()");
        (, bytes memory returnData) = dataProvider.call(signature);
        data = _extractData(returnData);
        signature = abi.encodeWithSignature(func);
        (, returnData) = dataProvider.call(signature);
        data = _extractData(returnData);
        emit LogData(data);
        if (keccak256(abi.encodePacked(func)) == keccak256(abi.encodePacked("makeSelfdestruct()"))) {
                dataProvider = address(new DataProvider());
        }
    }


    function getReturnDataForDelegateCall(string memory func) public returns (bytes memory data) {
        bytes memory signature = abi.encodeWithSignature("makeReturn()");
        (, bytes memory returnData) = dataProvider.call(signature);
        data = _extractData(returnData);
        signature = abi.encodeWithSignature(func);
        (, returnData) = dataProvider.delegatecall(signature);
        data = _extractData(returnData);
        emit LogData(data);
    }

    function getReturnDataForStaticCall(string memory func) public returns (bytes memory data) {
        bytes memory signature = abi.encodeWithSignature("makeReturn()");
        (, bytes memory returnData) = dataProvider.call(signature);
        data = _extractData(returnData);
        signature = abi.encodeWithSignature(func);
        (, returnData) = dataProvider.staticcall(signature);
        data = _extractData(returnData);
        emit LogData(data);
    }


    function getReturnDataSizeForCreate() public returns (uint size) {
        bytes memory bytecode = type(DataProvider).creationCode;
        address addr;
        assembly {
            addr := create(0, add(bytecode, 0x20), mload(bytecode))
            size := returndatasize()
        }
        emit LogSize(size);
    }

    function getReturnDataSizeForCreate2(string memory stringSalt) public returns (uint size) {
        bytes memory bytecode = type(DataProvider).creationCode;
        bytes memory addr;

        bytes32 salt = keccak256(abi.encodePacked(stringSalt));
        assembly {
            addr := create2(0, add(bytecode, 0x20), mload(bytecode), salt)
            size := returndatasize()
        }
        emit LogSize(size);

    }

    function getReturnDataForCreateWithRevert() public returns (bytes memory data) {
        bytes memory bytecode = type(RevertingContract).creationCode;
        address addr;
        bytes memory result;
        uint size;
        assembly {
            addr := create(0, add(bytecode, 0x20), mload(bytecode))
            size := returndatasize()
            let ptr := mload(0x40)
            mstore(ptr, size)
            result := add(ptr, 0x20)

            returndatacopy(result, 0, size)
            mstore(0x40, add(result, size))
            result := sub(result, 0x20)
        }
        emit LogData(result);
        return result;
    }

    function getReturnDataForCreate2WithRevert(string memory stringSalt) public returns (bytes memory data) {
        bytes memory bytecode = type(RevertingContract).creationCode;
        address addr;
        bytes memory result;
        uint size;
        bytes32 salt = keccak256(abi.encodePacked(stringSalt));

        assembly {
            addr := create2(0, add(bytecode, 0x20), mload(bytecode), salt)
            size := returndatasize()
            let ptr := mload(0x40)
            mstore(ptr, size)
            result := add(ptr, 0x20)
            returndatacopy(result, 0, size)
            mstore(0x40, add(result, size))
            result := sub(result, 0x20)
        }
        emit LogData(result);
        return result;
    }
}

contract DataProvider {
    address owner;

    constructor(){
        owner = msg.sender;
    }

    function makeReturn() public pure returns (string memory) {
        return "teststring";
    }

    function makeRevert() public pure {
       require(false, "Revert msg");
    }

    function makeStop() public pure {
       assembly {
           stop()
       }
    }
    function makeInvalid() public pure {
       assembly {
           invalid()
       }
    }
    function makeSelfdestruct() public {
        selfdestruct(payable(owner));
    }
}

contract RevertingContract {
    constructor() {
        require(false, "Revert msg");
    }
}
