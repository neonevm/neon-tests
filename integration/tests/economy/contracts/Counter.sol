pragma solidity ^0.8.10;

contract Counter {
    uint public count = 0;

    // Function to get the current count
    function get() public view returns (uint) {
        return count;
    }

    // Function to increment count by 1
    function inc() public {
        count += 1;
    }

    // Function to decrement count by 1
    function dec() public {
        count -= 1;
    }

    function moreInstruction(uint x, uint y) public {
        uint z = x;
        while (x < y) {
            z++;
            x = z;
        }

        if (y - z == 1) {
            z ++;
        }
    }

    function bigString(string memory text) public {
        bytes memory _baseBytes = bytes(text);
    }
}