import wallet from 'k6/x/ethereum/wallet';
import { fundAccountWithNeon, createAccount } from './utils/accountManager.js';
import { ethClient, sendNeon } from './utils/ethClient.js';
import { Trend, Counter } from 'k6/metrics'


const testConfig = JSON.parse(open('../env/options.json'));
export const options = testConfig;

const sendNeonRequests = new Counter('send_neon_requests');
const nonceRequests = new Counter('nonce_requests');
const blockNumberRequests = new Counter('block_number_requests');
const gasPriceRequests = new Counter('gas_price_requests');

const sendNeonErrorCounter = new Counter('send_neon_errors');
const blockNumberErrorCounter = new Counter('block_number_errors');
const nonceErrorCounter = new Counter('nonce_errors');
const gasPriceErrorCounter = new Counter('gas_price_errors');

const sendNeonRequestTime = new Trend('send_neon_request_time', true);
const blockNumberRequestTime = new Trend('block_number_request_time', true);
const nonceRequestTime = new Trend('nonce_request_time', true);
const gasPriceRequestTime = new Trend('gas_price_request_time', true);

//TO DO: create rpc client for a session not for each user
const client = ethClient();

//TO DO: before test actions
export function setup() {
    console.log('Setup');
}

export default function sendNeonTest(data) {
    let nonceCounter = 0;
    let gasPriceCounter = 0;
    let receipt;

    let account = createAccount();
    const accountReceiver = createAccount();
    const accountSender = wallet.newWalletKeyFromPrivateKey(account.private_key);
    fundAccountWithNeon(accountSender.address, 20);

    let nonce;
    try {
        const startTime = new Date();
        nonce = client.getNonce(accountSender.address);
        const finishTime = new Date();
        nonceRequests.add(1);
        nonceRequestTime.add(finishTime - startTime);
    } catch (e) {
        console.log('Error: ' + e);
        nonceErrorCounter.add(1);
    }

    let gasPrice;
    try {
        const startTime = new Date();
        gasPrice = client.gasPrice();
        const finishTime = new Date();
        gasPriceRequests.add(1);
        gasPriceRequestTime.add(finishTime - startTime);
    } catch (e) {
        console.log('Error: ' + e);
        gasPriceErrorCounter.add(1);
    }


    const sendingNeonStartTime = new Date();

    try {
        const startTime = new Date();
        client.blockNumber();
        const finishTime = new Date();
        blockNumberRequests.add(1);
        blockNumberRequestTime.add(finishTime - startTime);
    } catch (e) {
        console.log('Error: ' + e);
        blockNumberErrorCounter.add(1);
    }

    try {
        const startTime = new Date();
        client.getNonce(accountSender.address);
        const finishTime = new Date();
        nonceRequests.add(1);
        nonceRequestTime.add(finishTime - startTime);
    } catch (e) {
        console.log('Error: ' + e);
        nonceErrorCounter.add(1);
    }

    try {
        const startTime = new Date();
        client.gasPrice();
        const finishTime = new Date();
        gasPriceRequests.add(1);
        gasPriceRequestTime.add(finishTime - startTime);
    } catch (e) {
        console.log('Error: ' + e);
        gasPriceErrorCounter.add(1);
    }

    const startTime = new Date();

    try {
        receipt, nonceCounter, gasPriceCounter = sendNeon(client, accountSender.address, accountReceiver.address, 0.01, 0, gasPrice, nonce);
        nonceRequests.add(nonceCounter);
        gasPriceRequests.add(gasPriceCounter);
    } catch (e) {
        console.log('Error: ' + e);
        sendNeonErrorCounter.add(1);
    }
    sendNeonRequestTime.add(new Date() - startTime);
    sendNeonRequests.add(1);
    nonce++;
}

//TO DO: after test actions
export function teardown(data) {
    console.log('Tearing down');
}