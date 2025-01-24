// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;


contract StaticCaller {

    event Log(uint256 counter_value);
    event LogSuccess(bool success);


    // Функция для вызова метода get() контракта Counter через CALL
    function callGet(address _counterAddress) public returns (uint256) {
        // Формируем данные для вызова функции get()
        bytes memory data = abi.encodeWithSignature("get()");

        // Используем low-level вызов (staticcall для безопасного чтения)
        (bool success, bytes memory returnData) = _counterAddress.staticcall(data);

        require(success, "CALL failed");

        // Декодируем возвращаемые данные в uint256
        uint256 counter_value = abi.decode(returnData, (uint256));

        // Логируем декодированное значение
        emit Log(counter_value);

        return counter_value;
    }

    function callInc(address _counterAddress) public {
        // Формируем данные для вызова функции get()
        bytes memory data = abi.encodeWithSignature("inc()");

        // Используем low-level вызов staticcall для получения исключения
        (bool success, ) = _counterAddress.staticcall(data);
        emit LogSuccess(success);

    }
}