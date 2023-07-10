pragma solidity ^0.8.12;

contract A {
    int a = 0;
    string text = "sdsd";

    function method1() public {
        for (uint i; i < 10; i++) {
            a += 1;
            text = string.concat(text, text);
        }
    }
}

