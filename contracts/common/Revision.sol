// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.12;

contract RevisionChanger {
    uint256 public number_inner_contract_scope = 1;
    bytes32[64] public b;
    uint256 public number_outer_contract_scope = 2;

    function getVarB() public view returns (bytes32[64] memory) {
        return b;
    }

    function powNumberInnerAndRollback(uint256 n) public {
        require(n > 0, "Exponent should be > 0");

        uint original = number_inner_contract_scope;
        uint computedValue = 1;

        for (uint i = 0; i < n; i++) {
            computedValue *= original;
            number_inner_contract_scope = computedValue;
        }
        number_inner_contract_scope = original;
    }

    function powNumberOuterAndRollback(uint256 n) public {
        require(n > 0, "Exponent should be > 0");

        uint original = number_outer_contract_scope;
        uint computedValue = 1;

        for (uint i = 0; i < n; i++) {
            computedValue *= original;
            number_outer_contract_scope = computedValue;
        }
        number_outer_contract_scope = original;
    }

    function changeGlobalVarB(uint256 n) public {
        for (uint i = 0; i < 64; i++) {
            b[i] = bytes32(abi.encodePacked(n));
        }
    }
}

contract RevisionChangerCaller {
    RevisionChanger rch;
    constructor(address revisionChangerAddress) {
        rch = RevisionChanger(revisionChangerAddress);
    }

    function callRevisionChangerMethods(uint256 n) public {
        rch.powNumberInnerAndRollback(n);
        rch.changeGlobalVarB(n);
        checkGlobalVarBChanged(n);
        rch.powNumberOuterAndRollback(n);
    }

    // we do not change rch.b value here
    // we need to have a func with the same signature as in the RevisionChanger contract
    function changeGlobalVarB(uint256 n) public view {
        bytes32[64] memory b = rch.getVarB();
        b[0] = bytes32(abi.encodePacked(n+n));
        require(false, "Wrong method taken from caller contract");
    }

    function checkGlobalVarBChanged(uint256 n) public view {
        bytes32[64] memory b = rch.getVarB();
        for (uint i = 0; i < 64; i++) {
            require(
                b[i] == bytes32(abi.encodePacked(n)),
                "Global var is not changed"
            );
        }
    }
}
