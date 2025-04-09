import allure


@allure.step("Make nonce the biggest for chain to make it possible to deploy contract")
def make_nonce_the_biggest_for_chain(account, client, rest_clients):
    # to avoid error "EVM Error. Attempt to deploy to existing account 0x..."
    clients = [c for c in rest_clients if c]
    current_nonce = client.get_nonce(account.address)
    rest_nonces = [c.get_nonce(account.address) for c in clients]
    count = max(rest_nonces) - current_nonce
    while count > 0:
        transaction = client.make_raw_tx(account, account.address, estimate_gas=True, amount=1, nonce=current_nonce)
        client.send_transaction(account, transaction, timeout=180)
        current_nonce += 1
        count -= 1
