import json
import pathlib
import random

import pytest
from _pytest.config import Config

from integration.tests.basic.helpers.basic import BaseMixin
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


def load_parametrized_data():
    result = {"argnames": "address,input_data,expected", "argvalues": [], "ids": []}

    for precompile_name in PRECOMPILED_FIXTURES:
        for f in PRECOMPILED_FIXTURES[precompile_name]["files"]:
            filepath = pathlib.Path(__file__).parent / "precompiled" / f
            with open(filepath, "r") as datafp:
                data = json.load(datafp)
            for record in data:
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


class TestPrecompiledContracts(BaseMixin):
    @pytest.mark.parametrize(**parametrized_data)
    def test_call_direct(
        self, web3_client: NeonChainWeb3Client, address, input_data, expected
    ):
        result = web3_client._web3.eth.call(
            {"to": address, "value": 0, "data": input_data}
        )
        assert result.hex()[2:] == expected

    @pytest.mark.parametrize(**parametrized_data)
    def test_call_via_contract(
        self,
        web3_client: NeonChainWeb3Client,
        precompiled_contract,
        address,
        input_data,
        expected,
    ):
        contract = precompiled_contract
        input_data = b"" if input_data == "" else input_data
        result = contract.functions.call_precompiled(address, input_data).call()

        assert result.hex() == expected

    @pytest.mark.parametrize(**parametrized_data)
    def test_staticcall_via_contract(
        self,
        web3_client: NeonChainWeb3Client,
        precompiled_contract,
        address,
        input_data,
        expected,
    ):
        contract = precompiled_contract
        input_data = b"" if input_data == "" else input_data
        result = contract.functions.staticcall_precompiled(address, input_data).call()

        assert result.hex() == expected

    @pytest.mark.parametrize(**parametrized_data)
    def test_delegatecall_via_contract(
        self,
        web3_client: NeonChainWeb3Client,
        precompiled_contract,
        address,
        input_data,
        expected,
    ):
        contract = precompiled_contract
        input_data = b"" if input_data == "" else input_data
        result = contract.functions.delegatecall_precompiled(address, input_data).call()

        assert result.hex() == expected

    @pytest.mark.xdist_group("precompiled_contract_balance")
    @pytest.mark.parametrize(**parametrized_data)
    def test_call_via_send_trx(
        self,
        web3_client: NeonChainWeb3Client,
        address,
        input_data,
        expected,
        request,
        pytestconfig,
    ):
        if request.node.callspec.id == "blake2f-vector 8":
            pytest.skip("NDEV-1961")
        if (
            pytestconfig.getoption("--network") == "devnet"
            and address == "0x0000000000000000000000000000000000000005"
        ):
            pytest.skip("Doesn't work in devnet/mainnet")

        amount = random.choice([0, 10])
        balance_before = self.get_balance_from_wei(address)

        instruction_tx = self.create_contract_call_tx_object(amount=amount)
        instruction_tx["data"] = input_data
        instruction_tx["chainId"] = self.web3_client.eth.chain_id
        instruction_tx["to"] = address
        instruction_tx["from"] = self.sender_account.address
        if request.node.callspec.id not in [
            "modexp-nagydani-5-square0",
            "modexp-nagydani-5-square1",
            "modexp-nagydani-5-qube0",
            "modexp-nagydani-5-qube1",
            "modexp-nagydani-5-pow0x100010",
            "modexp-nagydani-5-pow0x100011",
        ]:
            receipt = self.web3_client.send_transaction(
                self.sender_account, instruction_tx
            )
            assert receipt["status"] == 1
            if pytestconfig.getoption("--network") not in ["devnet", "night-stand"]:
                assert self.get_balance_from_wei(address) - balance_before == amount
        else:
            # solana limits
            try:
                resp = self.web3_client.send_transaction(
                    self.sender_account, instruction_tx
                )
                assert resp["status"] == 0
            except ValueError as exc:
                assert "InvalidLength" in exc.args[0]["message"]

    @pytest.mark.xdist_group("precompiled_contract_balance")
    @pytest.mark.parametrize("contract", PRECOMPILED_FIXTURES)
    def test_send_neon_without_data(self, contract, pytestconfig):
        address = PRECOMPILED_FIXTURES[contract]["address"]
        balance_before = self.get_balance_from_wei(address)
        amount = random.randint(1, 10)
        instruction_tx = self.create_tx_object(
            self.sender_account.address, address, amount=amount
        )
        receipt = self.web3_client.send_transaction(self.sender_account, instruction_tx)

        assert receipt["status"] == 1
        pytestconfig.getoption("--network")
        if pytestconfig.getoption("--network") not in ["devnet", "night-stand"]:
            assert self.get_balance_from_wei(address) - balance_before == amount
