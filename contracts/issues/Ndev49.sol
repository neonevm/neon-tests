// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

/**
 * @title Ballot
 * @dev Implements voting process along with vote delegation
 */


contract BigGasFactory1 {

    BigGasFactory2[] private _big_gas;
    uint256 public immutable PROCESS_GAS;
    uint256 public immutable RESERVE_GAS;

    constructor(
        uint256 _processGas,
        uint256 _reserveGas
    ) {

        require(_processGas >= 850_000, "!process gas");
        require(_reserveGas >= 15_000, "!reserve gas");
        PROCESS_GAS = _processGas;
        RESERVE_GAS = _reserveGas;
    }

    function checkBigGasRequirements() public returns (uint256) {
    // Create new contract form Factory and check big int requirements
        require(gasleft() >= PROCESS_GAS + RESERVE_GAS, "!gas");
        BigGasFactory2 big_gas = new BigGasFactory2(
            PROCESS_GAS,
            RESERVE_GAS
        );
        _big_gas.push(big_gas);
        return 1;
    }

    function allBigGas() public returns (BigGasFactory2[] memory coll) {
        return coll;
    }
}


contract BigGasFactory2 {

    Test[] private _test;
    uint256 public immutable PROCESS_GAS;
    uint256 public immutable RESERVE_GAS;
    uint public counter;

    constructor(
        uint256 _processGas,
        uint256 _reserveGas
    ) {

        require(_processGas >= 850_000, "!process gas");
        require(_reserveGas >= 15_000, "!reserve gas");
        PROCESS_GAS = _processGas;
        RESERVE_GAS = _reserveGas;
        counter = 0;
    }

    function checkBigGasRequirements() public returns (uint256) {
    // Check big int requirements
        require(gasleft() >= PROCESS_GAS + RESERVE_GAS, "!gas");
        do {
            Test test = new Test();
            _test.push(test);
            counter++;
        } while (counter != 5 );
        return counter;
    }
}

contract Test {

    address public owner;
    uint public gas_price;

    constructor() {
        owner = msg.sender;
        gas_price = tx.gasprice;
    }
}