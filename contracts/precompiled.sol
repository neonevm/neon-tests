pragma solidity ^0.8.3;

contract TestPrecompiledContracts {
    function call_precompiled(address precompiledAddr, bytes memory callData)
        public
        returns (bytes memory)
    {
//        bytes memory params = hex"2bd3e6d0f3b142924f5ca7b49ce5b9d54c4703d7ae5648e61d02268b1a0a9fb721611ce0a6af85915e2f1d70300909ce2e49dfad4a4619c8390cae66cefdb20400000000000000000000000000000000000000000000000011138ce750fa15c2";
        (bool success, bytes memory result) = address(precompiledAddr).call(
            callData
        );
        require(success, "execution error");
        return result;
    }
}