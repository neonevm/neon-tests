import eth from 'k6/x/ethereum';
import {erc20Address, networkId, proxyUrl, tracerUrl} from './consts.js';
import {check} from 'k6';

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

export async function sendCallContractTransaction({
    ethClient,
    contractAddress,
    contractAbi,
    senderAddress,
    functionName,
    functionArgs = [],
    receiptErrorCounter,
    contractErrorCounter,
    requestTimeTrend,
    requestCounter,
    prometheusLabels = {},
    gasLimitMultiplier = 1,
}) {
    const startTime = new Date();
    const labels = Object.assign({ function: functionName }, prometheusLabels);

    try {
        const contract = ethClient.newContract(contractAddress, contractAbi);
        const input = contract.fillInput(contractAbi, functionName, ...functionArgs);

        const transaction = {
            from: senderAddress,
            to: contractAddress,
            value: 0,
            input: input,
        };

        const gasEstimate = ethClient.estimateGas(transaction)
        const gasLimit = gasEstimate * gasLimitMultiplier
        transaction.gas = gasLimit

        const timeout = 120;
        const txHash = ethClient.sendRawTransaction(transaction);
        const receipt = ethClient.waitForTransactionReceipt(txHash, timeout);
        let checkResult = false;

        checkResult = check(receipt, {
            'receipt has been received': (r) => !!r,
            'receipt status is 1': (r) => r && r.status === 1,
        });

        if (!checkResult) {
            console.log('Error in tx:', txHash, "receipt:", receipt ? JSON.stringify(receipt) : receipt);
            receiptErrorCounter.add(
                1,
                Object.assign(
                    { error: receipt ? `receipt status: ${receipt.status}` : `no receipt after ${timeout} seconds`},
                    labels,
                ),
            );
        }

    } catch (e) {
        console.log('Block.sol contract error:', e);
        contractErrorCounter.add(1, Object.assign({ error: "failed to send transaction"}, labels));
    } finally {
        requestTimeTrend.add(new Date() - startTime, labels);
        requestCounter.add(1, labels);
    }
}

