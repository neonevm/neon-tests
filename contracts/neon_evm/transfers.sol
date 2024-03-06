contract transfers {

    function transferNeon(uint256 amount, address[] memory recipients) public payable {
        require(address(this).balance >= amount * recipients.length, "contract balance less then needed");
        for (uint256 i = 0; i < recipients.length; i++) {
            (bool success, ) = recipients[i].call{value: amount}("");
            require(success, "Payment failed.");
        }
    }
}