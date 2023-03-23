pragma solidity ^0.8.3;

contract TestPrecompiledContracts {
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
}