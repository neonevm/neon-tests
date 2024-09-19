pragma solidity >=0.8.10 <0.9.0;

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

    function deposit() payable external {}
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

    function doTrivialRevert() public  view {
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