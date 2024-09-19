import inspect

import pytest
from _pytest.config import Config

from utils.tracer_client import TracerClient
from utils.storage_contract import StorageContract


@pytest.fixture(scope="session")
def tracer_json_rpc_client_session(pytestconfig: Config):
    return TracerClient(pytestconfig.environment.tracer_url)


@pytest.fixture(scope="class")
def tracer_api(tracer_json_rpc_client_session, request):
    if inspect.isclass(request.cls):
        request.cls.tracer_api = tracer_json_rpc_client_session
    yield tracer_json_rpc_client_session


@pytest.fixture(scope="class")
def storage_object(web3_client, storage_contract):
    return StorageContract(web3_client, storage_contract)