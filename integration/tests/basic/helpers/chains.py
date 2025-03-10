import web3


def make_nonce_the_biggest_for_chain(account, client, rest_clients):
    # to avoid error "EVM Error. Attempt to deploy to existing account 0x..."
    clients = [c for c in rest_clients if c]
    new_account = client.create_account()
    while client.get_nonce(account.address) < max([c.get_nonce(account.address) for c in clients]):
        transaction = client.make_raw_tx(
            account, new_account, estimate_gas=True, amount=web3.Web3.to_wei(0.001, "ether")
        )
        client.send_transaction(account, transaction, timeout=180)
