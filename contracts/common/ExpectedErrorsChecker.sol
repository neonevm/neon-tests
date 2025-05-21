// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;
contract A {
    int a = 0;
    uint public M;
    string[10] text_array;

    function method1() public {
        string memory text = "sdsd";

        for (uint i; i < 10; i++) {
            a += 1;
            text = string.concat(text, text);
        }

        for (uint i = 0; i < 5; i++) {
            text_array[i] = text;
        }
    }

    function iterativeWithCancel(uint N) public {
        for (uint i = 1; i <= N; i++) {
            if (i == N / 2) {
                method1();
            }
        }
    }

    function riskyDivision(uint x, uint y) public pure returns (uint) {
        return x / y;
    }

    function runLoopWithZeroDivision() public {
        for (uint i = 0; i < 300; i++) {
            if (i == 250) {
                uint result = riskyDivision(i, 0);
                M += result;
            } else {
                M += 1;
            }
        }
    }
}