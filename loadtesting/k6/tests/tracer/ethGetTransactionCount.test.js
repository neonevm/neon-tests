import { ethClient } from '../utils/ethClient.js';
import { standardScenarioOptions } from '../../options/options.js';
import { Trend, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';

import exec from 'k6/execution';
import { check } from 'k6';

const ethGetTransactionCountRequests = new Counter('tracer_eth_get_transaction_count_requests');
const ethGetTransactionCountRequestErrorCounter = new Counter('tracer_eth_get_transaction_count_request_errors');
const ethGetTransactionCountErrorCounter = new Counter('tracer_eth_get_transaction_count_errors');
const ethGetTransactionCountRequestTime = new Trend('tracer_eth_get_transaction_count_request_time', true);

export const options = standardScenarioOptions;

const historicalData = JSON.parse(open("../../data/tracer_data.json"));

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

    const mixedData = (historicalData.neon_transfers).concat(historicalData.erc20_transfers, 
        historicalData.erc20spl_transfers);
    const dataIndex = vuID % mixedData.length;
    const txInfo = mixedData[dataIndex];

    const accountPrivateKey = usersArray[index].sender_key;
    const client = ethClient(accountPrivateKey);

    // blockNumber
    const requestParamsBlockNumber = {
        requestType: "blockNumber",
        method: "eth_getTransactionCount",
        params: [txInfo.sender, {"blockNumber": txInfo.blockNumber}]
    }

    doRequest(client, requestParamsBlockNumber, txInfo.sender_nonce);

    // blockHash
    const requestParamsBlockHash = {
        requestType: "blockHash",
        method: "eth_getTransactionCount",
        params: [txInfo.sender, {"blockHash": txInfo.blockHash}]
    }
    
    doRequest(client, requestParamsBlockHash, txInfo.sender_nonce);
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
            'response result is not equal to real nonce': (r) => parseInt(r.result, 16) == expectedValue,
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