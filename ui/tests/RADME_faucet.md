# Neon Faucet + MetaMask Integration Tests

This project provides UI tests for verifying interactions between the [Neon Faucet](https://neonfaucet.org/) and MetaMask using Playwright and Pytest.

## Getting Started

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Prepare Chrome Extension and User Data
Place the MetaMask extension archive at:
```
ui/extensions/data/metamask.extension.tar.gz
```
Place the user data archive (with wallets configured) at:
```
ui/extensions/data/user_data.tar.gz
```

### Set Chrome Extension Password
Export the MetaMask password to an environment variable:
```bash
export CHROME_EXT_PASSWORD=1234Neon5678
```

### Run Tests
```bash
pytest ui/tests/test_faucet.py --headed
```

---

## Fixtures

### `context`
Creates a custom browser context with the MetaMask extension preloaded.
Returns a Playwright `BrowserContext` object.

### `metamask_page`
Initializes and authenticates the MetaMask extension page.
- Navigates to the MetaMask extension's home page
- Logs in with the provided password
- Closes pop-ups, changes the network, and verifies balance loading
Returns a `MetaMaskAccountsPage` instance.

### `neon_faucet_page`
Opens the faucet web page and returns a `NeonTestAirdropsPage` instance.

---

## Tests

### `TestFaucet.test_click_help_button`
- Navigates to the faucet URL
- Clicks the "Help" link
- Verifies the new tab opens with the correct documentation URL

### `TestMetaMaskPipeLIne.test_get_tokens_from_faucet`
- Connects the MetaMask wallet to the faucet
- Sends an airdrop of a specified token
- Verifies the token balance increases by the expected amount
- Ensures the next airdrop is re-enabled

---

## MetaMask Page Objects

### `MetaMaskLoginPage.login(password: str) -> MetaMaskPopoverNewsPage`
Fills in the password and logs into the MetaMask wallet.

### `MetaMaskPopoverNewsPage.close() -> MetaMaskAccountsPage`
Closes the news popover and returns the main accounts page.

### `MetaMaskAccountsPage`
- Properties:
  - `current_network`: currently selected network name
  - `active_account`: currently active account
  - `active_account_address`: copies and returns the wallet address
  - `neon_balance`, `usdt_balance`, etc.: balances of corresponding tokens
- Methods:
  - `get_balance(token: Token)`: returns token balance
  - `change_network(network: str)`: selects a network
  - `change_account(account: str)`: switches the account
  - `switch_assets()`, `switch_activity()`: toggles asset/activity view
  - `check_funds_protection()`: closes the "Protect your funds" dialog

---

## Faucet Page Object

### `NeonTestAirdropsPage`
- Methods:
  - `connect_wallet(timeout: int = 300)`: connects MetaMask to the faucet
  - `send_tokens(token: str, amount: int)`: sends tokens via faucet UI
  - `help_button_click()`: opens documentation in new tab
- Property:
  - `is_airdrop_enabled`: returns `True` if airdrop button is active

