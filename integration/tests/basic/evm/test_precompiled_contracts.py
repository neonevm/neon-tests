import json
import allure
import pathlib
import random

import pytest

from integration.tests.basic.helpers.rpc_checks import check_trx_is_success
from utils.accounts import EthAccounts
from utils.web3client import NeonChainWeb3Client

PRECOMPILED_FIXTURES = {
    "modexp": {
        "address": "0x0000000000000000000000000000000000000005",
        "files": ["modexp.json", "modexp_eip2565.json"],
    },
    "ecAdd": {
        "address": "0x0000000000000000000000000000000000000006",
        "files": ["bn256Add.json"],
    },
    "ecMul": {
        "address": "0x0000000000000000000000000000000000000007",
        "files": ["bn256ScalarMul.json"],
    },
    "ecPairing": {
        "address": "0x0000000000000000000000000000000000000008",
        "files": ["bn256Pairing.json"],
    },
    "sha2_256": {
        "address": "0x0000000000000000000000000000000000000002",
        "files": ["sha2_256.json"],
    },
    "ecRecover": {
        "address": "0x0000000000000000000000000000000000000001",
        "files": ["ecRecover.json"],
    },
    "ripemd160": {
        "address": "0x0000000000000000000000000000000000000003",
        "files": ["ripemd160.json"],
    },
    "identify": {
        "address": "0x0000000000000000000000000000000000000004",
        "files": ["identify.json"],
    },
    "blake2f": {
        "address": "0x0000000000000000000000000000000000000009",
        "files": ["blake2f.json"],
    },
}

NEON_PRECOMPILED = [
    "0xFF00000000000000000000000000000000000002",
    "0xFF00000000000000000000000000000000000003",
    "0xFF00000000000000000000000000000000000004",
    "0xFF00000000000000000000000000000000000005",
    "0xFF00000000000000000000000000000000000006",
]


SKIPPED_MODEXP_TESTS = [
    "nagydani-2-square",
    "nagydani-3-square",
    "nagydani-4-square",
    "nagydani-2-qube",
    "nagydani-3-qube",
    "nagydani-4-qube",
    "nagydani-2-pow0x10001",
    "nagydani-3-pow0x10001",
    "nagydani-4-pow0x10001",
]  # evm doesn't support mod exp operation with big values
SKIPPED_BLACK2F_TESTS = ["vector 8"]  # NDEV-1961


def load_parametrized_data():
    result = {"argnames": "address,input_data,expected", "argvalues": [], "ids": []}

    for precompile_name in PRECOMPILED_FIXTURES:
        for f in PRECOMPILED_FIXTURES[precompile_name]["files"]:
            filepath = pathlib.Path(__file__).parent / "precompiled" / f
            with open(filepath, "r") as datafp:
                data = json.load(datafp)
            for record in data:
                if record["Name"] not in SKIPPED_MODEXP_TESTS + SKIPPED_BLACK2F_TESTS:
                    result["argvalues"].append(
                        (
                            PRECOMPILED_FIXTURES[precompile_name]["address"],
                            record["Input"],
                            record["Expected"],
                        )
                    )
                    result["ids"].append(f'{precompile_name}-{record["Name"]}')

    return result


parametrized_data = load_parametrized_data()


@allure.feature("EVM tests")
@allure.story("Verify precompiled ethereum contracts")
@pytest.mark.usefixtures("accounts", "web3_client")
class TestPrecompiledContracts:
    web3_client: NeonChainWeb3Client
    accounts: EthAccounts

    @pytest.mark.parametrize(**parametrized_data)
    def test_call_direct(self, address, input_data, expected, pytestconfig):
        if pytestconfig.getoption("--network") == "devnet" and address == "0x0000000000000000000000000000000000000005":
            pytest.skip("Doesn't work in devnet/mainnet")
        result = self.web3_client._web3.eth.call({"to": address, "value": 0, "data": input_data})
        assert result.hex() == expected

    @pytest.mark.parametrize(**parametrized_data)
    def test_call_via_contract(self, precompiled_contract, address, input_data, expected, pytestconfig):
        if pytestconfig.getoption("--network") == "devnet" and address == "0x0000000000000000000000000000000000000005":
            pytest.skip("Doesn't work in devnet/mainnet")
        contract = precompiled_contract
        input_data = b"" if input_data == "" else input_data
        result = contract.functions.call_precompiled(address, input_data).call()

        assert result.hex() == expected

    @pytest.mark.parametrize(**parametrized_data)
    def test_staticcall_via_contract(self, precompiled_contract, address, input_data, expected, pytestconfig):
        if pytestconfig.getoption("--network") == "devnet" and address == "0x0000000000000000000000000000000000000005":
            pytest.skip("Doesn't work in devnet/mainnet")
        contract = precompiled_contract
        input_data = b"" if input_data == "" else input_data
        result = contract.functions.staticcall_precompiled(address, input_data).call()

        assert result.hex() == expected

    @pytest.mark.parametrize(**parametrized_data)
    def test_delegatecall_via_contract(self, precompiled_contract, address, input_data, expected, pytestconfig):
        if pytestconfig.getoption("--network") == "devnet" and address == "0x0000000000000000000000000000000000000005":
            pytest.skip("Doesn't work in devnet/mainnet")
        contract = precompiled_contract
        input_data = b"" if input_data == "" else input_data
        result = contract.functions.delegatecall_precompiled(address, input_data).call()

        assert result.hex() == expected

    @pytest.mark.xdist_group("precompiled_contract_balance")
    @pytest.mark.parametrize(**parametrized_data)
    def test_call_via_send_trx(
        self, web3_client: NeonChainWeb3Client, address, input_data, request, pytestconfig, expected, evm_loader
    ):
        sender_account = self.accounts[0]
        if address == "0x0000000000000000000000000000000000000007":
            amount = random.choice([1, 10])
        else:
            amount = 0
        balance_before = self.web3_client.get_balance(address)

        instruction_tx = self.web3_client.make_raw_tx(
            sender_account, address, data=input_data, amount=amount, estimate_gas=True
        )
        if "modexp-nagydani-5" not in request.node.callspec.id:
            receipt = self.web3_client.send_transaction(sender_account, instruction_tx)
            check_trx_is_success(self.web3_client, evm_loader, receipt["transactionHash"].hex())

            if pytestconfig.getoption("--network") not in ["devnet"]:
                assert self.web3_client.get_balance(address) - balance_before == amount
        else:
            # solana limits
            try:
                resp = self.web3_client.send_transaction(sender_account, instruction_tx)
                assert resp["status"] == 0
            except ValueError as exc:
                assert "InvalidLength" in exc.args[0]["message"]

    @pytest.mark.xdist_group("precompiled_contract_balance")
    def test_send_neon_without_data(self, pytestconfig, evm_loader):
        address = "0x0000000000000000000000000000000000000006"
        sender_account = self.accounts[0]
        balance_before = self.web3_client.get_balance(address)
        amount = random.randint(1, 10)
        instruction_tx = self.web3_client.make_raw_tx(sender_account.address, address, amount=amount, estimate_gas=True)
        receipt = self.web3_client.send_transaction(sender_account, instruction_tx)

        check_trx_is_success(self.web3_client, evm_loader, receipt["transactionHash"].hex())
        pytestconfig.getoption("--network")
        if pytestconfig.getoption("--network") not in ["devnet"]:
            assert self.web3_client.get_balance(address) - balance_before == amount

    @pytest.mark.parametrize("contract", PRECOMPILED_FIXTURES)
    def test_eth_get_code_ethereum_precompiled(self, json_rpc_client, contract):
        address = PRECOMPILED_FIXTURES[contract]["address"]
        code = json_rpc_client.get_contract_code(address)
        assert code == "0x"

    @pytest.mark.parametrize("address", NEON_PRECOMPILED)
    def test_eth_get_code_neon_precompiled(self, json_rpc_client, address):
        response = json_rpc_client.send_rpc(
            "eth_getCode",
            params=[address, "latest"],
        )
        assert response["result"] == "0xfe"
