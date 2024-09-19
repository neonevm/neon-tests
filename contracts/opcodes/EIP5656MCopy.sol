// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract MemoryCopy {

    function copy(bytes32 initData, uint24 dst, uint24 src, uint24 length) public pure returns (bytes32) {
        assembly {
            let p := mload(0x40)
            mstore(p, initData)
            mcopy(add(p, dst), add(p, src), length)
            return (p, 32)
        }
    }
}
