
contract A {
    int a = 0;
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
}

