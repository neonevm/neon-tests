import pytest
from eth_account import Account
from integration.tests.basic.helpers.basic_helpers import BasicHelpers


class BaseTransfers(BasicHelpers):
    sender_account: Account
    recipient_account: Account

    @pytest.fixture
    def prepare_accounts(self):
        self.sender_account = self.create_account_with_balance()
        self.recipient_account = self.create_account_with_balance()
        yield
