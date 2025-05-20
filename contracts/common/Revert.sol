pragma solidity >=0.8.10 <0.9.0;
pragma abicoder v2;

import {ICallSolana} from "../external/neon-contracts/contracts/precompiles/ICallSolana.sol";

error NumberTooHigh(uint256 from, uint256 number);

contract TrivialRevert {
    function doStringBasedRevert() public pure {
        require(false, "Predefined revert happened");
    }

    function doTrivialRevert() public pure {
        require(false);
    }

    function customErrorRevert(uint256 from, uint256 number) public pure {
        revert NumberTooHigh(from, number);
    }

    function doAssert() public pure {
        assert(false);
    }

    function deposit() external payable {}
}

contract FailingContract {
    constructor(bool shouldFail) {
        require(!shouldFail, "Constructor intentionally failed.");
    }
}

contract Caller {
    TrivialRevert public myRevert;
    FailingContract public deployedContract;

    constructor(address _address) {
        myRevert = TrivialRevert(_address);
    }

    function doTrivialRevert() public view {
        return myRevert.doTrivialRevert();
    }

    function doTrivialRevertAferIterativeActions() public view {
        uint x = 0;
        uint y = 3000;
        uint z = x;
        while (x < y) {
            z++;
            x = z;
        }

        if (y - z == 1) {
            z++;
        }

        return myRevert.doTrivialRevert();
    }

    function doStringBasedRevert() public view {
        return myRevert.doStringBasedRevert();
    }

    function doCustomErrorRevert(uint256 from, uint256 number) public view {
        return myRevert.customErrorRevert(from, number);
    }

    function doAssert() public view {
        return myRevert.doAssert();
    }

    function deployContract() public {
        new FailingContract(true);
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
