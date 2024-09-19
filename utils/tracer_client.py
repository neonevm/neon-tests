from utils.apiclient import JsonRPCSession
from utils.helpers import wait_condition

class TracerClient:
    def __init__(self, url):
        self.url = url
        self.tracer_api = JsonRPCSession(url)
    
    def send_rpc_and_wait_response(self, method_name, params, req_type=None):
        wait_condition(
            lambda: self.tracer_api.send_rpc(method=method_name, params=params, req_type=req_type)["result"]
            is not None,
            timeout_sec=120,
        )

        return self.tracer_api.send_rpc(
            method=method_name, params=params
        )
    
    def send_rpc(self, method, params, req_type=None):
        return self.tracer_api.send_rpc(method=method, params=params, req_type=req_type)
