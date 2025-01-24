pragma solidity ^0.8.10;

contract Counter {
    uint public count = 0;
    uint256 public totalReceived;
    event LogUint(uint value);

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

    function moreInstructionWithLogs(uint x, uint y) public {
        uint z = x;
        emit LogUint(z);
        while (x < y) {
            z++;
            x = z;
            emit LogUint(z);
        }

        if (y - z == 1) {
            z ++;
            emit LogUint(z);
        }
    }

    function bigString(string memory text) public {
        bytes memory _baseBytes = bytes(text);
    }

    // Функция для получения ETH и увеличения счетчика
    function receiveEthAndIncrement() public payable {
        // Обновляем общее количество полученных ETH
        totalReceived += msg.value;

        // Увеличиваем счетчик
        count += 1;
    }
}


contract CounterWithMap {

mapping(address => uint256) map;

    function inc() public {
        map[msg.sender] += 1;
    }

    function get() public view returns (uint256) {
        return map[msg.sender];
    }
}

contract CounterWithLogging{
    uint256 public count;
    uint256 public totalReceived;

    event LogTotalReceived(uint256 totalReceived);

    // Function to increment count by 1
    function incWithSenderAddr() public returns(address){
        count += 1;
        return msg.sender;
    }

    function receiveAndIncrement() public payable {
        totalReceived += msg.value;
        count += 1;
    }

    function getTotalReceived() public  returns(uint256) {
        emit LogTotalReceived(totalReceived);
        return totalReceived;
    }
}