import binascii
import re


def validate_hex_string(str_: str):
    assert str_.startswith("0x"), f'"{str_}" is not a hex string'
    str__ = str_.removeprefix("0x")

    if len(str__) % 2 != 0:
        str__ = "0" + str__

    binascii.unhexlify(str__)  # validate

    return str_


def validate_jsonrpc(str_: str):
    pattern = r"\d+\.\d+"
    assert re.match(pattern, str_), f'"{str_}" is not a jsonrpc string'
    return str_


def validate_id(id_: int):
    assert id_ >= 0, f'"{id_}" is not a valid id'
    return id_


def validate_error_code(error_code: int):
    assert error_code < 0, f'"{error_code}" is not a valid error id'
    return error_code


def validate_gas_price(gas_price: str):
    assert (
        int(gas_price, 16) > 0
    ), f"gas price {gas_price} should be greater 0, got {int(gas_price, 16)}"
    return gas_price


def validate_estimate_gas_price(gas_price: str):
    assert int(gas_price, 16) > 0, f"gas price {gas_price} should be greater 0, got {int(gas_price, 16)}"
    return gas_price


def validate_balance(balance: str):
    assert int(balance, 16) >= 0, f"balance {balance} should be greater or equal 0, got {int(balance, 16)}"
    return balance


def validate_non_zero_bytes(zero_bytes: str):
    assert zero_bytes.startswith("0x")
    assert len(zero_bytes[2:]) % 2 == 0
    if len(zero_bytes[2:]) > 0:
        assert any(c != "0" for c in zero_bytes[2:]), f"non-zero bytes should be present in {zero_bytes}"
    return zero_bytes


def validate_zero_bytes(zero_bytes: str):
    assert zero_bytes.startswith("0x")
    if len(zero_bytes[2:]) > 0:
        assert len(zero_bytes[2:]) % 2 == 0
        assert all(c == "0" for c in zero_bytes[2:])
    return zero_bytes


def validate_neon_version_string(version: str):
    pattern = r"Neon-EVM/v\d{1,3}\.\d{1,3}\.\d{1,3}\-.*"
    assert re.match(pattern, version), f'"{version}" is not a neon version string'
    return version


def validate_net_version_string(version: str):
    assert version.isdigit(), f"net_version must be integer, got {version}"
    return version


def validate_storage_string(storage: str):
    assert int(storage, 16) >= 0, f"storage {storage} should be greater or equal 0, got {int(storage, 16)}"
    return storage


def validate_is_false(is_false: bool):
    assert not is_false, f'"{is_false}" is not False'
    return is_false


def validate_not_supported_method_string(method: str):
    pattern = r"the method (eth|shh)_(\w+) does not exist/is not available"
    assert re.match(pattern, method), f'"{method}" is not a not supported method string'
    return method


def validate_required_params_error(error: str):
    pattern = r"The parameter '(.+)': Field required."
    assert re.match(pattern, error), f'"{error}" is not a required params error'
    return error
