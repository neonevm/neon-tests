// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Caller {
    uint256 public count; // Переменная состояния Caller
    address public sender_in_counter;
    address public sender_in_caller;

    event CallResult(bool success, bytes data);
    event LogCounterValue(uint256 counter_value);
    event LogSuccess(bool success);
    event LogCallerCountValue(uint256 count);
    event LogSenderInCounter(address sender_in_counter);
    event LogSenderInCaller(address sender_in_caller);



    // Function to get the current count
    function get() public returns (uint) {
        emit LogCallerCountValue(count);
        return count;
    }

    // Function to increment count by 1
    function inc() public {
        count += 1;
    }

    // Функция для вызова метода increment() контракта Counter через CALL
    function callInc(address counterAddress) public {
        // Формируем данные для вызова функции increment()
        bytes memory data = abi.encodeWithSignature("inc()");


        // Используем CALL для вызова increment() в контракте Counter
        (bool success, bytes memory returnData) = counterAddress.call(data);

        // Логируем результат вызова
        emit CallResult(success, returnData);
    }


    // Функция для вызова метода get() контракта Counter через CALL
    function callGet(address _counterAddress) public returns (uint256) {
        bytes memory data = abi.encodeWithSignature("get()");

        (bool success, bytes memory returnData) = _counterAddress.staticcall(data);

        require(success, "CALL failed");

        uint256 counter_value = abi.decode(returnData, (uint256));

        emit LogCounterValue(counter_value);

        return counter_value;
    }

        // Функция для вызова метода increment() контракта Counter через CALL
    function callIncWithSenderLog(address counterAddress) public {
        bytes memory data = abi.encodeWithSignature("incWithSenderAddr()");

        // Используем CALL для вызова incWithSenderAddr() в контракте CounterWithLogSender
        (bool success, bytes memory returnData) = counterAddress.call(data);

        address  senderInCounter = abi.decode(returnData, (address));

        emit LogSenderInCaller(msg.sender);
        emit LogSenderInCounter(senderInCounter);

        // Логируем результат вызова
        emit CallResult(success, returnData);
    }

        // Функция для вызова метода increment() контракта Counter через CALL
    function callIncWithSendValue(address counterAddress) public payable{
        bytes memory data = abi.encodeWithSignature("receiveAndIncrement()");

        // Используем CALL для вызова incWithSenderAddr() в контракте CounterWithLogSender
        (bool success, bytes memory returnData) = counterAddress.call{value: msg.value}(data);

        // Логируем результат вызова
        emit CallResult(success, returnData);
    }
}