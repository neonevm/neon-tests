import pydantic
from solders.pubkey import Pubkey


class OperatorAccountsModel(pydantic.BaseModel):
    name: str
    accounts: list[str]

    @pydantic.field_validator("accounts", mode="before")
    def validate_account(cls, accounts):
        for account in accounts:
            try:
                Pubkey.from_string(account)
            except ValueError:
                raise ValueError(f"Invalid Solana account: {account}")
        return accounts
