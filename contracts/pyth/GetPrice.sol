// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./PythOracle.sol";
import "./@pythnetwork/pyth-sdk-solidity/PythStructs.sol";

contract GetPrice {

    function get(address addr, bytes32 id) public view returns (int64 price){
       PythOracle pyth = PythOracle(addr);
       PythStructs.Price memory result = pyth.getCurrentPrice(id);
       return result.price;
    }
}