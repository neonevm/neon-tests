pragma solidity ^0.8.12;

contract EventCaller {
    mapping(address => mapping(uint256 => uint256)) public data;
    string text = "sdsd";
    string[10] text_array;

    event NonArgs();
    event AllTypes(address addr, uint256 u, string s, bytes32 b, bool bol);
    event IndexedArgs(address indexed who, uint256 indexed value);
    event NonIndexedArg(string hello);
    event UnnamedArg(string);
    event BigArgsCount(address indexed who, string indexed s1, string indexed s2, string s3, string s4, string s5, string s6, string s7, string s8, string s9);
    event Event1(string indexed text);
    event Event2(string indexed text1, string indexed text2);
    event Event3(string indexed text1, string indexed text2, string indexed text3);

    function callEvent1(string memory text) public {
        emit Event1(text);
    }

    function callEvent2(string memory text1, string memory text2) public {
        emit Event2(text1, text2);
    }

    function callEvent3(string memory text1, string memory text2, string memory text3) public {
        emit Event3(text1, text2, text3);
    }

    function nonArgs() public {
        emit NonArgs();
    }

    function allTypes(address a, uint256 i, string memory s, bytes32 b, bool bol) public {
        emit AllTypes(a, i, s, b, bol);
    }

    function indexedArgs() public payable {
        emit IndexedArgs(msg.sender, msg.value);
    }

    function nonIndexedArg(string memory text) public payable {
        emit NonIndexedArg(text);
    }

    function unnamedArg(string memory text) public payable {
        emit UnnamedArg(text);
    }

    function bigArgsCount(string memory text) public {
        emit BigArgsCount(msg.sender, text, text, text, text, text, text, text, text, text);
    }

    function emitThreeEvents() public {
        emit IndexedArgs(msg.sender, 2);
        emit NonIndexedArg("world");
        emit AllTypes(msg.sender, 1, "text", "b", true);


    }

    function updateStorageMap(uint resize) public {
        uint n = 0;
        while (n < resize){
            data[msg.sender][n] = uint256(n);
            emit NonIndexedArg("world");
            n = n + 1;
        }
    }

    function causeOutOfMemory() public {
        string memory memory_text = text;
        for (uint i; i < 10; i++) {
            memory_text = string.concat(memory_text, memory_text);
            emit NonIndexedArg(memory_text);
        }

        for (uint i; i < 5; i++) {
            text_array[i] = memory_text;
        }
    }

}

