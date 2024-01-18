import random

MAX_TOKENS_AMOUNT = 1000000000000000


def check_erc20_mint_function(
    web3_client,
    contract,
    account,
):
    balance_before = contract.functions.balanceOf(account.address).call()
    amount = random.randint(1, MAX_TOKENS_AMOUNT)
    tx = web3_client.make_raw_tx(account.address, gas=0)
    del tx["gas"]
    instruction_tx = contract.functions.mint(account.address, amount).build_transaction(tx)
    web3_client.send_transaction(account, instruction_tx)
    balance_after = contract.functions.balanceOf(account.address).call()
    assert balance_after == balance_before + amount


def check_erc20_transfer_function(web3_client, contract, sender, receiver):
    balance_acc1_before = contract.functions.balanceOf(sender.address).call()
    balance_acc2_before = contract.functions.balanceOf(receiver.address).call()
    total_before = contract.functions.totalSupply().call()
    amount = random.randint(1, 100)
    tx = web3_client.make_raw_tx(sender.address, gas=0)
    del tx["gas"]
    contract.functions.mint(sender.address, amount).build_transaction(tx)

    tx = web3_client.make_raw_tx(sender.address, gas=0)
    del tx["gas"]
    instruction_tx = contract.functions.transfer(receiver.address, amount).build_transaction(tx)
    web3_client.send_transaction(sender, instruction_tx)
    balance_acc1_after = contract.functions.balanceOf(sender.address).call()
    balance_acc2_after = contract.functions.balanceOf(receiver.address).call()
    total_after = contract.functions.totalSupply().call()
    assert balance_acc1_after == balance_acc1_before - amount
    assert balance_acc2_after == balance_acc2_before + amount
    assert total_before == total_after
