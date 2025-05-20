// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.28;

import {ICallSolana} from "../external/neon-contracts/contracts/precompiles/ICallSolana.sol";
pragma abicoder v2;

contract RevisionChanger {
    uint256 public number_inner_contract_scope = 1;
    bytes32[64] public b;
    uint256 public number_outer_contract_scope = 2;

    function getVarB() public returns (bytes32[64] memory) {
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
    function changeGlobalVarB(uint256 n) public {
        bytes32[64] memory b = rch.getVarB();
        b[0] = bytes32(abi.encodePacked(n + n));
        require(false, "Wrong method taken from caller contract");
    }

    function checkGlobalVarBChanged(uint256 n) public {
        bytes32[64] memory b = rch.getVarB();
        for (uint i = 0; i < 64; i++) {
            require(
                b[i] == bytes32(abi.encodePacked(n)),
                "Global var is not changed"
            );
        }
    }
}

contract RevisionRevert {
    ICallSolana constant _callSolana =
        ICallSolana(0xFF00000000000000000000000000000000000006);

    constructor() payable {}

    event LogBytes(bytes32 value);

    function transferNeonSeveralTimes(
        uint256 transfersNumber,
        uint256 amount,
        address recipient
    ) public payable {
        require(
            address(this).balance >= transfersNumber * amount,
            "Insufficient contract balance"
        );
        for (uint256 i = 0; i < transfersNumber; i++) {
            (bool success, ) = recipient.call{value: amount}("");
            require(success, "Failed transfer");
        }

        uint x = 0;
        uint y = 500;
        uint z = x;
        while (x < y) {
            z++;
            x = z;
        }
    }

    function transferNeonAndCallSolana(
        uint64 lamports,
        bytes calldata instruction,
        uint256 amount,
        address recipient
    ) public payable {
        require(
            address(this).balance >= amount,
            "Insufficient contract balance"
        );

        (bool success, ) = recipient.call{value: amount}("");
        require(success, "Failed transfer");

        bytes32 returnData = bytes32(
            _callSolana.execute(lamports, instruction)
        );

        emit LogBytes(returnData);
    }

    function getPayer() public returns (bytes32) {
        bytes32 payer = _callSolana.getPayer();
        return payer;
    }
}
