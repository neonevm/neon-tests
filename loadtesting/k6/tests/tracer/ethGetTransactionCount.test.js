import { ethClient } from '../utils/ethClient.js';
import { standardScenarioOptions } from '../../options/options.js';
import { Trend, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';

import exec from 'k6/execution';
import { check } from 'k6';

const ethGetTransactionCountRequests = new Counter('eth_get_storage_at_requests');
const ethGetTransactionCountRequestErrorCounter = new Counter('eth_get_storage_at_request_errors');
const ethGetTransactionCountErrorCounter = new Counter('eth_get_storage_at_errors');
const ethGetTransactionCountRequestTime = new Trend('eth_get_storage_at_request_time', true);

export const options = standardScenarioOptions;

const historicalData = JSON.parse(open("../../data/transaction.json"));
let testData = {};
let i = 0;
for (const [key, _] of Object.entries(historicalData.store)) {
    testData[i] = {"address": key, "info": historicalData.store[key]};
    i++;
}

const usersArray = new SharedArray('Users accounts', function () {
    const accounts = JSON.parse(open("../../data/accounts.json"));
    let data = [];
    for (let i = 0; i < Object.keys(accounts).length; i++) {
        data[i] = accounts[i];
    }
    return data;
});


export default function EthGetTransactionCountTest() {
    const vuID = exec.vu.idInTest
    const index = vuID % usersArray.length;
    const dataIndex = vuID % Object.entries(testData).length;
    const txInfo = testData[dataIndex].info[0];

    const accountSenderAddress = usersArray[index].sender_address;
    const accountSenderPrivateKey = usersArray[index].sender_key;
    const client = ethClient(accountSenderPrivateKey);
    const nonce = client.getNonce(accountSenderAddress);
    console.log("nonce: ", nonce);

    // blockNumber
    const requestParamsBlockNumber = {
        requestType: "blockNumber",
        method: "eth_getTransactionCount",
        params: [accountSenderAddress, {"blockNumber": txInfo.blockNumber}]
    }

    doRequest(client, requestParamsBlockNumber, nonce);

    // blockHash
    const requestParamsBlockHash = {
        requestType: "blockHash",
        method: "eth_getTransactionCount",
        params: [accountSenderAddress, {"blockHash": txInfo.blockHash}]
    }
    
    doRequest(client, requestParamsBlockHash, nonce);
}

function doRequest(client, requestParams, expectedValue) {
    const startTime = new Date();
    try {
        const responseBody = client.callTracer(
            JSON.stringify(requestParams.requestType), 
            JSON.stringify(requestParams.method), 
            JSON.stringify(requestParams.params)
        );
        const response = JSON.parse(responseBody);

        const checkResult = check(response, {
            'response result is not equal to real nonce': (r) => parseInt(r.result, 16) === expectedValue,
        });
        if (!checkResult) {
            console.log('Error in response of eth_getTransactionCount: ' + JSON.stringify(response));
            ethGetTransactionCountRequestErrorCounter.add(1);
        }
    } catch (e) {
        console.log('Error in eth_getTransactionCount: ' + e);
        ethGetTransactionCountErrorCounter.add(1);
    }
    ethGetTransactionCountRequestTime.add(new Date() - startTime);
    ethGetTransactionCountRequests.add(1);
}