// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Caller {
    uint256 public count; // Переменная состояния Caller

    event CallResult(bool success, bytes data);
    event CallerCount(uint256 count);

    // Функция для увеличения собственного count
    function incrementCallerCount() public {
        count += 1;
        emit CallerCount(count);
    }

    // Функция для вызова метода increment() контракта Counter через DELEGATECALL
    function delegateCallIncrement(address counterAddress) public {
        // Формируем данные для вызова функции increment()
        bytes memory data = abi.encodeWithSignature("increment()");

        // Используем DELEGATECALL для вызова increment() в контракте Counter
        (bool success, bytes memory returnData) = counterAddress.delegatecall(data);

        // Логируем результат вызова
        emit CallResult(success, returnData);
    }

    // Функция для установки собственного count
    function setCallerCount(uint256 _value) public {
        count = _value;
        emit CallerCount(count);
    }
}