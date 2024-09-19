// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract TransientStorage {

    function save(bytes32 initData) public {
        assembly {
            tstore(0x0, initData)
        }
    }

    function read() public returns (bytes32 data) {
        assembly {
            data := tload(0x0)
        }
    }
}

contract TransientStorageCaller {
    TransientStorage ts = new TransientStorage();

    function saveAndRead(bytes32 initData) public returns (bytes32 data) {
        ts.save(initData);
        return ts.read();

    }
}