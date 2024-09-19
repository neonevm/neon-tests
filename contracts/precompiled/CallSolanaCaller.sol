pragma solidity >=0.7.0 <0.9.0;
pragma abicoder v2;

import "../external/neon-evm/call_solana.sol";


contract CallSolanaCaller {

    CallSolana constant _callSolana = CallSolana(0xFF00000000000000000000000000000000000006);
    struct ExecuteArgs {
        uint64 lamports;
        bytes instruction;
    }
    struct ExecuteWithSeedArgs {
        uint64 lamports;
        bytes32 salt;
        bytes instruction;
    }


    event LogBytes(bytes32 value);
    event LogStr(string value);
    event LogData(bytes32 program, bytes value);

    function getNeonAddress(address addr) public returns (bytes32){
        bytes32 solanaAddr = _callSolana.getNeonAddress(addr);
        return solanaAddr;
    }

    function execute(uint64 lamports, bytes calldata instruction) public {
        bytes32 returnData = bytes32(_callSolana.execute(lamports, instruction));
        emit LogBytes(returnData);

    }

    function execute_with_get_return_data(uint64 lamports, bytes calldata instruction) public {
        _callSolana.execute(lamports, instruction);
        (bytes32 program, bytes memory returnData) = _callSolana.getReturnData();
        emit LogData(program, returnData);
    }

    function batchExecute(ExecuteArgs[] memory _args) public {
        for(uint i = 0; i < _args.length; i++) {
            _callSolana.execute(_args[i].lamports, _args[i].instruction);
        }
        (bytes32 program, bytes memory returnData) = _callSolana.getReturnData();
        emit LogData(program, returnData);
    }

    function getPayer() public returns (bytes32){
        bytes32 payer = _callSolana.getPayer();
        return payer;
    }

    function createResource(bytes32 salt, uint64 space, uint64 lamports, bytes32 owner) external returns (bytes32){
        bytes32 resource = _callSolana.createResource(salt, space, lamports, owner);
        return resource;
    }

    function getResourceAddress(bytes32 salt) external returns (bytes32){
        bytes32 resource = _callSolana.getResourceAddress(salt);
        return resource;
    }

    function getSolanaPDA(bytes32 program_id, bytes memory seeds) external returns (bytes32){
        bytes32 pda = _callSolana.getSolanaPDA(program_id, seeds);
        return pda;
    }

    function getExtAuthority(bytes32 salt) external returns (bytes32){
        bytes32 authority = _callSolana.getExtAuthority(salt);
        return authority;
    }

    function executeWithSeed(uint64 lamports, bytes32 salt, bytes calldata instruction) public {
        bytes32 returnData = bytes32(_callSolana.executeWithSeed(lamports, salt, instruction));
        emit LogBytes(returnData);
    }

    function getReturnData() public returns (bytes32, bytes memory){
        return _callSolana.getReturnData();
    }

    function batchExecuteWithSeed(ExecuteWithSeedArgs[] memory _args) public {
        for(uint i = 0; i < _args.length; i++) {
            _callSolana.executeWithSeed(_args[i].lamports, _args[i].salt, _args[i].instruction);
        }
    }
}