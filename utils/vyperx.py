import subprocess
import sys

import requests
from pkg_resources import parse_version


def get_installable_vyper_versions():
    url = f"https://pypi.org/pypi/vyper/json"
    res = requests.get(url, timeout=5)
    data = res.json()
    versions = data['releases']
    return sorted(versions, key=parse_version, reverse=True)


def install(version):
    code = subprocess.check_call([sys.executable, "-m", "pip", "install", f'vyper=={version}'])
    if code != 0:
        raise RuntimeError(f"Failed to install vyper {version}")


def get_three_last_versions():
    versions = get_installable_vyper_versions()[:3]
    versions.sort()
    return versions
