pragma solidity >=0.7.0 <0.9.0;
contract TrivialRevert {
    function do_string_based_revert() public view returns (uint256) {
        require(false, "Predefined revert happened");
    }
    function do_trivial_revert() public view returns (uint256) {
        require(false);
    }
}