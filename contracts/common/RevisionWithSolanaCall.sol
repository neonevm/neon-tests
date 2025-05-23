pragma solidity 0.8.28;
pragma abicoder v2;

import {ICallSolana} from "../external/neon-contracts/contracts/precompiles/ICallSolana.sol";

contract RevisionChangerWithSolanaCall {
    ICallSolana constant _callSolana =
        ICallSolana(0xFF00000000000000000000000000000000000006);

    constructor() payable {}

    event LogBytes(bytes32 value);

    function transferNeonSeveralTimes(
        uint256 transfersNumber,
        address recipient
    ) public payable {
        uint256 value = address(this).balance;
        uint256 amount = address(this).balance / transfersNumber;
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
        require(address(this).balance == 0, "Incorrect contract balance");
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
