import json
import pathlib

import pytest

from integration.tests.basic.helpers.basic import BaseMixin
from utils.web3client import NeonWeb3Client


PRECOMPILED_FIXTURES = {

    # NOT IMPLEMENTED YET
    # "modexp": {
    #     "address": "0x0000000000000000000000000000000000000005",
    #     "files": ["modexp.json", "modexp_eip2565.json"],
    # },
    # "ecAdd": {
    #     "address": "0x0000000000000000000000000000000000000006",
    #     "files": ["bn256Add.json"],
    # },
    # "ecMul": {
    #     "address": "0x0000000000000000000000000000000000000007",
    #     "files": ["bn256ScalarMul.json"],
    # },
    # "ecPairing": {
    #     "address": "0x0000000000000000000000000000000000000008",
    #     "files": ["bn256Pairing.json"],
    # },

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


@pytest.mark.parametrize(**load_parametrized_data())
class TestPrecompiledContracts(BaseMixin):
    def test_call_direct(
        self, web3_client: NeonWeb3Client, address, input_data, expected
    ):
        result = web3_client._web3.eth.call(
            {
                "to": address,
                "value": 0,
                "data": input_data,
                "gas": 10000000,
            }
        )
        assert result.hex()[2:] == expected

    def test_call_via_contract(
        self,
        web3_client: NeonWeb3Client,
        precompiled_contract,
        address,
        input_data,
        expected,
    ):
        contract = precompiled_contract
        result = contract.functions.call_precompiled(address, input_data).call()

        assert result.hex() == expected
