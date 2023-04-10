// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
// contract for checking returndatasize and returndatacopy opcodes
contract EIP211Checker {
    uint256 public dataSize;
    bytes public extractedData;
    function setDataSize() public {
        DataProvider dataProvider = new DataProvider();
        address target = address (dataProvider);
        uint returnDataSize;
        bytes memory data = abi.encodeWithSignature("getData()");
        assembly {
            let success := staticcall(gas(), target, add(data, 0x20), mload(data), 0, 0)
            returnDataSize := returndatasize()
        }
        dataSize = returnDataSize;
    }
    function extractData() public returns (bytes memory) {
        DataProvider dataProvider = new DataProvider();
        address target = address(dataProvider);
        bytes memory data = abi.encodeWithSignature("getData()");

        (bool success, bytes memory returnData) = target.call(data);

        if (success) {
            bytes memory result = new bytes(returnData.length);
            assembly {
                returndatacopy(add(result, 32), 0, mload(returnData))
                mstore(result, mload(returnData))
            }
            return result;
        } else {
            revert("Data extraction failed");
        }
    }

    function setData() public {
        extractedData = extractData();
    }
}

contract DataProvider {
    string public data="teststring";

    function getData() public view returns (string memory) {
        return data;
    }
}

