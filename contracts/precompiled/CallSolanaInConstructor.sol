pragma solidity ^0.8.28;

import {Storage} from "../common/StorageSoliditySource.sol";
import {ICallSolana} from "../external/neon-contracts/contracts/precompiles/ICallSolana.sol";
pragma abicoder v2;

contract CallSolanaInConstructor {
    ICallSolana public constant _callSolana =
        ICallSolana(0xFF00000000000000000000000000000000000006);
    uint256 public storeNumber = 0;

    event LogBytes(bytes32 value);

    constructor(uint256 number, uint64 lamports, bytes memory instruction) {
        storeNumber = number;
        bytes32 returnData = bytes32(
            _callSolana.execute(lamports, instruction)
        );
        emit LogBytes(returnData);
    }

    function getStoreNumber() public returns (uint256) {
        return storeNumber;
    }
}
