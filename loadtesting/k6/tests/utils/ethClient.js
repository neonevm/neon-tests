import eth from 'k6/x/ethereum';
import { proxyUrl, tracerUrl, networkId, erc20Address } from './consts.js';

export function ethClient(privateKey) {
    const client = new eth.Client({
        proxyUrl: proxyUrl,
        tracerUrl: tracerUrl,
        chainID: networkId,
        privateKey: privateKey,
    });
    return client;
}

export function sendNeon(client, from, to, amount) {
    return sendTokens(client, from, to, amount, null);
}

export function sendErc20ViaTransferFunction(client, abi, sender, receiverAddress, amount) {
    const erc20 = client.newContract(erc20Address, abi, sender.key)
    let input = erc20.fillInput(abi, "transfer", receiverAddress, amount);
    return sendTokens(client, sender.address, erc20Address, 0, input);
}

export function sendTokens(client, from, to, value, input) {
    let transaction = {
        "from": from,
        "to": to,
        "value": value
    };

    if (input != null) {
        transaction["input"] = input;
    }

    const txh = client.sendRawTransaction(transaction);
    return client.waitForTransactionReceipt(txh, 120);
}
