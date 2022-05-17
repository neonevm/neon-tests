MSG_EXCEPTIONS = [
    "Failed to fetch",
    "SharedArrayBuffer will require cross-origin isolation",
    "Download the React DevTools for a better development experience:",
    "Slow network is detected.",
    "Synchronous XMLHttpRequest on the main thread is deprecated because of its detrimental effects to the end user's experience.",
    "Failed to load resource: the server responded with a status of 405",
    "XTemplate evaluation exception",
    "failed: WebSocket is closed before the connection is established.",  # Segment
    '"billing" is unknown Breadcrumb ID',  # https://scalr-labs.atlassian.net/browse/SCALRCORE-20117
    "Operation 'list-resource-tiers' doesn't accept query parameters.",  # https://scalr-labs.atlassian.net/browse/SCALRCORE-20732
]


class BrowserErrors:
    def __init__(self):
        self.errors = []

    def append(self, err):
        self.errors.append(err)

    def assert_errors(self):
        msgs = []
        for err in self.errors:
            excludes = False
            for exc in MSG_EXCEPTIONS:
                if exc in err.text:
                    excludes = True
                    break
            if err.type not in ("log", "info", "verbose") and not excludes:
                msgs.append(f"{err.type}:{err.text}")
        assert not msgs, f"Browser has errors: \n{msgs}"
