# Useful tips


## How to get NEON operator reward address

To get the NEON Operator reward address from Solana Private, we need to use:
```python
import os
import json
from solana.account import Account
from common_neon.address import EthereumAddress

keys = []
for f in os.listdir("operator-keypairs"):
    with open(f"operator-keypairs/{f}", "r") as key:
        a = Account(json.load(key)[:32])
        keys.append(str(EthereumAddress.from_private_key(a.secret_key())))
```


## How to get NEON address for Chainlink feed

To get a NEON address for Oracles Solana feeds:

```python
print(f'0x{binascii.hexlify(base58.b58decode(solana_address)).decode()}')
```

