// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

/**
 * @title Ballot
 * @dev Implements voting process along with vote delegation
 */

contract BigGasFactory {

    BigGas[] private _big_gas;
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
        BigGas big_gas = new BigGas(
            PROCESS_GAS,
            RESERVE_GAS
        );
        _big_gas.push(big_gas);
        require(gasleft() >= PROCESS_GAS + RESERVE_GAS, "!gas");
        return 1;
    }

    function allBigGas() public returns (BigGas[] memory coll) {
        return coll;
    }
}

contract BigGas {

    uint256 public immutable PROCESS_GAS;
    uint256 public immutable RESERVE_GAS;
    address public owner;
    uint public gas_price;

    constructor(
        uint256 _processGas,
        uint256 _reserveGas
    ) {

        require(_processGas >= 850_000, "!process gas");
        require(_reserveGas >= 15_000, "!reserve gas");
        PROCESS_GAS = _processGas;
        RESERVE_GAS = _reserveGas;
        owner = msg.sender;
        gas_price = tx.gasprice;
    }

    function checkBigGasRequirements() public view returns (uint256) {
    // Check big int requirements
        require(gasleft() >= PROCESS_GAS + RESERVE_GAS, "!gas");
        return 1;
    }
}

