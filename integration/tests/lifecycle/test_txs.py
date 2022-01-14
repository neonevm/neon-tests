import pytest


class TestAccountOperations:
    def test_create_account_and_get_balance(self):
        pass

    @pytest.mark("token", ["neon", "spl", "erc20"])
    def test_get_balances(self, token):
        pass

    @pytest.mark("token", ["neon", "spl", "erc20"])
    def test_send_tokens(self, token):
        pass

    @pytest.mark("token,count", [
        ("neon", "100000"),
        ("neon", "0"),
        ("neon", "-10"),
        ("neon", "abc"),
        ("spl", "100000"),
        ("spl", "0"),
        ("spl", "-10"),
        ("spl", "abc"),
        ("erc20", "100000"),
        ("erc20", "0"),
        ("erc20", "-10"),
        ("erc20", "abc"),
    ])
    def test_send_invalid_tokens(self, token, count):
        pass
