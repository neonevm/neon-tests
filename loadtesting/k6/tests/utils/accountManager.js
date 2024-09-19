import wallet from 'k6/x/ethereum/wallet';
import http from 'k6/http';
import { check } from 'k6';

const faucetUrl = __ENV.FAUCET_URL;
const amount = 100;

export function createAccount() {
    var accountKey = wallet.generateKey();
    return {
        private_key: accountKey.private_key,
        address: accountKey.address,
    };
}

export function fundAccountWithNeon(address, amount) {
    const payload = JSON.stringify({
        amount: amount,
        wallet: address,
    });

    const params = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const response = http.post(faucetUrl, payload, params);
    check(response, {
        'status is 200': (r) => r.status === 200,
    });
}
