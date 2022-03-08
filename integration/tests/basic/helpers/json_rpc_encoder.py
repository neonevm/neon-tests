from json import JSONEncoder


class JsonRpcEncoder(JSONEncoder):
    def default(self, o: object) -> str:
        return o.__dict__