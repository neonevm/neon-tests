pragma solidity ^0.8.28;

import {Storage} from "../common/StorageSoliditySource.sol";
import {ICallSolana} from "../external/neon-contracts/contracts/precompiles/ICallSolana.sol";
pragma abicoder v2;

contract CallSolanaCaller {
    ICallSolana constant _callSolana =
        ICallSolana(0xFF00000000000000000000000000000000000006);
    struct Data {
        uint256 value1;
        uint256 value2;
    }
    mapping(uint256 => Data) public dataMap;
    uint256 public numberToStore;

    struct ExecuteArgs {
        uint64 lamports;
        bytes instruction;
    }

    struct ExecuteWithSeedArgs {
        uint64 lamports;
        bytes32 salt;
        bytes instruction;
    }

    struct ExecuteWithSeedArgsOverload {
        bytes32 salt;
        bytes instruction;
    }
    event LogBytes(bytes32 value);
    event LogStr(string value);
    event LogInt(uint value);
    event LogAddress(address value);
    event LogData(bytes32 program, bytes value);

    function getNeonAddress(address addr) public returns (bytes32) {
        bytes32 solanaAddr = _callSolana.getNeonAddress(addr);
        return solanaAddr;
    }

    function execute(uint64 lamports, bytes calldata instruction) public {
        numberToStore = 190;
        bytes32 returnData = bytes32(
            _callSolana.execute(lamports, instruction)
        );
        emit LogBytes(returnData);
    }

    function execute(bytes calldata instruction) public {
        numberToStore = 190;
        bytes32 returnData = bytes32(
            _callSolana.execute(instruction)
        );
        emit LogBytes(returnData);
    }

    function executeInIterativeMode(
        uint256 actionsNumber,
        uint64 lamports,
        bytes calldata instruction
    ) public returns (uint256) {
        doIterativeActions(actionsNumber);
        execute(lamports, instruction);
        return actionsNumber;
    }

    function solanaCallBeforeActionWithMatrix(
        uint[][] memory a,
        uint64 lamports,
        bytes calldata instruction
    ) public {
        // Matrix matrixContract = new Matrix();
        execute(lamports, instruction);
        uint sum = sumMatrixElements(a);
        emit LogInt(sum);
    }

    function solanaCallAfterActionWithMatrix(
        uint[][] memory a,
        uint64 lamports,
        bytes calldata instruction
    ) public {
        uint sum = sumMatrixElements(a);
        execute(lamports, instruction);
        emit LogInt(sum);
    }

    function solanaCallInsideActionWithMatrix(
        uint256 _numberToStore,
        uint[][] memory a,
        uint64 lamports,
        bytes calldata instruction
    ) public {
        numberToStore = _numberToStore;
        uint sum = 0;
        for (uint i = 0; i < a.length; i++) {
            for (uint j = 0; j < a[i].length; j++) {
                if (i == a.length / 2) {
                    execute(lamports, instruction);
                }
                sum += a[i][j];
            }
        }
        emit LogInt(sum);
    }

    function solanaCallInsideActionWithMatrixWithRevert(
        uint256 _numberToStore,
        uint[][] memory a,
        uint64 lamports,
        bytes calldata instruction
    ) public {
        numberToStore = _numberToStore;
        uint sum = 0;
        for (uint i = 0; i < a.length; i++) {
            for (uint j = 0; j < a[i].length; j++) {
                if (i == a.length / 2) {
                    execute(lamports, instruction);
                }
                sum += a[i][j];
            }
        }
        emit LogInt(sum);
        require(false, "Revert after solana call");
    }

    function batchExecuteInIterativeMode(
        uint256 actionsNumber,
        ExecuteArgs[] memory _args
    ) public {
        doIterativeActions(actionsNumber);
        batchExecute(_args);
    }

    function batchExecuteInIterativeModeWithoutLamport(
        uint256 actionsNumber,
        bytes[] memory _args
    ) public {
        doIterativeActions(actionsNumber);
        batchExecuteWithoutLamports( _args);
    }

    function sendTokensAndExecuteInIterativeMode(
        uint256 actionsNumber,
        uint64 lamports,
        bytes calldata instruction
    ) public payable {
        executeInIterativeMode(actionsNumber, lamports, instruction);
    }

    function doIterativeActions(uint actionsNumber) public {
        // some actions to make the call iterative
        for (uint256 i = 0; i < actionsNumber; i++) {
            Data memory newData = Data({value1: 1, value2: 2});
            dataMap[i] = newData;
        }
    }

    function deployStorageAndCallSolana(
        uint64 lamports,
        bytes calldata instruction
    ) public {
        Storage storageContract = new Storage();
        storageContract.store(10);
        require(storageContract.retrieve() == 10);
        execute(lamports, instruction);
        emit LogAddress(address(storageContract));
    }

    function executeWithGetReturnData(
        uint64 lamports,
        bytes calldata instruction
    ) public {
        _callSolana.execute(lamports, instruction);
        (bytes32 program, bytes memory returnData) = _callSolana
            .getReturnData();
        emit LogData(program, returnData);
    }

    function batchExecute(ExecuteArgs[] memory _args) public {
        for (uint i = 0; i < _args.length; i++) {
            _callSolana.execute(_args[i].lamports, _args[i].instruction);
        }
        (bytes32 program, bytes memory returnData) = _callSolana
            .getReturnData();
        emit LogData(program, returnData);
    }

    function batchExecuteWithoutLamports(bytes[] memory _args) public {
        for (uint i = 0; i < _args.length; i++) {
            _callSolana.execute(_args[i]);
        }
        (bytes32 program, bytes memory returnData) = _callSolana
            .getReturnData();
        emit LogData(program, returnData);
    }

    function getPayer() public returns (bytes32) {
        bytes32 payer = _callSolana.getPayer();
        return payer;
    }

    function createResource(
        bytes32 salt,
        uint64 space,
        uint64 lamports,
        bytes32 owner
    ) external returns (bytes32) {
        bytes32 resource = _callSolana.createResource(
            salt,
            space,
            lamports,
            owner
        );
        return resource;
    }

    function getResourceAddress(bytes32 salt) external returns (bytes32) {
        bytes32 resource = _callSolana.getResourceAddress(salt);
        return resource;
    }

    function getSolanaPDA(
        bytes32 program_id,
        bytes memory seeds
    ) external returns (bytes32) {
        bytes32 pda = _callSolana.getSolanaPDA(program_id, seeds);
        return pda;
    }

    function getExtAuthority(bytes32 salt) external returns (bytes32) {
        bytes32 authority = _callSolana.getExtAuthority(salt);
        return authority;
    }

    function executeWithSeed(
        uint64 lamports,
        bytes32 salt,
        bytes calldata instruction
    ) public {
        bytes32 returnData = bytes32(
            _callSolana.executeWithSeed(lamports, salt, instruction)
        );
        emit LogBytes(returnData);
    }

    function executeWithSeed(
        bytes32 salt,
        bytes calldata instruction
    ) public {
        bytes32 returnData = bytes32(
            _callSolana.executeWithSeed(salt, instruction)
        );
        emit LogBytes(returnData);
    }

    function getReturnData() public returns (bytes32, bytes memory) {
        return _callSolana.getReturnData();
    }

    function batchExecuteWithSeed(ExecuteWithSeedArgs[] memory _args) public {
        for (uint i = 0; i < _args.length; i++) {
            _callSolana.executeWithSeed(
                _args[i].lamports,
                _args[i].salt,
                _args[i].instruction
            );
        }
    }

    function batchExecuteWithSeedOverload(ExecuteWithSeedArgsOverload[] memory _args) public {
        for (uint i = 0; i < _args.length; i++) {
            _callSolana.executeWithSeed(
                _args[i].salt,
                _args[i].instruction
            );
        }
    }

    function sumMatrixElements(uint[][] memory a) public pure returns (uint) {
        uint sum = 0;
        for (uint i = 0; i < a.length; i++) {
            for (uint j = 0; j < a[i].length; j++) {
                sum += a[i][j];
            }
        }
        return sum;
    }
}
