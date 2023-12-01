pragma solidity ^0.8.3;

contract CommonCaller {
    function call_precompiled(address precompiledAddr, bytes memory callData)
        public
        returns (bytes memory)
    {
        (bool success, bytes memory result) = address(precompiledAddr).call(
            callData
        );
        require(success, "execution error");
        return result;
    }

    function staticcall_precompiled(address precompiledAddr, bytes memory callData)
        public
        returns (bytes memory)
    {
        (bool success, bytes memory result) = address(precompiledAddr).staticcall(
            callData
        );
        require(success, "execution error");
        return result;
    }

    function delegatecall_precompiled(address precompiledAddr, bytes memory callData)
        public
        returns (bytes memory)
    {
        (bool success, bytes memory result) = address(precompiledAddr).delegatecall(
            callData
        );
        require(success, "execution error");
        return result;
    }
}