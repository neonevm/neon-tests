pragma solidity ^0.8.12;

contract A {
    event EventA1(string text);

    function method1(address contractB, address contractC) public {
        emit EventA1("contractA method1");
        address(contractB).call(abi.encodeWithSignature("method1(address)", contractC));
        address(contractB).call(abi.encodeWithSignature("method2(address)", contractC));
    }
}

contract B {
    event EventB1(string text);
    event EventB2(string text);

    function method1(address contractC) public {
        emit EventB1("contractB method1");
        address(contractC).call(abi.encodeWithSignature("method1()"));
    }
    function method2(address contractC) public {
        emit EventB2("contractB method2");
        address(contractC).call(abi.encodeWithSignature("method2()"));
        revert();
    }

}

contract C {
    event EventC1(string text);
    event EventC2(string text);

    function method1() public {
        emit EventC1("ContractC method1");
        revert();
    }
    function method2() public {
        emit EventC2("ContractC method2");
    }
}
