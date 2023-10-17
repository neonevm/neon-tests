pragma solidity >=0.7.0 <0.9.0;

contract TrivialRevert {
    function do_string_based_revert() public view {
        require(false, "Predefined revert happened");
    }
    function do_trivial_revert() public view {
        require(false);
    }
}

contract Caller {
    TrivialRevert public myRevert;

    constructor(address _address) {
        myRevert = TrivialRevert(_address);
    }

    function do_string_based_revert() public view {
         return myRevert.do_string_based_revert();
    }
}