pragma solidity >=0.5.12;

contract calculator {
    uint public x = 20;
    uint public y = 20;

    function getSum() public view returns (uint256) {
        return x + y;
    }
}

contract calculatorCaller {
    calculator calc;

    constructor(address _calc) {
        calc = calculator(_calc);
    }

    function callCalculator() public view returns (uint sum) {
        sum = calc.getSum();
    }
}
