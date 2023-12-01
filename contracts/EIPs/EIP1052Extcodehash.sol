pragma solidity ^0.8.0;
import '../opcodes/SelfDestroyable.sol';

contract EIP1052Checker {
    event ReceivedHash(bytes32 hash);
    event DestroyedContract(address addr);

    function getContractHash(address a) public view returns (bytes32 hash) {
        assembly {
            hash := extcodehash(a)
        }
    }

    function getContractHashWithLog(address a) public returns (bytes32 hash) {
        assembly {
            hash := extcodehash(a)
        }

        emit ReceivedHash(hash);
    }

    function getHashForDestroyedContract() public returns (bytes32 hash1, bytes32 hash2, address adr) {
        SelfDestroyable contr = new SelfDestroyable();
        hash1 = getContractHash(address(contr));
        emit ReceivedHash(hash1);

        contr.destroy(address(this));
        hash2 = getContractHash(address(contr));
        adr = address(contr);
        emit DestroyedContract(adr);
        emit ReceivedHash(hash2);
    }

    function getHashForDestroyedContractAfterRevert(address selfDestroyableContract, address selfDestroyableContractCaller) public {
        address(selfDestroyableContractCaller).call(abi.encodeWithSignature("callDestroy(address)", selfDestroyableContract));
        bytes32 hash3 = getContractHash(selfDestroyableContract);
        emit ReceivedHash(hash3);
    }
}

contract DestroyCaller {
    event ReceivedHash(bytes32 hash);

    function callDestroy(address addr) public  {
        bytes32 hash1 = getContractHash(addr);
        emit ReceivedHash(hash1);
        address(addr).call(abi.encodeWithSignature("destroy(address)", address(this)));
        bytes32 hash2 = getContractHash(addr);
        emit ReceivedHash(hash2);

        require(false, "My expected revert");
    }

    function getContractHash(address a) public view returns (bytes32 hash) {
        assembly {
            hash := extcodehash(a)
        }
    }

}