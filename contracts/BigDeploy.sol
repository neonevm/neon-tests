pragma solidity ^0.8.10;


contract Contract2 {
    string public data;
    uint256 public order;

    constructor(string memory mydata, uint256 count) {
        order = count;
        data = mydata;
    }
}


contract Contract1 {
    string data = "Ke0drJO0r3ExN5kUXJSgMBU0EVRjB1wpVUEXX65eVQnqTcXtUF0k8IhYR04Pl8pMAL2z98ZHwvqaNb8pMmj5lAbSKNFXVdqPn5hmbHgqSuvdUTiXTQmlC6SX26DXxohxLUUuSLM0CbyjaWUnX08ub7q772rAB2m5w3mTypxPKtBt718baynBh0GDh2zuLbCga7oBIDNjskEYi4aAfpb5neMZR2WCpj7bm9o9y4NzSehAnn7mCOeEc2rW9ZIpjFcZDTKFtJqbHH5XJGKp9y6R5udpDkdVZUw4jT4gfkh5XZhIYMC8HyJbYlxtlTLoFpMjYacNX1ixrsEdsD6XirgYkD9vmUL45w1u7gMtOlfB63uevm3VI2ndCVt0tkMluL0XmRw1eT7fw2PhpnL9RbXUiItATU8UrFovsBunmfk7447TVpiUwT4KvFIZ2eknlP7GMRoxScI8Yfl2wgJ4eyFDkCdJk89228YSKnYUPDd60YEzOZcNxuTdFsB7NVulqeeMTUFP8uknnUbVEw3r8zs1pZUS0JfL45DD7S3YD94qhR5OMr6v6cYizQcAdiUDdj7iQLKuZKmgmPW3Bh638ZbBFpgDpzIrcNEb5Hoaipztr1oatoTO9srEfgXCXM3q1WUuDj8c0WzULGkr5MJHFfKE0D6CtPWgobkWvMDWrjOpBkAQXy8JlYhVaEvICTYMxYsTmtWTFuVOYuJ0dFNxEtwotcTLEeR5t30jHnu7b4KtSot5tCQzzcK7T35NBX2gmgI5wh56DbyCp1PZhODGRDQWkmgbGfZ0SjqFWSnulI4LBo77AoIjZuCSx25a2kGu4W5ltpk0QLAZJPHYGtCkvLwmu81IdqRE01c3NrBbzqQFQ17azj9me0ruKdPZvXpRMo7JPpYaRbzqUrT4DFMlgU11pGPoBB2POaOA34W6wYbn6r47fkffhcaJ4YQVyA2TGTTWAwEyoL1IQEyjGWHH9zZb8JHc8VNMTbXbznpAGGSLnBz9creI4eDB3MaQ5L6Htn8QO2DNFAqufKgODky9guDSEMEd4qmQzNYpqe52m0lzCsBVYizA5orMj6wL8iH9sTNUJbWfOnPA3jwZ1j52OC2VmKJQ06iDUcPQJaISHWTMttNKJuW3tPJVrpjX4y35Rsq7YbKwvE6O1c3eLvayNxfTybZLY9nWPYb0xmyiuWFrdKl1CFYU";
    Contract2[] public contracts;

    // Function to get the current count
    constructor() {
        for (uint256 i = 0; i < 10; i++) {
            string memory bigdata = data;
//            for (uint256 j = 0; j < 2; j++) {
//                bigdata = string.concat(bigdata, data);
//            }
            contracts.push(new Contract2(bigdata, i));
        }
    }
}