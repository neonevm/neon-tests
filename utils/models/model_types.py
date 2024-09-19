from pydantic.functional_validators import AfterValidator
from typing_extensions import Annotated

import utils.models.model_type_validators as mtv


HexString = Annotated[str, AfterValidator(mtv.validate_hex_string)]
JsonRPCString = Annotated[str, AfterValidator(mtv.validate_jsonrpc)]
IdField = Annotated[int, AfterValidator(mtv.validate_id)]
ErrorCodeField = Annotated[int, AfterValidator(mtv.validate_error_code)]
GasPriceString = Annotated[str, AfterValidator(mtv.validate_hex_string), AfterValidator(mtv.validate_gas_price)]
BalanceString = Annotated[str, AfterValidator(mtv.validate_hex_string), AfterValidator(mtv.validate_balance)]
NonZeroBytesString = Annotated[
    str, AfterValidator(mtv.validate_hex_string), AfterValidator(mtv.validate_non_zero_bytes)
]
ZeroBytesString = Annotated[str, AfterValidator(mtv.validate_hex_string), AfterValidator(mtv.validate_zero_bytes)]
NeonVersionString = Annotated[str, AfterValidator(mtv.validate_neon_version_string)]
NetVersionString = Annotated[str, AfterValidator(mtv.validate_net_version_string)]
StorageString = Annotated[str, AfterValidator(mtv.validate_hex_string), AfterValidator(mtv.validate_storage_string)]
FalseOnly = Annotated[bool, AfterValidator(mtv.validate_is_false)]
NotSupportedMethodString = Annotated[str, AfterValidator(mtv.validate_not_supported_method_string)]
EstimateGasPriceString = Annotated[
    str, AfterValidator(mtv.validate_hex_string), AfterValidator(mtv.validate_estimate_gas_price)
]
RequiredParamsString = Annotated[str, AfterValidator(mtv.validate_required_params_error)]
